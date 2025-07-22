import psycopg2
import requests
import time

DB_CONFIG = {
    "dbname": "semantic_search",
    "user": "postgres",
    "password": "pa55w0rd",
    "host": "localhost",
    "port": 5432,
}

OLLAMA_URL = "http://localhost:11434/api/generate"  # for text generation
EMBED_URL = "http://localhost:11434/api/embeddings"  # for embeddings
MODEL_NAME = "chroma/all-minilm-l6-v2-f32:latest"

def fetch_functions_without_embedding(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, metadata
                FROM code_function_embeddings
                WHERE embedding is null
        """)
        return cur.fetchall()

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

def store_embedding(conn, embedding_id, embedding):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE code_function_embeddings
                SET embedding = %s
                WHERE id = %s
        """, (embedding, embedding_id))

def embed_all_functions():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        rows = fetch_functions_without_embedding(conn)
        print(f"Found {len(rows)} functions without embeddings.")

        for index, (embedding_id, metadata) in enumerate(rows, 1):
            print(f"[{index}/{len(rows)}] Processing embedding ID {embedding_id}…")
            try:
                embedding = generate_embedding(metadata)
                store_embedding(conn, embedding_id, embedding)
                conn.commit()
            except Exception as e:
                print(f"Error processing function ID {embedding_id}: {e}")
                conn.rollback()
                time.sleep(1)

        print("All functions described & embeddings stored.")
    finally:
        conn.close()

if __name__ == "__main__":
    embed_all_functions()
