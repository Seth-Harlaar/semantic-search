import os
import sys
import psycopg2
from tree_sitter import Language, Parser

# Config
GRAMMAR_PATH = "tree-sitter-c-sharp"
BUILD_LIB_PATH = "build/my-languages.so"

DB_CONFIG = {
    "dbname": "semantic_search",
    "user": "postgres",
    "password": "pa55w0rd",
    "host": "localhost",
    "port": 5432,
}

TABLE_NAME = "code_functions"

def build_language():
    if not os.path.exists(BUILD_LIB_PATH):
        print("Building C# grammar …")
        Language.build_library(
            BUILD_LIB_PATH,
            [GRAMMAR_PATH]
        )
    else:
        print("Using existing compiled grammar.")
    return Language(BUILD_LIB_PATH, "c_sharp")

def find_ancestor_of_type(node, ancestor_type):
    parent = node.parent
    while parent:
        if parent.type == ancestor_type:
            return parent
        parent = parent.parent
    return None

def get_node_name(node, code_bytes):
    if not node:
        return ""
    for child in node.children:
        if child.type == "identifier":
            return code_bytes[child.start_byte:child.end_byte].decode("utf8")
    return ""

def extract_functions_with_context(code_bytes, root_node):
    functions = []
    def visit(node):
        if node.type == "method_declaration":
            func_text = code_bytes[node.start_byte:node.end_byte].decode("utf8").strip()

            parent_class_node = find_ancestor_of_type(node, "class_declaration")
            parent_class_name = get_node_name(parent_class_node, code_bytes)

            namespace_node = find_ancestor_of_type(node, "namespace_declaration")
            namespace_name = get_node_name(namespace_node, code_bytes)

            functions.append({
                "namespace": namespace_name,
                "parent_class": parent_class_name,
                "function_text": func_text
            })
        for child in node.children:
            visit(child)
    visit(root_node)
    return functions

def insert_into_db(file_name, functions):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    for func in functions:
        cur.execute(f"""
            INSERT INTO {TABLE_NAME} (filename, namespace, parent_class, function_text)
            VALUES (%s, %s, %s, %s)
        """, (file_name, func["namespace"], func["parent_class"], func["function_text"]))
    conn.commit()
    cur.close()
    conn.close()

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <file.cs>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    language = build_language()
    parser = Parser()
    parser.set_language(language)

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    code_bytes = code.encode("utf8")

    tree = parser.parse(code_bytes)
    root_node = tree.root_node

    funcs = extract_functions_with_context(code_bytes, root_node)

    if not funcs:
        print("No functions found.")
        return

    insert_into_db(os.path.basename(file_path), funcs)

    print(f"Inserted {len(funcs)} functions from {file_path} into {TABLE_NAME}.")

if __name__ == "__main__":
    main()
