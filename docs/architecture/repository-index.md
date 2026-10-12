# Repository index (role 2) / 仓库索引（2 号）

The index parses every Python file in a repository checkout with `ast` and
records its modules, classes, functions and methods. Lexical retrieval
(role 3), failure mapping (role 4) and evaluation (role 5) read from it.

索引用 `ast` 解析仓库里的每个 Python 文件，记录其中的模块、类、函数和方法。
词法检索（3 号）、失败映射（4 号）和评估（5 号）都从这里读取数据。

## Build / 构建

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

只依赖标准库；需要 Python 3.10 及以上。

## Index record / 索引记录

Defined in `src/repository/models.py` (`IndexRecord`).

定义在 `src/repository/models.py`（`IndexRecord`）。

| Field / 字段 | Example / 示例 | Notes / 说明 |
|---|---|---|
| `id` | `shop/pricing.py::Cart.total` | Unique. Modules use the bare path. A redefined name (property setter, `if/else` definitions) gets `#2`, `#3`... in source order.<br>唯一标识。模块直接用路径。同名重复定义（property 的 setter、`if/else` 里各定义一次）按出现顺序加 `#2`、`#3`…… |
| `path` | `shop/pricing.py` | Relative to the repo root, always `/`.<br>相对仓库根目录，一律用 `/`。 |
| `module` | `shop.pricing` | Dotted name derived from the path.<br>由路径推出的点分模块名。 |
| `symbol` | `Cart.total` | Dotted name inside the file. Nested functions: `Cart.total.line_total`. Modules: `<module>`, as in tracebacks.<br>文件内的点分名称。嵌套函数写作 `Cart.total.line_total`。模块记录为 `<module>`，与 traceback 的写法一致。 |
| `name` | `total` | Last part of `symbol`.<br>`symbol` 的最后一段。 |
| `kind` | `method` | `module`, `class`, `function` (module-level or nested in a function) or `method` (directly in a class body).<br>`module`、`class`、`function`（模块顶层或嵌套在函数里）或 `method`（直接定义在类体中）。 |
| `start_line`, `end_line` | `30`, `40` | 1-based, inclusive, same numbering as tracebacks. `start_line` includes decorators.<br>从 1 开始，包含首尾两行，与 traceback 的行号一致。`start_line` 包含装饰器所在行。 |
| `parent` | `shop/pricing.py::Cart` | `id` of the enclosing record; `None` for modules.<br>外层记录的 `id`；模块为 `None`。 |
| `signature` | `def total(self, with_tax=True)` | `""` for modules.<br>模块为空字符串。 |
| `docstring` | `Total price of all items.` | Truncated to `max_text_chars`.<br>截断到 `max_text_chars`。 |
| `text` | | Retrieval text, truncated to `max_text_chars` (default 2000). Functions/methods: path, symbol, then the source. Classes: path, symbol, signature, docstring, member names. Modules: path, module name, docstring, top-level names. Tokenization is left to the retriever.<br>检索用文本，截断到 `max_text_chars`（默认 2000 字符）。函数/方法：路径、symbol，然后是源码。类：路径、symbol、签名、docstring、成员名。模块：路径、模块名、docstring、顶层名称。分词由检索模块负责。 |
| `is_test` | `False` | Heuristic: inside `test/`, `tests/` or `testing/`, or named `test_*.py`, `*_test.py`, `tests.py`, `conftest.py`.<br>启发式判断：位于 `test/`、`tests/`、`testing/` 目录下，或文件名为 `test_*.py`、`*_test.py`、`tests.py`、`conftest.py`。 |

## Files that cannot be indexed / 无法索引的文件

They are listed in `index.errors` (`ParseError`: `path`, `kind`, `message`,
`line`) and contribute no records. The build never stops on a bad file.
`kind` is one of `syntax_error`, `decode_error`, `too_large` (over
`max_file_bytes`, default 2 MB), `read_error`, `recursion_error`.

这些文件记录在 `index.errors` 中（`ParseError`：`path`、`kind`、`message`、
`line`），不产生任何索引记录。遇到坏文件时构建不会中断。`kind` 取值为
`syntax_error`（语法错误）、`decode_error`（编码错误）、`too_large`（超过
`max_file_bytes`，默认 2 MB）、`read_error`（读取失败）、`recursion_error`
（嵌套过深）。

Skipped while walking: hidden directories, `__pycache__`, `node_modules`,
`site-packages`, `*.egg-info`, symlinks, and `build/`, `dist/`, `env/`,
`venv/` at the repo root.

遍历时跳过：隐藏目录、`__pycache__`、`node_modules`、`site-packages`、
`*.egg-info`、符号链接，以及仓库根目录下的 `build/`、`dist/`、`env/`、`venv/`。

## Lookups / 查询

| Method / 方法 | Use / 用途 |
|---|---|
| `index.get(id)` | One record.<br>获取一条记录。 |
| `index.records_in_file(path)` | Module record first, then definitions in source order.<br>先返回模块记录，再按源码顺序返回其中的定义。 |
| `index.children(id)` | Direct children, e.g. the methods of a class.<br>直接子记录，例如一个类的方法。 |
| `index.find_enclosing(path, line)` | Innermost record containing the line, falling back to the module record. For mapping traceback frames.<br>包含该行的最内层记录，找不到时返回模块记录。用于把 traceback 栈帧映射到代码实体。 |
| `index.find_by_name(name)` | Records whose symbol is `name` or ends with `.name`, e.g. `total` or `Cart.total`.<br>symbol 等于 `name` 或以 `.name` 结尾的记录，例如 `total` 或 `Cart.total`。 |
| `to_repo_path(path, repo_root)` | Normalize a traceback path, e.g. `("/testbed/shop/pricing.py", "/testbed")` -> `shop/pricing.py`; `None` if outside the repo.<br>规范化 traceback 中的路径，例如 `("/testbed/shop/pricing.py", "/testbed")` -> `shop/pricing.py`；仓库外的路径返回 `None`。 |
