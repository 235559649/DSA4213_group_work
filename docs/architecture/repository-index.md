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

## Build from a SWE-bench task ID / 按 SWE-bench 任务 ID 构建

```bash
python scripts/build_index.py --task django__django-11133
```

```python
from src.repository.swebench import build_task_index, load_task

task = load_task("django__django-11133")   # repo, base_commit, problem_statement, version, created_at
index = build_task_index("django__django-11133")
```

On first use this downloads the pinned dataset revision
(`SWE-bench/SWE-bench_Verified@78f471bf`), clones the task's repository once,
reads the Python files at `base_commit` straight from git (no checkout), and
caches the index per task. Later calls load the cached index.

第一次调用时会自动下载锁定版本的数据集（`SWE-bench/SWE-bench_Verified@78f471bf`），
每个仓库只 clone 一次，直接从 git 读取 `base_commit` 版本的 Python 文件（不需要 checkout），
并按任务缓存索引。之后再调用会直接读取缓存。

- Needs `git` and `pyarrow` (`pip install pyarrow`, only for loading tasks).<br>
  需要 `git` 和 `pyarrow`（`pip install pyarrow`，只在读取任务时用到）。
- Cache: `.swebench_cache/` in the project root, ignored by git. Move it with the
  `SWEBENCH_CACHE_DIR` environment variable or `--cache-dir`.<br>
  缓存默认在项目根目录的 `.swebench_cache/`，不会被 git 提交。可以用环境变量
  `SWEBENCH_CACHE_DIR` 或 `--cache-dir` 改到别的位置。
- Only `instance_id`, `repo`, `base_commit`, `problem_statement`, `version`,
  `created_at` are read from the dataset. The reference patch, test patch,
  FAIL_TO_PASS / PASS_TO_PASS and hints never reach the cache.<br>
  只从数据集读取 `instance_id`、`repo`、`base_commit`、`problem_statement`、`version`、
  `created_at`。参考补丁、测试补丁、FAIL_TO_PASS / PASS_TO_PASS 和 hints 不会进入缓存。
- Index metadata records `repo`, `commit`, `instance_id`, `dataset_revision` and
  `index_sha256` (`index.digest()`, the hash of the indexed content), as the
  index identity required by the evaluation protocol.<br>
  索引元数据记录 `repo`、`commit`、`instance_id`、`dataset_revision` 和
  `index_sha256`（`index.digest()`，索引内容的哈希），作为评估协议要求的"索引身份"。
- Files generated at install time inside the task container (e.g. a
  setuptools-scm `_version.py`) are not in git and so not indexed.<br>
  任务容器安装时生成的文件（例如 setuptools-scm 生成的 `_version.py`）不在 git 里，所以不会被索引。

## Index record / 索引记录

Defined in `src/repository/models.py` (`IndexRecord`). The first six fields
are the shared contract with role 1 (`IndexRecord` in `src/agent/contracts.py`):
same names, order, types and defaults. The remaining fields are extras filled
by the indexer; they have defaults, so a record can be built with only the
six shared fields.

定义在 `src/repository/models.py`（`IndexRecord`）。前六个字段是和 1 号约定的共享接口
（`src/agent/contracts.py` 里的 `IndexRecord`）：名称、顺序、类型、默认值都一致。其余字段由
索引器额外填写，都有默认值，所以只传六个共享字段也能创建记录。

**Shared with role 1 / 与 1 号共享的字段**

