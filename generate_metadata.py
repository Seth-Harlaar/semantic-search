import psycopg2
import requests
import time
import inflection
import re

DB_CONFIG = {
    "dbname": "semantic_search",
    "user": "postgres",
    "password": "pa55w0rd",
    "host": "localhost",
    "port": 5432,
}

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama2"

VALID_OPTIONS = ['code', 'llm-llama2', 'natural-code']

# Returns a list of (id, filename, namespace, parent_class, function_text)
# for code_functions that don't yet have an embedding row for the given metadata_type.
def fetch_functions_missing_metadata(conn, metadata_type):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT cf.id, cf.filename, cf.namespace, cf.parent_class, cf.function_text
            FROM code_functions cf
            LEFT JOIN code_function_embeddings cfe
            ON cf.id = cfe.function_id AND cfe.model = %s
            WHERE cfe.id IS NULL
        """, (metadata_type,))
        return cur.fetchall()

def generate_metadata_code(filename, namespace, parent_class, function_text):
    return f"Filename: {filename}\nNamespace: {namespace}\nClass: {parent_class}\nFunction:\n{function_text}"

# Send code_string to Llama2 and get a concise but detailed description.
def generate_metadata_llm_llama2(code_string):
    prompt = (
        f"Describe what the following C# function does in 1–2 sentences, "
        f"keeping as much implementation detail as possible:\n\n{code_string}\n\nDescription:"
    )
    res = requests.post(
        url=OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
        }
    )
    res.raise_for_status()
    desc = res.json()["response"].strip()
    print(f"Generated LLM description: {desc}")
    return desc

# Placeholder — you can implement later.
def generate_metadata_natural_code(filename, namespace, parent_class, function_text):
    return textify(filename, namespace, parent_class, function_text)

# based off of Qdrant: https://qdrant.tech/documentation/advanced-tutorials/code-search/
def textify(filename, namespace, parent_class, function_text) -> str:
    # Get rid of all the camel case / snake case
    # - inflection.underscore changes the camel case to snake case
    # - inflection.humanize converts the snake case to human readable form
    parent_name = inflection.humanize(inflection.underscore(parent_class))
    function = inflection.humanize(inflection.underscore(function_text))

    # Combine all the bits and pieces together
    text_representation = (
        f"{filename}"
        f"{namespace}"
        f"{parent_name}"
        f"defined as {function}"
    )

    # Remove any special characters and concatenate the tokens
    tokens = re.split(r"\W", text_representation)
    tokens = filter(lambda x: x, tokens)
    return " ".join(tokens)


# Stores the generated metadata in the code_function_embeddings table.
def store_metadata(conn, function_id, metadata, metadata_type):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO code_function_embeddings (function_id, embedding, model, metadata, metadata_type)
            VALUES (%s, NULL, %s, %s, %s)
        """, (function_id, metadata_type, metadata, metadata_type))

def process_functions(metadata_type):
    if metadata_type not in VALID_OPTIONS:
        raise ValueError(f"Invalid metadata type. Choose from: {VALID_OPTIONS}")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        rows = fetch_functions_missing_metadata(conn, metadata_type)
        print(f"Found {len(rows)} functions without '{metadata_type}' metadata.")

        for idx, (func_id, filename, namespace, parent_class, function_text) in enumerate(rows, 1):
            print(f"[{idx}/{len(rows)}] Processing function ID {func_id}…")
            try:
                if metadata_type == 'code':
                    metadata = generate_metadata_code(filename, namespace, parent_class, function_text)
                elif metadata_type == 'llm-llama2':
                    code_string = generate_metadata_code(filename, namespace, parent_class, function_text)
                    metadata = generate_metadata_llm_llama2(code_string)
                elif metadata_type == 'natural-code':
                    metadata = generate_metadata_natural_code(filename, namespace, parent_class, function_text)

                store_metadata(conn, func_id, metadata, metadata_type)
                conn.commit()
            except Exception as e:
                print(f"Error processing function ID {func_id}: {e}")
                conn.rollback()
                time.sleep(1)

        print(f"All '{metadata_type}' metadata generated & stored.")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <metadata_type>")
        print(f"Valid options: {VALID_OPTIONS}")
        sys.exit(1)

    metadata_type = sys.argv[1]
    process_functions(metadata_type)
