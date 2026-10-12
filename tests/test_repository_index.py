from pathlib import Path

import pytest

from src.repository.ast_parser import is_test_path, module_name, parse_source
from src.repository.indexer import RepositoryIndex, build_index, to_repo_path
from src.repository.models import MODULE_SYMBOL

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"
PRICING = "shop/pricing.py"


def line_of(text: str, path: str = PRICING) -> int:
    """1-based line number of the first line in a fixture file containing `text`."""
    lines = (SAMPLE_REPO / path).read_text(encoding="utf-8").splitlines()
    return next(i for i, line in enumerate(lines, start=1) if text in line)


@pytest.fixture(scope="module")
def index():
    return build_index(SAMPLE_REPO)


# ----- sample repository -----


def test_indexes_every_file_and_records_the_broken_one(index):
    assert index.files == [
        "shop/__init__.py",
        "shop/broken.py",
        "shop/pricing.py",
        "shop/utils/__init__.py",
        "shop/utils/rounding.py",
        "tests/test_pricing.py",
    ]
    assert [(e.path, e.kind, e.line) for e in index.errors] == [
        ("shop/broken.py", "syntax_error", line_of("def broken(", "shop/broken.py"))
    ]
    assert index.records_in_file("shop/broken.py") == []


def test_symbols_and_kinds(index):
    found = {r.id: r.kind for r in index.records_in_file(PRICING)}
    assert found == {
        "shop/pricing.py": "module",
        "shop/pricing.py::apply_discount": "function",
        "shop/pricing.py::Cart": "class",
        "shop/pricing.py::Cart.__init__": "method",
        "shop/pricing.py::Cart.discount": "method",
        "shop/pricing.py::Cart.discount#2": "method",  # the property setter
        "shop/pricing.py::Cart.total": "method",
        "shop/pricing.py::Cart.total.line_total": "function",  # nested, not a method
        "shop/pricing.py::Cart.checkout": "method",  # async
        "shop/pricing.py::Cart.Receipt": "class",
        "shop/pricing.py::Cart.Receipt.render": "method",
        "shop/pricing.py::describe_tax": "function",  # defined inside `if`
        "shop/pricing.py::describe_tax#2": "function",  # ... and inside `else`
    }


def test_line_ranges_are_one_based_and_inclusive(index):
    total = index.get("shop/pricing.py::Cart.total")
    assert total.start_line == line_of("def total(")
    assert total.end_line == line_of("return round_price(subtotal)")

    setter = index.get("shop/pricing.py::Cart.discount#2")
    assert setter.start_line == line_of("@discount.setter")  # decorators included

    module = index.get(PRICING)
    assert (module.start_line, module.end_line) == (1, line_of('return "no tax"'))


def test_record_fields(index):
    total = index.get("shop/pricing.py::Cart.total")
    assert total.path == PRICING
    assert total.module == "shop.pricing"
    assert total.name == "total"
    assert total.parent == "shop/pricing.py::Cart"
    assert total.signature == "def total(self, with_tax=True)"
    assert total.docstring == "Total price of all items."
    assert total.text.startswith("shop/pricing.py\nCart.total\n    def total(")
    assert "subtotal *= 1 + TAX_RATE" in total.text
    assert not total.is_test

    cart = index.get("shop/pricing.py::Cart")
    assert cart.signature == "class Cart"
    assert "currency" in cart.text and "checkout" in cart.text

    checkout = index.get("shop/pricing.py::Cart.checkout")
    assert checkout.signature == "async def checkout(self, gateway)"

    module = index.get(PRICING)
    assert module.symbol == MODULE_SYMBOL
    assert module.parent is None
    assert "TAX_RATE" in module.text and "Cart" in module.text


def test_empty_file_and_package_module_names(index):
    utils = index.get("shop/utils/__init__.py")
    assert utils.module == "shop.utils"
    assert (utils.start_line, utils.end_line) == (1, 1)
    assert index.records_in_file("shop/utils/__init__.py") == [utils]


def test_test_files_are_flagged(index):
    assert index.get("tests/test_pricing.py::test_apply_discount").is_test
    assert not index.get("shop/utils/rounding.py::round_price").is_test


# ----- lookups -----


def test_find_enclosing_returns_innermost_record(index):
    assert index.find_enclosing(PRICING, line_of("price, quantity = item")).id == (
        "shop/pricing.py::Cart.total.line_total"
    )
    assert index.find_enclosing(PRICING, line_of("subtotal *= 1")).id == (
        "shop/pricing.py::Cart.total"
    )
    assert index.find_enclosing(PRICING, line_of('currency = "SGD"')).id == "shop/pricing.py::Cart"
    assert index.find_enclosing(PRICING, line_of("TAX_RATE = 0.09")).id == PRICING
    # Windows-style paths are normalized.
    assert index.find_enclosing("shop\\pricing.py", 1).id == PRICING


