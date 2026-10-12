# Repository index (role 2)

The index parses every Python file in a repository checkout with `ast` and
records its modules, classes, functions and methods. Lexical retrieval
(role 3), failure mapping (role 4) and evaluation (role 5) read from it.

## Build

```bash
python scripts/build_index.py path/to/repo -o index.json
```

```python
from src.repository.indexer import RepositoryIndex, build_index

index = build_index("path/to/repo")
index.save("index.json")
index = RepositoryIndex.load("index.json")
```

Standard library only; Python 3.10+.

## Index record

Defined in `src/repository/models.py` (`IndexRecord`).

| Field | Example | Notes |
|---|---|---|
| `id` | `shop/pricing.py::Cart.total` | Unique. Modules use the bare path. A redefined name (property setter, `if/else` definitions) gets `#2`, `#3`... in source order. |
| `path` | `shop/pricing.py` | Relative to the repo root, always `/`. |
| `module` | `shop.pricing` | Dotted name derived from the path. |
| `symbol` | `Cart.total` | Dotted name inside the file. Nested functions: `Cart.total.line_total`. Modules: `<module>`, as in tracebacks. |
| `name` | `total` | Last part of `symbol`. |
| `kind` | `method` | `module`, `class`, `function` (module-level or nested in a function) or `method` (directly in a class body). |
| `start_line`, `end_line` | `30`, `40` | 1-based, inclusive, same numbering as tracebacks. `start_line` includes decorators. |
| `parent` | `shop/pricing.py::Cart` | `id` of the enclosing record; `None` for modules. |
| `signature` | `def total(self, with_tax=True)` | `""` for modules. |
| `docstring` | `Total price of all items.` | Truncated to `max_text_chars`. |
| `text` | | Retrieval text, truncated to `max_text_chars` (default 2000). Functions/methods: path, symbol, then the source. Classes: path, symbol, signature, docstring, member names. Modules: path, module name, docstring, top-level names. Tokenization is left to the retriever. |
| `is_test` | `False` | Heuristic: inside `test/`, `tests/` or `testing/`, or named `test_*.py`, `*_test.py`, `tests.py`, `conftest.py`. |

## Files that cannot be indexed

They are listed in `index.errors` (`ParseError`: `path`, `kind`, `message`,
`line`) and contribute no records. The build never stops on a bad file.
`kind` is one of `syntax_error`, `decode_error`, `too_large` (over
`max_file_bytes`, default 2 MB), `read_error`, `recursion_error`.

Skipped while walking: hidden directories, `__pycache__`, `node_modules`,
`site-packages`, `*.egg-info`, symlinks, and `build/`, `dist/`, `env/`,
`venv/` at the repo root.

## Lookups

| Method | Use |
|---|---|
| `index.get(id)` | One record. |
| `index.records_in_file(path)` | Module record first, then definitions in source order. |
| `index.children(id)` | Direct children, e.g. the methods of a class. |
| `index.find_enclosing(path, line)` | Innermost record containing the line, falling back to the module record. For mapping traceback frames. |
| `index.find_by_name(name)` | Records whose symbol is `name` or ends with `.name`, e.g. `total` or `Cart.total`. |
| `to_repo_path(path, repo_root)` | Normalize a traceback path, e.g. `("/testbed/shop/pricing.py", "/testbed")` -> `shop/pricing.py`; `None` if outside the repo. |
