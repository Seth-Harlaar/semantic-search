import psycopg2
import requests
import time
import sys

DB_CONFIG = {
    "dbname": "semantic_search",
    "user": "postgres",
    "password": "pa55w0rd",
    "host": "localhost",
    "port": 5432,
}

EMBED_URL = "http://localhost:11434/api/embeddings"  # for embeddings
MODEL_NAME = "chroma/all-minilm-l6-v2-f32:latest"

# Create an embedding from the natural language description.
def generate_embedding(text):
    res = requests.post(
        url=EMBED_URL,
        json={
            "model": MODEL_NAME,
            "prompt": text
        }
    )
    res.raise_for_status()
    return res.json()["embedding"]


# Regenerates embeddings from the *existing descriptions* of all functions.
# Updates the embedding column in the DB.
def generate_all_embeddings():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, description
                FROM code_functions
                    WHERE {colname} = null
            """)
            rows = cur.fetchall()

        print(f"Found {len(rows)} existing embeddings to regenerate.")

        for index, (embedding_id, description) in enumerate(rows, 1):
            print(f"[{index}/{len(rows)}] Re-embedding ID {embedding_id}…")
            try:
                new_embedding = generate_embedding(description)

                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE code_function_embeddings
                        SET embedding = %s, model = %s
                        WHERE id = %s
                    """, (new_embedding, MODEL_NAME, embedding_id))

                conn.commit()
            except Exception as e:
                print(f"Error re-embedding ID {embedding_id}: {e}")
                conn.rollback()
                time.sleep(1)

        print("All embeddings have been regenerated.")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: embed.py columnname")
    else:
        colname = sys.argv[1]
        generate_all_embeddings()