def test_find_enclosing_unknown_file_or_line(index):
    assert index.find_enclosing("shop/missing.py", 1) is None
    assert index.find_enclosing("shop/broken.py", 1) is None
    assert index.find_enclosing(PRICING, 10_000) is None


def test_find_by_name(index):
    assert [r.id for r in index.find_by_name("total")] == ["shop/pricing.py::Cart.total"]
    assert [r.id for r in index.find_by_name("Cart.total")] == ["shop/pricing.py::Cart.total"]
    assert [r.id for r in index.find_by_name("describe_tax")] == [
        "shop/pricing.py::describe_tax",
        "shop/pricing.py::describe_tax#2",
    ]


def test_children(index):
    assert [r.name for r in index.children("shop/pricing.py::Cart")] == [
        "__init__",
        "discount",
        "discount",
        "total",
        "checkout",
        "Receipt",
    ]


# ----- persistence and determinism -----


def test_save_and_load_round_trip(index, tmp_path):
    out = tmp_path / "index.json"
    index.save(out)
    loaded = RepositoryIndex.load(out)
    assert loaded == index
    assert loaded.find_enclosing(PRICING, line_of("subtotal *= 1")).id == (
        "shop/pricing.py::Cart.total"
    )


def test_load_rejects_other_schema_versions(index):
    data = index.to_dict()
    data["schema_version"] = 999
    with pytest.raises(ValueError):
        RepositoryIndex.from_dict(data)


def test_build_is_deterministic(index):
    assert build_index(SAMPLE_REPO).to_dict() == index.to_dict()


# ----- unusual files -----


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_encodings_and_bad_files(tmp_path):
    write(tmp_path / "latin1.py", b"# -*- coding: latin-1 -*-\ndef caf\xe9():\n    pass\n")
    write(tmp_path / "bom.py", b"\xef\xbb\xbfdef f():\n    pass\n")
    write(tmp_path / "bad_utf8.py", b"x = '\xff'\n")
    write(tmp_path / "null.py", b"x = 1\x00\n")
    write(tmp_path / "big.py", b"x = 1\n" * 100)

    index = build_index(tmp_path, max_file_bytes=500)

    assert index.get("latin1.py::café").start_line == 2
    assert index.get("bom.py::f").start_line == 1
    errors = {e.path: e.kind for e in index.errors}
    assert errors == {
        "bad_utf8.py": "decode_error",
        "big.py": "too_large",
        "null.py": "syntax_error",
    }


def test_line_numbers_with_crlf_and_form_feed():
    source = "x = 1\r\n\x0c\r\ndef f():\r\n    return 1\r\n"
    module, f = parse_source(source, "m.py")
    assert (f.start_line, f.end_line) == (3, 4)
    assert module.end_line == 4
    assert f.text.endswith("def f():\n    return 1")


def test_excluded_directories(tmp_path):
    for rel in [
        "pkg/a.py",
        "pkg/build/b.py",  # "build" is only excluded at the root
        "build/lib/pkg/a.py",
        ".git/hooks/x.py",
        ".venv/lib/x.py",
        "pkg/__pycache__/a.py",
        "pkg.egg-info/x.py",
        "pkg/data.txt",
    ]:
        write(tmp_path / rel, b"x = 1\n")
    assert build_index(tmp_path).files == ["pkg/a.py", "pkg/build/b.py"]


def test_text_is_truncated(tmp_path):
    write(tmp_path / "m.py", b'def f():\n    """' + b"word " * 1000 + b'"""\n')
    index = build_index(tmp_path, max_text_chars=100)
    f = index.get("m.py::f")
    assert len(f.text) == 100 and len(f.docstring) == 100


# ----- helpers -----


@pytest.mark.parametrize(
    "path, root, expected",
    [
        ("shop/pricing.py", None, "shop/pricing.py"),
        ("./shop/../shop/pricing.py", None, "shop/pricing.py"),
        ("shop\\pricing.py", None, "shop/pricing.py"),
        ("/testbed/shop/pricing.py", "/testbed", "shop/pricing.py"),
        ("/testbed/shop/pricing.py", "/testbed/", "shop/pricing.py"),
        ("C:\\work\\repo\\shop\\pricing.py", "C:\\work\\repo", "shop/pricing.py"),
        ("/usr/lib/python3.11/json/__init__.py", "/testbed", None),
        ("C:/elsewhere/x.py", None, None),
        ("../outside.py", None, None),
    ],
)
def test_to_repo_path(path, root, expected):
    assert to_repo_path(path, root) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("shop/pricing.py", "shop.pricing"),
        ("shop/__init__.py", "shop"),
        ("setup.py", "setup"),
    ],
)
def test_module_name(path, expected):
    assert module_name(path) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("tests/test_pricing.py", True),
        ("sympy/core/tests/test_basic.py", True),
        ("pkg/conftest.py", True),
        ("pkg/foo_test.py", True),
        ("pkg/contest.py", False),
        ("pkg/testsuite_helpers.py", False),
    ],
)
def test_is_test_path(path, expected):
    assert is_test_path(path) == expected