| Field / 字段 | Example / 示例 | Notes / 说明 |
|---|---|---|
| `path` | `shop/pricing.py` | Relative to the repo root, always `/`.<br>相对仓库根目录，一律用 `/`。 |
| `symbol` | `Cart.total` | Dotted name inside the file. Nested functions: `Cart.total.line_total`. `None` for modules.<br>文件内的点分名称。嵌套函数写作 `Cart.total.line_total`。模块为 `None`。 |
| `symbol_type` | `method` | `module`, `class`, `function` (module-level or nested in a function) or `method` (directly in a class body).<br>`module`、`class`、`function`（模块顶层或嵌套在函数里）或 `method`（直接定义在类体中）。 |
| `start_line`, `end_line` | `30`, `40` | 1-based, inclusive, same numbering as tracebacks. `start_line` includes decorators. Always set by the indexer.<br>从 1 开始，包含首尾两行，与 traceback 的行号一致。`start_line` 包含装饰器所在行。索引器总会填写。 |
| `retrieval_text` | | Truncated to `max_text_chars` (default 2000). Functions/methods: path, symbol, then the source. Classes: path, symbol, signature, docstring, member names. Modules: path, module name, docstring, top-level names. Tokenization is left to the retriever.<br>截断到 `max_text_chars`（默认 2000 字符）。函数/方法：路径、symbol，然后是源码。类：路径、symbol、签名、docstring、成员名。模块：路径、模块名、docstring、顶层名称。分词由检索模块负责。 |

**Extra fields / 额外字段**

| Field / 字段 | Example / 示例 | Notes / 说明 |
|---|---|---|
| `id` | `shop/pricing.py::Cart.total` | Unique. Modules use the bare path. A redefined name (property setter, `if/else` definitions) gets `#2`, `#3`... in source order. Derived from `path` and `symbol` if not given.<br>唯一标识。模块直接用路径。同名重复定义（property 的 setter、`if/else` 里各定义一次）按出现顺序加 `#2`、`#3`……未提供时由 `path` 和 `symbol` 自动生成。 |
| `module` | `shop.pricing` | The name Python imports the file as: the path below the outermost directory without an `__init__.py`, so `src/_pytest/python.py` is `_pytest.python`.<br>Python 导入该文件时用的名字：从最外层没有 `__init__.py` 的目录以下开始算，所以 `src/_pytest/python.py` 是 `_pytest.python`。 |
| `name` | `total` | Last part of `symbol`; `None` for modules.<br>`symbol` 的最后一段；模块为 `None`。 |
| `parent` | `shop/pricing.py::Cart` | `id` of the enclosing record; `None` for modules.<br>外层记录的 `id`；模块为 `None`。 |
| `signature` | `def total(self, with_tax=True)` | `""` for modules.<br>模块为空字符串。 |
| `docstring` | `Total price of all items.` | Truncated to `max_text_chars`.<br>截断到 `max_text_chars`。 |
| `is_test` | `False` | Heuristic: inside `test/`, `tests/` or `testing/`, or named `test_*.py`, `*_test.py`, `tests.py`, `conftest.py`.<br>启发式判断：位于 `test/`、`tests/`、`testing/` 目录下，或文件名为 `test_*.py`、`*_test.py`、`tests.py`、`conftest.py`。 |

Saved index JSON carries `schema_version` (currently 4); loading a file with a
different version raises an error. `build_task_index` rebuilds outdated cached
indexes automatically.

保存的索引 JSON 带有 `schema_version`（当前为 4）；读取版本不同的文件会报错。
`build_task_index` 会自动重建过期的缓存索引。

## Import graph / 导入关系

`index.imports` maps each file to the repository files it imports (files
without internal imports are omitted). Statements anywhere in the file count,
including inside functions and `try` blocks. Rules:

`index.imports` 记录每个文件导入了仓库里的哪些文件（没有内部导入的文件不出现）。
文件中任何位置的 import 都算，包括函数内部和 `try` 块里的。规则如下：

- Relative imports are resolved against the file's package; going above the
  top-level package is dropped.<br>
  相对导入按文件所在的包解析；超出顶层包的会被丢弃。
- `from a.b import c` points to `a/b/c.py` if `c` is a submodule, otherwise to
  module `a.b`. `import a.b` points to `a.b` only, not to the parent package `a`.<br>
  `from a.b import c`：如果 `c` 是子模块就指向 `a/b/c.py`，否则指向模块 `a.b`。
  `import a.b` 只指向 `a.b`，不指向父包 `a`。
