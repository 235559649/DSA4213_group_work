# Repository index coverage (development set) / 仓库索引覆盖情况（开发集）

Role 2, round 5 check: does the index cover every Python file of the 20
development tasks at their `base_commit`, and how many files could not be
indexed? Generated on 2026-10-25 with index schema 4.

2 号第 5 轮检查：在 20 个开发任务的 `base_commit` 上，索引是否覆盖了全部 Python 文件，
有多少文件无法索引？2026-10-25 用第 4 版索引格式生成。

Reproduce / 复现：

```bash
python scripts/index_coverage.py --tasks-from experiments/bm25_results.json --rebuild
```

## Summary / 结论

- **27,484 Python files, 528,100 records (modules, classes, functions, methods)
  across 20 tasks; 1 file could not be indexed.**<br>
  **20 个任务共 27,484 个 Python 文件、528,100 条记录（模块、类、函数、方法）；只有 1 个文件无法索引。**
- The one failure is `tests/test_runner_apps/tagged/tests_syntax_error.py` in
  django-14539, a file in Django's own test suite that is **invalid on purpose**
  (Django tests how it reports syntax errors). The indexer recorded it as
  `syntax_error` and continued, as designed. It is a test fixture, not a
  localization target.<br>
  唯一的失败是 django-14539 中的 `tests/test_runner_apps/tagged/tests_syntax_error.py`，这是 Django
  测试套件里**故意写错语法**的文件（Django 用它测试自己如何报告语法错误）。索引器按设计把它记为
  `syntax_error` 并继续，它是测试样例，不是定位目标。
- No decode errors, oversized files or unreadable files. Every task's index is
  identified by `index_sha256` in `experiments/structural_results.json`.<br>
  没有编码错误、超大文件或读取失败。每个任务的索引都以 `experiments/structural_results.json` 中的
  `index_sha256` 作为身份标识。
- Test files are a large share of each repository (django about 68%, sympy
  about 43%, sphinx about 64%, pytest about 63%). The structural ranking does
  not count them as neighbors; how retrieval treats them is role 3's choice.<br>
  测试文件在各仓库中占比很高（django 约 68%，sympy 约 43%，sphinx 约 64%，pytest 约 63%）。
  结构排名不把它们算作邻居；检索如何处理它们由 3 号决定。
- Building an index from git takes 1–5 s for pytest, sphinx and django and
  about 14–15 s for sympy, whose index files are also the largest (about 40 MB).
  Cached indexes load in well under a second.<br>
  从 git 构建索引：pytest、sphinx、django 需 1–5 秒，sympy 约 14–15 秒，其索引文件也最大（约 40 MB）。
  已缓存的索引加载不到 1 秒。
- The largest Python source tree is 29.9 MB (sympy-23262), within the 64 MB
  snapshot limit Condition D uses when it reads the task container.<br>
  最大的 Python 源码树为 29.9 MB（sympy-23262），在条件 D 读取任务容器时使用的 64 MB 快照上限以内。

## Per task / 各任务明细

Columns: Python files indexed; test files (`is_test`); total Python source;
index records and how many are classes and functions/methods; files that could
not be indexed; resolved internal import edges; size of the cached index JSON;
time to rebuild the index from the local clone.

各列：已索引的 Python 文件数；测试文件数（`is_test`）；Python 源码总大小；索引记录数及其中的类、
函数/方法数；无法索引的文件；解析出的仓库内部导入边数；缓存的索引 JSON 大小；从本地 clone 重建索引的耗时。

