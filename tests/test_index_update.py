"""RepositoryIndex.with_updated_files: keeping the index in step with an agent's edits."""

import shutil
from pathlib import Path

import pytest

from src.repository.indexer import build_index, read_workspace_files

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def line_of(path: Path, text: str) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(i for i, line in enumerate(lines, start=1) if text in line)


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(SAMPLE_REPO, root)
    return root


def edit_like_an_agent(root: Path) -> list[str]:
    """Typical edits during a run; returns the paths `git status` would report."""
    pricing = root / "shop" / "pricing.py"
    text = pricing.read_text(encoding="utf-8")
    # Five new lines above Cart shift every later line number.
    text = text.replace("class Cart:", "# a\n# b\n# c\n# d\n# e\nclass Cart:")
    text = text.replace("from shop.utils.rounding import round_price", "from .utils import rounding\nfrom shop.utils.rounding import round_price")
    pricing.write_text(text, encoding="utf-8")
    (root / "shop" / "utils" / "rounding.py").write_text("def round_price(:\n", encoding="utf-8")  # mid-edit
    (root / "shop" / "broken.py").write_text("def fixed():\n    return 1\n", encoding="utf-8")  # now valid
    (root / "tests" / "test_pricing.py").unlink()
    (root / "reproduce.py").write_text("from shop.pricing import Cart\nprint(Cart().total())\n", encoding="utf-8")
    (root / "notes.txt").write_text("not python", encoding="utf-8")
    return [
        "shop/pricing.py",
        "shop/utils/rounding.py",
        "shop/broken.py",
        "tests/test_pricing.py",
        "reproduce.py",
        "notes.txt",
    ]


def test_update_equals_full_rebuild(workspace):
    base = build_index(workspace)
    changed = edit_like_an_agent(workspace)

    updated = base.with_updated_files(read_workspace_files(workspace, changed))
    rebuilt = build_index(workspace)

    assert updated.digest() == rebuilt.digest()
    assert updated.files == rebuilt.files
    assert updated.imports == rebuilt.imports
    assert [(e.path, e.kind) for e in updated.errors] == [("shop/utils/rounding.py", "syntax_error")]
    assert "reproduce.py" in updated.files and "notes.txt" not in updated.files
    assert "tests/test_pricing.py" not in updated.files
    assert updated.imports["reproduce.py"] == ["shop/pricing.py"]


def test_traceback_lines_map_to_the_edited_code(workspace):
    base = build_index(workspace)
    changed = edit_like_an_agent(workspace)
    updated = base.with_updated_files(read_workspace_files(workspace, changed))

    line = line_of(workspace / "shop" / "pricing.py", "subtotal *= 1 + TAX_RATE")
    assert updated.find_enclosing("shop/pricing.py", line).id == "shop/pricing.py::Cart.total"
    # The base index, built before the edit, points five lines off.
    assert base.find_enclosing("shop/pricing.py", line).id != "shop/pricing.py::Cart.total"


def test_base_index_is_left_unchanged(workspace):
    base = build_index(workspace)
    digest = base.digest()
    base.with_updated_files(read_workspace_files(workspace, edit_like_an_agent(workspace)))
    assert base.digest() == digest


def test_metadata_tracks_the_base_and_accumulates_updates(workspace):
    base = build_index(workspace)
    first = base.with_updated_files({"a.py": "x = 1\n"})
    second = first.with_updated_files({"b.py": b"y = 2\n"})

    assert first.metadata["base_index_sha256"] == base.digest()
    assert second.metadata["base_index_sha256"] == base.digest()
    assert second.metadata["updated_files"] == ["a.py", "b.py"]
    assert second.metadata["num_files"] == len(base.files) + 2


def test_index_sha256_follows_the_content_when_present(workspace):
    base = build_index(workspace)
    base.metadata["index_sha256"] = base.digest()
    updated = base.with_updated_files({"a.py": "x = 1\n"})
    assert updated.metadata["index_sha256"] == updated.digest() != base.digest()


def test_new_package_resolves_imports_of_unchanged_files(tmp_path):
    root = tmp_path / "repo"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "a.py").write_text("from . import b\n", encoding="utf-8")
    (root / "src" / "pkg" / "b.py").write_text("", encoding="utf-8")
    base = build_index(root)
    assert base.imports == {}  # no __init__.py yet: `from . import b` resolves to nothing

    (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    updated = base.with_updated_files(read_workspace_files(root, ["src/pkg/__init__.py"]))
    rebuilt = build_index(root)

    assert updated.imports == rebuilt.imports == {"src/pkg/a.py": ["src/pkg/b.py"]}
    assert [(r.id, r.module) for r in updated.records] == [(r.id, r.module) for r in rebuilt.records]


def test_paths_are_normalized_and_must_stay_inside_the_repo(workspace):
    base = build_index(workspace)
    updated = base.with_updated_files({"shop\\new.py": "def f():\n    pass\n"})
    assert updated.get("shop/new.py::f") is not None
    with pytest.raises(ValueError):
        base.with_updated_files({"../outside.py": "x = 1\n"})
    with pytest.raises(ValueError):
        read_workspace_files(workspace, ["/elsewhere/x.py"])


def test_size_limit_applies_to_updates(workspace):
    base = build_index(workspace, max_file_bytes=1000)
    updated = base.with_updated_files({"big.py": "x = 1\n" * 500})
    assert ("big.py", "too_large") in {(e.path, e.kind) for e in updated.errors}


def test_read_workspace_files_accepts_absolute_paths(workspace):
    changes = read_workspace_files(workspace, [str(workspace / "shop" / "pricing.py"), "gone.py"])
    assert set(changes) == {"shop/pricing.py", "gone.py"}
    assert changes["gone.py"] is None


def test_chained_updates_equal_one_update_from_the_base(workspace):
    base = build_index(workspace)
    first = {"shop/pricing.py": "def a():\n    pass\n", "new.py": "import shop.pricing\n"}
    second = {"shop/pricing.py": "\n\ndef b():\n    pass\n", "new.py": None}

    chained = base.with_updated_files(first).with_updated_files(second)
    at_once = base.with_updated_files({**first, **second})
    assert chained.digest() == at_once.digest()
    assert chained.find_enclosing("shop/pricing.py", 3).id == "shop/pricing.py::b"
