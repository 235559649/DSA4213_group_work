# Group 25: SWE-bench Verified Candidate Pool

## 1. Dataset and Selection

- Dataset: `SWE-bench/SWE-bench_Verified`, `default/test`.
- Revision: `78f471bf655a3137b2e8a75af1501690ec009ec3`.
- Pool: 20 development candidates: Django 6, SymPy 6, Sphinx 4, pytest 4. The original 12 are retained and eight are added.
- This completes the development shortlist; the separate held-out evaluation set remains to be selected.
- Selection uses original issue descriptions, metadata and environment manifests. Reference patches, hidden tests and `hints_text` were excluded.
- Keep original task inputs unchanged across A-D.

[Dataset source](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/tree/78f471bf655a3137b2e8a75af1501690ec009ec3)

## 2. Environment

Use a fixed runner, Agent, model, evaluation harness and resource policy. Preserve each task's specified Python and dependencies; A-D must start from the same clean environment for that task.

Inspected manifests list Python 3.6.13 for Django 11133, 12262, 13158 and 13417; Python 3.8.20 for Django 14017 and 14539; and Python 3.9.20 for the other 14. Actual container versions and compatibility remain unverified.

[Manifest source](https://github.com/SWE-bench/SWE-bench/tree/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/swebench/resources/swebench-og)

## 3. Shared Records

| Field | Value |
|---|---|
| `intended_use` | `development_candidate` |
| `selection_status` | `shortlist_complete` |
| `environment_manifest_status` | `inspected` |
| `environment_check_status` | `not_checked` |
| `evaluation_status` | `not_run` |
| `exclusion_reason` | `null` |
| `has_localization_hint` | `yes` for all 20; annotation proposed |

Hints include explicit locations, identifiers, traceback frames or reproduction code. Each task's hint basis is noted below. This pool is not balanced for hint/no-hint analysis.

`version` is the dataset's repository version group; `base_commit` pins the source. `difficulty` is an official estimate of human repair time, not an Agent budget. [Difficulty definition](https://openai.com/index/introducing-swe-bench-verified/)

## 4. Django (`django/django`)

### django__django-11133

- **Base commit:** `879cc3da6249e920b8d54518a0ae06de835d7373`; **version:** `3.0`; **difficulty:** `<15 min fix`.
- **Issue:** HttpResponse returns a memory description instead of bytes for memoryview input.
- **Reason:** Small reproduction for lexical localization and the repair/evaluation workflow.
- **Hint basis:** HttpResponse and input examples. **Check:** The direct memoryview example may avoid an external database.

### django__django-12262

- **Base commit:** `69331bb851c34f05bc77e9fc24020fe6908b9cd5`; **version:** `3.1`; **difficulty:** `15 min - 1 hour`.
- **Issue:** Template tags reject valid keyword-only arguments and report duplicate arguments incorrectly.
- **Reason:** Connects template calls with Python argument handling.
- **Hint basis:** simple_tag definitions and template examples. **Check:** Both simple and inclusion tags.

### django__django-13158

- **Base commit:** `7af8f4127397279d19ef7c7899e93018274e2f9b`; **version:** `3.2`; **difficulty:** `15 min - 1 hour`.
- **Issue:** An empty form submission selects all objects when its queryset uses union().
- **Reason:** Covers interaction between forms, queries and model relations.
- **Hint basis:** QuerySet.none(), ModelForm and union() examples. **Check:** Database state and form submission.

### django__django-13417

- **Base commit:** `71ae1ab0123582cc5bfe0f7d5f4cc19a9412f396`; **version:** `3.2`; **difficulty:** `<15 min fix`.
- **Issue:** QuerySet.ordered stays True after aggregation removes SQL ordering.
- **Reason:** Compares query metadata with generated SQL, useful for lexical and structural localization checks.
- **Hint basis:** ordered, Meta.ordering and SQL examples. **Check:** Use the task's database configuration.

### django__django-14017

- **Base commit:** `466920f6d726eee90d5566e0a9948e92b33a122e`; **version:** `4.0`; **difficulty:** `15 min - 1 hour`.
- **Issue:** Q() & Exists() raises TypeError, while the reverse order works.
- **Reason:** Short traceback for failure mapping and expression-component interaction.
- **Hint basis:** query_utils.py, __and__ and _combine. **Check:** Both operand orders and the specified model/database setup.

### django__django-14539

- **Base commit:** `6a5ef557f80a8eb6a758ebe99c8bb477ca47459e`; **version:** `4.0`; **difficulty:** `<15 min fix`.
- **Issue:** urlize() mishandles HTML-escaped text with trailing punctuation.
- **Reason:** Adds a text-processing case with precise expected output.
- **Hint basis:** urlize() and HTML examples. **Check:** Escaping and punctuation; the reproduction is local string processing.

## 5. SymPy (`sympy/sympy`)

### sympy__sympy-23262

- **Base commit:** `fdc707f73a65a429935c01532cd3970d3355eab6`; **version:** `1.11`; **difficulty:** `15 min - 1 hour`.
- **Issue:** Generated code loses the comma in a one-element tuple, returning an integer.
- **Reason:** Connects the lambdify entry point with code printing.
- **Hint basis:** lambdify and generated-code examples. **Check:** One-element and multi-element tuples.

### sympy__sympy-17630

- **Base commit:** `58e78209c8577b9890e957b624466e5beed7eb08`; **version:** `1.5`; **difficulty:** `1-4 hours`.
- **Issue:** Repeated multiplication of BlockMatrix objects with zero blocks raises AttributeError.
- **Reason:** Provides a multi-layer traceback for failure extraction and source mapping.
- **Hint basis:** blockmatrix.py, strategies/core.py and Zero/ZeroMatrix. **Check:** Matrix behavior; this has a higher human difficulty label.

### sympy__sympy-21379

- **Base commit:** `624217179aaf8d094e6ff75b7493ad1ee47599b0`; **version:** `1.9`; **difficulty:** `15 min - 1 hour`.
- **Issue:** subs() raises PolynomialError for certain expressions; cache state affects reproduction.
- **Reason:** Tests reliable reproduction and recording of state-sensitive failures.
- **Hint basis:** clear_cache, Piecewise and subs() examples. **Check:** Cache reset and execution order; the minimal example uses SymPy alone.

### sympy__sympy-19346

- **Base commit:** `94fb720696f5f5d12bad8bc813699fd696afd2fb`; **version:** `1.7`; **difficulty:** `15 min - 1 hour`.
- **Issue:** srepr() handles symbols in lists/tuples but prints them incorrectly in dictionaries/sets.
- **Reason:** Covers container-specific printing and entity retrieval.
- **Hint basis:** srepr() examples for four container types. **Check:** Distinguish representation errors from set-order differences.

### sympy__sympy-20154

- **Base commit:** `bdb49c4abfb35554a3c8ce761696ffff3bb837fe`; **version:** `1.7`; **difficulty:** `15 min - 1 hour`.
- **Issue:** partitions() reuses output dictionaries, producing unexpected stored results.
- **Reason:** Adds an iterator-state and shared-object case.
- **Hint basis:** sympy.utilities.iterables and a suggested dictionary copy. **Check:** Supply valid arguments and inspect multiple stored outputs.

### sympy__sympy-20438

- **Base commit:** `33b47e4bd60e2302e42616141e76285038b724d6`; **version:** `1.8`; **difficulty:** `15 min - 1 hour`.
- **Issue:** Set subset checks are inconsistent, and simplifying equality raises AttributeError.
- **Reason:** Combines incorrect results with a traceback across several modules.
- **Hint basis:** ProductSet, FiniteSet and basic/simplify/relational frames. **Check:** Preserve the distinction between unknown and false results.

## 6. Sphinx (`sphinx-doc/sphinx`)

### sphinx-doc__sphinx-8595

- **Base commit:** `b19bce971e82f2497d67fdacdeca8db08ae0ba56`; **version:** `3.5`; **difficulty:** `<15 min fix`.
- **Issue:** autodoc displays module members despite an empty __all__.
- **Reason:** Small example for lexical localization and document-output validation.
- **Hint basis:** __all__, automodule and autodoc examples. **Check:** Build and inspect the generated documentation.

### sphinx-doc__sphinx-7462

- **Base commit:** `b3e26a6c851133b82b50f4b68b53692076574d13`; **version:** `3.1`; **difficulty:** `<15 min fix`.
- **Issue:** Tuple[()] annotations cause IndexError during document generation.
- **Reason:** Short traceback for checking failure-to-source mapping.
- **Hint basis:** sphinx/domains/python.py and unparse. **Check:** Historical typing and documentation dependencies.

### sphinx-doc__sphinx-9673

- **Base commit:** `5fb51fb1467dc5eea7505402c3c5d9b378d3b441`; **version:** `4.3`; **difficulty:** `15 min - 1 hour`.
- **Issue:** Return types disappear when autodoc settings are combined with Napoleon.
- **Reason:** Covers interaction between two documentation extensions.
- **Hint basis:** Configuration, extension names and docstring examples. **Check:** Enable both extensions and inspect the output.

### sphinx-doc__sphinx-8721

- **Base commit:** `82ef497a8c88f0f6e50d84520e7276bfbf65025d`; **version:** `3.5`; **difficulty:** `<15 min fix`.
- **Issue:** Building HTML then EPUB creates EPUB source pages despite viewcode_enable_epub=False.
- **Reason:** Covers extension/builder interaction and state across builds.
- **Hint basis:** viewcode configuration and make html epub. **Check:** Build both formats in order and inspect EPUB contents.

## 7. pytest (`pytest-dev/pytest`)

### pytest-dev__pytest-7571

- **Base commit:** `422685d0bdc110547535036c1ff398b5e1c44145`; **version:** `6.0`; **difficulty:** `15 min - 1 hour`.
- **Issue:** caplog changes leak into the next test instead of restoring the log level.
- **Reason:** Covers state restoration and regression checks across tests.
- **Hint basis:** caplog.set_level and two test examples. **Check:** Preserve test order.

### pytest-dev__pytest-7205

- **Base commit:** `5e7f1ab4bf58e473e5d7f878eb2b499d7deabd29`; **version:** `5.4`; **difficulty:** `<15 min fix`.
- **Issue:** Bytes parameters with --setup-show trigger BytesWarning under Python -bb.
- **Reason:** Traceback covers both project and dependency code, useful for failure mapping.
- **Hint basis:** setuponly.py frames and a suggested change. **Check:** Preserve -bb and --setup-show.

### pytest-dev__pytest-7490

- **Base commit:** `7f7a36478abe7dd1fa993b115d22606aa0e35e88`; **version:** `6.0`; **difficulty:** `15 min - 1 hour`.
- **Issue:** Dynamically added xfail marks no longer handle test failures correctly.
- **Reason:** Covers interaction between test marks, execution and reporting.
- **Hint basis:** request.node.add_marker, xfail and test output. **Check:** The assertion failure is intentional; validate its classification.

### pytest-dev__pytest-10356

- **Base commit:** `3c1534944cbd34e8a41bc9e76818018fadefc9a1`; **version:** `7.2`; **difficulty:** `1-4 hours`.
- **Issue:** Test classes with multiple marked base classes lose inherited marks.
- **Reason:** Checks class indexing and mark collection; the current structural method does not resolve MRO.
- **Hint basis:** pytestmark, __mro__ and a metaclass workaround. **Check:** Adapt reproduction syntax to the task interpreter and verify all inherited marks.

Include `src/_pytest` as framework source in the repository index.
