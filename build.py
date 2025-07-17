from tree_sitter import Language

Language.build_library(
    'build/ts-csharp.so',
    ['tree-sitter-c-sharp']
)