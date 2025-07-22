import psycopg2
import requests
import csv
import sys

DB_CONFIG = {
    "dbname": "semantic_search",
    "user": "postgres",
    "password": "pa55w0rd",
    "host": "localhost",
    "port": 5432,
}

OLLAMA_URL = "http://localhost:11434/api/embeddings"  # for embeddings
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


# will grab all the tests from tests.csv and loop through each one
# each row in tests is a string followed be expected function ID corresponding to code_functions.id
# this will take each of the test strings, generate an embedding, and compare it to the embeddings
# in code_function_embeddings, then get the 3 most likely returned and save the results in another csv file called results
def test():
    input_csv = "tests.csv"
    output_csv = "results.csv"

    conn = psycopg2.connect(**DB_CONFIG)

    with open(input_csv, newline='', encoding='utf-8') as infile, \
         open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # header
        writer.writerow([
            "metadata_type", "test_text", "expected_id",
            "rank_1_id", "rank_1_distance",
            "rank_2_id", "rank_2_distance",
            "rank_3_id", "rank_3_distance"
        ])

        for row in reader:
            if not row:
                continue
            test_text, expected_id = row[0], row[1]

            # embed query
            query_emb = generate_embedding(test_text)
            emb_str = f"[{','.join(str(x) for x in query_emb)}]"

            for metadata_type in VALID_OPTIONS:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT cf.id, cfe.embedding <=> %s AS distance
                        FROM code_function_embeddings cfe
                        JOIN code_functions cf ON cf.id = cfe.function_id
                        WHERE cfe.metadata_type = %s
                        ORDER BY distance ASC
                        LIMIT 3
                    """, (emb_str, metadata_type))

                    results = cur.fetchall()

                # collect top-3
                top = []
                for r in results:
                    top.append((r[0], round(r[1], 4)))

                # pad to 3 if less
                while len(top) < 3:
                    top.append(("", ""))

                writer.writerow([
                    metadata_type, test_text, expected_id,
                    top[0][0], top[0][1],
                    top[1][0], top[1][1],
                    top[2][0], top[2][1],
                ])

    conn.close()
    print(f"Test results written to {output_csv}")


if __name__ == "__main__":
    test()