| Task | Commit | .py files | Test files | Source (MB) | Records | Classes | Functions / methods | Parse errors | Import edges | Index JSON (MB) | Build (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| django__django-11133 | `879cc3da62` | 2545 | 1726 | 12.6 | 34433 | 8419 | 23469 | 0 | 7237 | 29.7 | 4.0 |
| django__django-12262 | `69331bb851` | 2588 | 1762 | 13.0 | 35571 | 8751 | 24232 | 0 | 7442 | 30.7 | 4.0 |
| django__django-13158 | `7af8f41273` | 2647 | 1802 | 13.5 | 36542 | 9071 | 24824 | 0 | 7606 | 31.8 | 4.3 |
| django__django-13417 | `71ae1ab012` | 2672 | 1822 | 13.6 | 36845 | 9137 | 25036 | 0 | 7673 | 32.1 | 4.4 |
| django__django-14017 | `466920f6d7` | 2684 | 1832 | 13.9 | 37462 | 9310 | 25468 | 0 | 7707 | 32.6 | 4.5 |
| django__django-14539 | `6a5ef557f8` | 2696 | 1842 | 14.1 | 38090 | 9448 | 25947 | tests/test_runner_apps/tagged/tests_syntax_error.py (syntax_error) | 7817 | 33.2 | 4.6 |
| sympy__sympy-23262 | `fdc707f73a` | 1544 | 665 | 29.9 | 45723 | 2091 | 42088 | 0 | 13274 | 45.4 | 15.3 |
| sympy__sympy-17630 | `58e78209c8` | 1337 | 570 | 26.2 | 40641 | 1790 | 37514 | 0 | 8086 | 39.4 | 13.9 |
| sympy__sympy-21379 | `624217179a` | 1505 | 647 | 28.6 | 44198 | 2003 | 40690 | 0 | 9003 | 43.3 | 14.4 |
| sympy__sympy-19346 | `94fb720696` | 1397 | 605 | 27.3 | 41941 | 1864 | 38680 | 0 | 8331 | 40.9 | 13.7 |
| sympy__sympy-20154 | `bdb49c4abf` | 1438 | 624 | 27.9 | 42960 | 1950 | 39572 | 0 | 8675 | 41.9 | 14.0 |
| sympy__sympy-20438 | `33b47e4bd6` | 1449 | 626 | 28.1 | 43231 | 1968 | 39814 | 0 | 8687 | 42.2 | 14.3 |
| sphinx-doc__sphinx-8595 | `b19bce971e` | 530 | 341 | 3.8 | 7459 | 987 | 5942 | 0 | 1296 | 6.6 | 1.2 |
| sphinx-doc__sphinx-7462 | `b3e26a6c85` | 487 | 300 | 3.5 | 6812 | 869 | 5456 | 0 | 1245 | 6.0 | 1.1 |
| sphinx-doc__sphinx-9673 | `5fb51fb146` | 548 | 364 | 3.6 | 7667 | 1025 | 6094 | 0 | 1274 | 6.8 | 1.2 |
| sphinx-doc__sphinx-8721 | `82ef497a8c` | 534 | 345 | 3.8 | 7496 | 990 | 5972 | 0 | 1304 | 6.7 | 1.2 |
| pytest-dev__pytest-7571 | `422685d0bd` | 215 | 135 | 2.3 | 5186 | 575 | 4396 | 0 | 617 | 5.0 | 0.8 |
| pytest-dev__pytest-7205 | `5e7f1ab4bf` | 210 | 130 | 2.1 | 5004 | 547 | 4247 | 0 | 500 | 4.7 | 0.7 |
| pytest-dev__pytest-7490 | `7f7a36478a` | 214 | 134 | 2.3 | 5174 | 575 | 4385 | 0 | 618 | 5.0 | 0.8 |
| pytest-dev__pytest-10356 | `3c1534944c` | 244 | 159 | 2.5 | 5665 | 619 | 4802 | 0 | 740 | 5.5 | 0.8 |

Build times were measured on one Windows laptop with Python 3.14 and are
indicative only.

构建耗时在一台 Windows 笔记本上用 Python 3.14 测得，仅供参考。

## Limits / 局限

- The index covers files tracked in git at `base_commit`. Files generated when
  the task environment is installed (for example a setuptools-scm
  `_version.py`) are not indexed. Condition D, which reads the container,
  does see them.<br>
  索引覆盖的是 `base_commit` 时 git 跟踪的文件。任务环境安装时生成的文件（例如 setuptools-scm 生成的
  `_version.py`）不在索引中；条件 D 读取的是容器，能看到这些文件。
- Files are parsed with the Python running the indexer (3.10 or newer), not the
  task's interpreter (3.6–3.9). Syntax removed in newer Python would show up as
  `syntax_error`; none occurred in these 20 tasks.<br>
  文件由运行索引器的 Python（3.10 及以上）解析，而不是任务自己的解释器（3.6–3.9）。新版 Python
  中已移除的语法会被记为 `syntax_error`；这 20 个任务中没有出现。
