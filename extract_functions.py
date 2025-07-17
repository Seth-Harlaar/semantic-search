import os
import sys
import csv
from tree_sitter import Language, Parser

GRAMMAR_PATH = "tree-sitter-c-sharp"
BUILD_LIB_PATH = "build/my-languages.so"

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
    # Try to get the declared name from typical child nodes like 'identifier'
    for child in node.children:
        if child.type == "identifier":
            return code_bytes[child.start_byte:child.end_byte].decode("utf8")
    return ""

def extract_functions_with_context(code_bytes, root_node):
    functions = []
    def visit(node):
        if node.type == "method_declaration":
            func_text = code_bytes[node.start_byte:node.end_byte].decode("utf8").strip()
            
            # Find parent class
            parent_class_node = find_ancestor_of_type(node, "class_declaration")
            parent_class_name = get_node_name(parent_class_node, code_bytes) if parent_class_node else ""

            # Find namespace
            namespace_node = find_ancestor_of_type(node, "namespace_declaration")
            namespace_name = get_node_name(namespace_node, code_bytes) if namespace_node else ""

            functions.append({
                "namespace": namespace_name,
                "parent_class": parent_class_name,
                "function_text": func_text
            })
        for child in node.children:
            visit(child)
    visit(root_node)
    return functions

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

    output_csv = "functions_output.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["filename", "namespace", "parent_class", "function_text"])
        writer.writeheader()
        for func in funcs:
            writer.writerow({
                "filename": os.path.basename(file_path),
                "namespace": func["namespace"],
                "parent_class": func["parent_class"],
                "function_text": func["function_text"]
            })

    print(f"Extracted {len(funcs)} functions. Output written to {output_csv}")

if __name__ == "__main__":
    main()
