import sys
import psycopg2
import requests

DB_CONFIG = {
  "dbname": "semantic_search",
  "user": "postgres",
  "password": "pa55w0rd",
  "host": "localhost",
  "port": 5432,
}

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "chroma/all-minilm-l6-v2-f32:latest"

VALID_OPTIONS = ['code', 'llm-llama2', 'natural-code']

def generate_embedding(text):
  res = requests.post(
    url=OLLAMA_URL,
    json={
      "model": MODEL_NAME,
      "prompt": text
    }
  )
  res.raise_for_status()
  return res.json()["embedding"]

def find_closest_function(prompt, top_k=1):
  # get embedding for the prompt
  query_emb = generate_embedding(prompt)
  emb_str = f"[{','.join(str(x) for x in query_emb)}]"
  conn = psycopg2.connect(**DB_CONFIG)
  try:
    with conn.cursor() as cur:
      cur.execute(f"""
        SELECT cf.id, cf.filename, cf.namespace, cf.parent_class, cf.function_text,
          cfe.embedding <=> %s AS distance, cfe.metadata_type
        FROM code_function_embeddings cfe
          JOIN code_functions cf ON cf.id = cfe.function_id
        WHERE cfe.metadata_type = %s
          ORDER BY distance ASC
        LIMIT %s
      """, (emb_str, metadata_type, top_k))

      results = cur.fetchall()

      for r in results:
        print(f"ID: {r[0]}")
        print(f"File: {r[1]}")
        print(f"Namespace: {r[2]}")
        print(f"Class: {r[3]}")
        print(f"Distance: {r[5]:.4f}")
        print(f"MetaData Type: {r[6]}")
        print("Function:")
        print(r[4])
        print("=" * 40)

    return results
  finally:
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
      print(f"Usage: python {sys.argv[0]} <metadata_type>")
      print(f"Valid options: {VALID_OPTIONS}")
      sys.exit(1)

    metadata_type = sys.argv[1]
    prompt = input("Describe the function you’re looking for: ")
    find_closest_function(prompt, top_k=3)