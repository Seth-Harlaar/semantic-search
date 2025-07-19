from sentence_transformers import SentenceTransformer
import psycopg2
import time

DB_CONFIG = {
    "dbname": "your_db",
    "user": "your_user",
    "password": "your_password",
    "host": "localhost",
    "port": 5432,
}

MODEL_NAME = "all-MiniLM-L6-v2"  # or another local embedding model

def fetch_functions_without_embedding(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT cf.id, cf.function_text
            FROM code_functions cf
            LEFT JOIN code_function_embeddings cfe
            ON cf.id = cfe.function_id
            WHERE cfe.id IS NULL
        """)
        return cur.fetchall()  # list of (id, function_text)

def generate_embedding(model, text): # this doesn't use ollama properly
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist()

def store_embedding(conn, function_id, embedding):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO code_function_embeddings (function_id, embedding, model)
            VALUES (%s, %s, %s)
        """, (function_id, embedding, MODEL_NAME))

def embed_all_functions():
    conn = psycopg2.connect(**DB_CONFIG)
    model = SentenceTransformer(MODEL_NAME)

    try:
        rows = fetch_functions_without_embedding(conn)
        print(f"Found {len(rows)} functions without embeddings.")

        for idx, (func_id, func_text) in enumerate(rows, 1):
            print(f"[{idx}/{len(rows)}] Embedding function ID {func_id}…")
            try:
                emb = generate_embedding(model, func_text)
                store_embedding(conn, func_id, emb)
                conn.commit()
            except Exception as e:
                print(f"Error embedding function ID {func_id}: {e}")
                conn.rollback()
                time.sleep(1)

        print("All embeddings created & stored.")
    finally:
        conn.close()
