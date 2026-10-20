from pathlib import Path

import pytest

from src.repository.ast_parser import module_names
from src.repository.indexer import build_index

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def write_repo(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


def test_sample_repo_imports():
    index = build_index(SAMPLE_REPO)
    assert index.imports == {
        "shop/pricing.py": ["shop/utils/rounding.py"],
        "tests/test_pricing.py": ["shop/pricing.py"],
    }
    assert index.imported_by("shop/pricing.py") == ["tests/test_pricing.py"]
    assert index.neighbors("shop/pricing.py") == ["shop/utils/rounding.py", "tests/test_pricing.py"]
    assert index.metadata["num_import_edges"] == 2


def test_module_names_follow_packages():
    names = module_names(
        [
            "src/pkg/__init__.py",
            "src/pkg/core.py",
            "src/pkg/sub/__init__.py",
            "src/pkg/sub/helpers.py",
            "testing/test_core.py",
            "setup.py",
        ]
    )
    assert names == {
        "src/pkg/__init__.py": "pkg",  # src layout: "src" is not a package
        "src/pkg/core.py": "pkg.core",
        "src/pkg/sub/__init__.py": "pkg.sub",
        "src/pkg/sub/helpers.py": "pkg.sub.helpers",
        "testing/test_core.py": "test_core",  # non-package test directory
        "setup.py": "setup",
    }


@pytest.fixture
def src_layout(tmp_path):
    write_repo(
        tmp_path,
        {
            "src/pkg/__init__.py": "from .core import Engine\n",
            "src/pkg/core.py": (
                "import os\n"
                "from . import util\n"
                "from .sub import helpers\n"
                "from pkg.sub.helpers import helper as h\n"
                "class Engine: pass\n"
            ),
            "src/pkg/util.py": (
                "from pkg import util as _self\n"  # self-import is dropped
                "def f():\n"
                "    from .sub.helpers import helper\n"  # import inside a function
                "    return helper\n"
                "try:\n"
                "    import numpy\n"  # external: dropped
                "except ImportError:\n"
                "    pass\n"
            ),
            "src/pkg/sub/__init__.py": "from ..util import *\n",
            "src/pkg/sub/helpers.py": (
                "from ... import nothing\n"  # beyond the top-level package: dropped
                "import pkg\n"
                "import pkg.core\n"
                "def helper(): pass\n"
            ),
            "testing/test_core.py": "from pkg.core import Engine\nfrom pkg import util\n",
            "testing/conftest.py": "",
            "other/conftest.py": "",
            "scripts/run.py": "import conftest\n",  # ambiguous: two top-level conftest modules
        },
    )
    return build_index(tmp_path)


def test_resolves_relative_absolute_and_star_imports(src_layout):
    assert src_layout.imports == {
        "src/pkg/__init__.py": ["src/pkg/core.py"],
        "src/pkg/core.py": ["src/pkg/sub/helpers.py", "src/pkg/util.py"],
        "src/pkg/sub/__init__.py": ["src/pkg/util.py"],
        "src/pkg/sub/helpers.py": ["src/pkg/__init__.py", "src/pkg/core.py"],
        "src/pkg/util.py": ["src/pkg/sub/helpers.py"],
        "testing/test_core.py": ["src/pkg/core.py", "src/pkg/util.py"],
    }


def test_record_module_names_use_the_import_name(src_layout):
    assert src_layout.get("src/pkg/core.py::Engine").module == "pkg.core"


def test_imported_by_and_neighbors(src_layout):
    assert src_layout.imported_by("src/pkg/util.py") == [
        "src/pkg/core.py",
        "src/pkg/sub/__init__.py",
        "testing/test_core.py",
    ]
    assert src_layout.neighbors("src/pkg/util.py") == [
        "src/pkg/core.py",
        "src/pkg/sub/__init__.py",
        "src/pkg/sub/helpers.py",
        "testing/test_core.py",
    ]
    assert src_layout.neighbors("unknown.py") == []


def test_package_wins_over_module_of_the_same_name(tmp_path):
    write_repo(
        tmp_path,
        {"thing.py": "", "thing/__init__.py": "", "main.py": "import thing\n"},
    )
    assert build_index(tmp_path).imports == {"main.py": ["thing/__init__.py"]}


def test_files_that_fail_to_parse_can_still_be_import_targets(tmp_path):
    write_repo(tmp_path, {"broken.py": "def (:\n", "main.py": "import broken\n"})
    index = build_index(tmp_path)
    assert index.imports == {"main.py": ["broken.py"]}
    assert [e.path for e in index.errors] == ["broken.py"]
