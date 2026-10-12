"""Records produced by the repository index.

These are the interface between the indexer (role 2) and its consumers:
lexical retrieval (role 3), failure mapping (role 4) and evaluation (role 5).

Conventions
-----------
* ``path`` is relative to the repository root and always uses ``/``.
* Line numbers are 1-based and inclusive, matching Python tracebacks.
  ``start_line`` includes decorators, so a traceback line pointing at a
  decorator still maps to the decorated function.
* ``symbol`` is the dotted name inside the file (``Cart.total``,
  ``Cart.total.line_total``). Module records use ``<module>``, the same
  name tracebacks print for module-level code.
"""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = 1

MODULE_SYMBOL = "<module>"

# Kinds of index records.
MODULE = "module"
CLASS = "class"
FUNCTION = "function"  # module-level or nested inside another function
METHOD = "method"  # defined directly in a class body
KINDS = (MODULE, CLASS, FUNCTION, METHOD)

# Kinds of parse errors.
SYNTAX_ERROR = "syntax_error"
DECODE_ERROR = "decode_error"
TOO_LARGE = "too_large"
READ_ERROR = "read_error"
RECURSION_ERROR = "recursion_error"


@dataclass(frozen=True)
class IndexRecord:
    """One code entity: a module, class, function or method."""

    id: str  # "<path>" for modules, "<path>::<symbol>" otherwise; "#2", "#3"... on redefinition
    path: str  # "shop/pricing.py"
    module: str  # dotted module name derived from the path, "shop.pricing"
    symbol: str  # "Cart.total", or "<module>"
    name: str  # last component of symbol, "total"
    kind: str  # one of KINDS
    start_line: int
    end_line: int
    parent: str | None  # id of the enclosing record; None for modules
    signature: str  # "def total(self, with_tax=True)", "class Cart(Base)", "" for modules
    docstring: str
    text: str  # retrieval text: path, symbol and selected source, truncated
    is_test: bool  # heuristic: the file looks like test code

    def contains(self, line: int) -> bool:
        return self.start_line <= line <= self.end_line


@dataclass(frozen=True)
class ParseError:
    """A Python file that could not be indexed. It contributes no records."""

    path: str
    kind: str  # SYNTAX_ERROR, DECODE_ERROR, TOO_LARGE, READ_ERROR or RECURSION_ERROR
    message: str
    line: int | None = None