- External modules (stdlib, third-party) and self-imports are dropped. A package
  (`x/__init__.py`) wins over a module (`x.py`). Names claimed by two files of
  the same kind are ambiguous and not resolved.<br>
  外部模块（标准库、第三方库）和自己导入自己会被丢弃。包（`x/__init__.py`）优先于同名模块（`x.py`）。
  被两个同类文件同时占用的模块名视为有歧义，不解析。
- Files that fail to parse can still be import targets, but contribute no
  imports of their own.<br>
  解析失败的文件仍然可以被别人导入，但它自己的导入不会被记录。

| Method / 方法 | Use / 用途 |
|---|---|
| `index.imports_of(path)` | Files `path` imports.<br>`path` 导入的文件。 |
| `index.imported_by(path)` | Files that import `path`.<br>导入了 `path` 的文件。 |
| `index.neighbors(path)` | Both, without `path` itself: the one-hop neighbors N(q) of the proposal.<br>两者合并，去掉自身：即 proposal 中的一跳邻居 N(q)。 |
| `index.is_test_file(path)` | The file's `is_test` flag.<br>文件的 `is_test` 标记。 |

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

## Keeping the index current during a run / 运行中保持索引与代码一致

The index is built at `base_commit`. Once the agent edits a file, line numbers
in that file shift, and traceback frames no longer match the index. Before
mapping a failure (Condition D), update the index with the files changed so
far:

索引是按 `base_commit` 构建的。Agent 一旦修改文件，该文件的行号就会变化，traceback
里的行号就和索引对不上了。在映射失败信息（条件 D）之前，先用目前为止改动过的文件更新索引：

```python
base = build_task_index(instance_id)          # once per run; keep it
index = base.with_updated_files(changes)      # before each failure mapping
record = index.find_enclosing(path, line)
```

`changes` maps each changed path to its current content (`bytes`, or `str`
encoded as UTF-8), or to `None` if the file was deleted. In the task
container, the paths come from:

`changes` 把每个改动过的路径映射到它当前的内容（`bytes`，或按 UTF-8 编码的 `str`），
被删除的文件映射为 `None`。在任务容器里，路径可以这样获得：

```bash
git -C /testbed diff --name-only HEAD                     # edited and deleted tracked files
git -C /testbed ls-files --others --exclude-standard       # new files, e.g. reproduce.py
```

Read each file's content from the container (it no longer exists if
deleted). With a local checkout, `read_workspace_files(repo_root, paths)`
builds `changes` directly.

再从容器里读取每个文件的内容（被删除的文件读不到，就传 `None`）。如果是本地的代码目录，
可以直接用 `read_workspace_files(repo_root, paths)` 生成 `changes`。

- Always pass **all** files changed since `base_commit` to the **base** index,
  or only the newest changes to the previous result; both give the same index.<br>
  每次可以把从 `base_commit` 起**所有**改动过的文件传给**基准**索引，也可以只把最新的改动传给
  上一次的结果，两种方式得到的索引相同。
- Only the changed files are parsed again (django: about 0.3 s for one file);
  the import graph is re-resolved for the whole repository. The base index is
  not modified.<br>
  只重新解析改动过的文件（django 上更新一个文件约 0.3 秒）；导入关系会对整个仓库重新解析。
  基准索引本身不会被修改。
- A file the agent left with a syntax error appears in `index.errors` and has
  no records, so `find_enclosing` returns `None` for it.<br>
  被 Agent 改出语法错误的文件会出现在 `index.errors` 中，没有记录，`find_enclosing` 对它返回 `None`。
- The result equals a full rebuild from the updated files, with one exception:
  if an `__init__.py` is added or removed, unchanged files get their new module
  names, but their module records' retrieval text keeps the old name.<br>
  结果与用更新后的文件重新完整构建一致，只有一个例外：如果新增或删除了 `__init__.py`，未改动的文件
  会得到新的模块名，但它们模块记录的检索文本里仍是旧的模块名。
- Metadata records `base_index_sha256` (the index before any update) and
  `updated_files` (all paths updated so far).<br>
  元数据记录 `base_index_sha256`（更新前的索引）和 `updated_files`（目前为止更新过的所有路径）。
