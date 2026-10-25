"""Records produced by the repository index.

These are the interface between the indexer (role 2) and its consumers:
lexical retrieval (role 3), failure mapping (role 4), integration (role 1)
and evaluation (role 5).

The first six fields of IndexRecord match `IndexRecord` in
`src/agent/contracts.py` (role 1) in name, order and meaning, so a record
built by the indexer can be used wherever that contract is expected.

Conventions
-----------
* ``path`` is relative to the repository root and always uses ``/``.
* Line numbers are 1-based and inclusive, matching Python tracebacks.
  ``start_line`` includes decorators, so a traceback line pointing at a
  decorator still maps to the decorated function.
* ``symbol`` is the dotted name inside the file (``Cart.total``,
  ``Cart.total.line_total``), or None for module records.
"""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = 4

# Values of IndexRecord.symbol_type.
MODULE = "module"
CLASS = "class"
FUNCTION = "function"  # module-level or nested inside another function
METHOD = "method"  # defined directly in a class body
SYMBOL_TYPES = (MODULE, CLASS, FUNCTION, METHOD)

# Values of ParseError.kind.
SYNTAX_ERROR = "syntax_error"
DECODE_ERROR = "decode_error"
TOO_LARGE = "too_large"
READ_ERROR = "read_error"
RECURSION_ERROR = "recursion_error"


@dataclass(frozen=True)
class IndexRecord:
    """One code entity: a module, class, function or method."""

    # --- Shared with src/agent/contracts.py (role 1) ---
    path: str  # "shop/pricing.py"
    symbol: str | None  # "Cart.total"; None for modules
    symbol_type: str  # one of SYMBOL_TYPES
    start_line: int | None  # always set by the indexer
    end_line: int | None  # always set by the indexer
    retrieval_text: str = ""  # path, symbol and selected source, truncated

    # --- Filled by the indexer ---
    id: str = ""  # "<path>" for modules, "<path>::<symbol>" otherwise; "#2", "#3"... on redefinition
    module: str = ""  # dotted module name derived from the path, "shop.pricing"
    name: str | None = None  # last component of symbol, "total"; None for modules
    parent: str | None = None  # id of the enclosing record; None for modules
    signature: str = ""  # "def total(self, with_tax=True)", "class Cart(Base)", "" for modules
    docstring: str = ""
    is_test: bool = False  # heuristic: the file looks like test code

    def __post_init__(self) -> None:
        # Records built by hand (e.g. in other roles' tests) get the same
        # derived fields the indexer would give them.
        if not self.id:
            object.__setattr__(self, "id", f"{self.path}::{self.symbol}" if self.symbol else self.path)
        if self.name is None and self.symbol:
            object.__setattr__(self, "name", self.symbol.rsplit(".", 1)[-1])

    def contains(self, line: int) -> bool:
        if self.start_line is None or self.end_line is None:
            return False
        return self.start_line <= line <= self.end_line


@dataclass(frozen=True)
class ParseError:
    """A Python file that could not be indexed. It contributes no records."""

    path: str
    kind: str  # SYNTAX_ERROR, DECODE_ERROR, TOO_LARGE, READ_ERROR or RECURSION_ERROR
    message: str
    line: int | None = None
