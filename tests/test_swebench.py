"""Offline tests for src/repository/swebench.py.

A local git repository stands in for GitHub and a small parquet file for the
SWE-bench dataset, so nothing here touches the network.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.repository import swebench
from src.repository.indexer import build_index

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"
REPO = "acme/shop"
SECRET = "REFERENCE-PATCH-MUST-NOT-LEAK"


def git(cwd: Path, *args: str, input: bytes | None = None) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.autocrlf=false", *args],
        cwd=cwd,
        input=input,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode().strip()


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def remote(tmp_path, monkeypatch):
    """A local stand-in for github.com/acme/shop with two commits."""
    work = tmp_path / "remotes" / "acme" / "shop"
    shutil.copytree(SAMPLE_REPO, work)
    for rel in [".hidden/x.py", "build/lib/x.py", "shop/build/helper.py", "pkg.egg-info/x.py"]:
        (work / rel).parent.mkdir(parents=True, exist_ok=True)
        (work / rel).write_text("x = 1\n", encoding="utf-8")
    git(work, "init", "-q")
    git(work, "config", "uploadpack.allowAnySHA1InWant", "true")
    first = commit_all(work, "first")

    with open(work / "shop" / "pricing.py", "a", encoding="utf-8") as f:
        f.write("\n\ndef added_later():\n    return 1\n")
    second = commit_all(work, "second")

    monkeypatch.setattr(swebench, "GIT_URL", str(tmp_path / "remotes") + "/{repo}")
    return {"work": work, "first": first, "second": second}


@pytest.fixture
def cache(tmp_path):
    return tmp_path / "cache"


# ----- reading source from git -----


def test_commit_index_matches_directory_index(remote, cache):
    git(remote["work"], "checkout", "-q", remote["first"])
    from_git = swebench.build_commit_index(REPO, remote["first"], cache_dir=cache)
    from_dir = build_index(remote["work"])

    assert from_git.digest() == from_dir.digest()
    assert "shop/build/helper.py" in from_git.files  # "build" is only skipped at the root
    assert not any(p.startswith((".hidden/", "build/", "pkg.egg-info/")) for p in from_git.files)
    assert from_git.metadata["commit"] == remote["first"]


def test_index_follows_the_commit(remote, cache):
    first = swebench.build_commit_index(REPO, remote["first"], cache_dir=cache)
    second = swebench.build_commit_index(REPO, remote["second"], cache_dir=cache)
    assert first.find_by_name("added_later") == []
    assert [r.id for r in second.find_by_name("added_later")] == ["shop/pricing.py::added_later"]


def test_commit_made_after_the_clone_is_fetched(remote, cache):
    swebench.build_commit_index(REPO, remote["first"], cache_dir=cache)  # clones
    (remote["work"] / "shop" / "late.py").write_text("def late():\n    pass\n", encoding="utf-8")
    third = commit_all(remote["work"], "third")

    index = swebench.build_commit_index(REPO, third, cache_dir=cache)
    assert index.get("shop/late.py::late") is not None


def test_symlinks_and_submodules_are_skipped(remote, cache):
    work = remote["work"]
    blob = git(work, "hash-object", "-w", "--stdin", input=b"shop/pricing.py")
    git(work, "update-index", "--add", "--cacheinfo", f"120000,{blob},link.py")
    git(work, "update-index", "--add", "--cacheinfo", f"160000,{remote['first']},vendored")
    git(work, "commit", "-q", "-m", "links")
    commit = git(work, "rev-parse", "HEAD")

    index = swebench.build_commit_index(REPO, commit, cache_dir=cache)
    assert "link.py" not in index.files
    assert not any(p.startswith("vendored") for p in index.files)


def test_oversized_files_are_recorded_not_read(remote, cache):
    index = swebench.build_commit_index(REPO, remote["first"], cache_dir=cache, max_file_bytes=200)
    assert ("shop/pricing.py", "too_large") in {(e.path, e.kind) for e in index.errors}


def test_unknown_commit_is_an_error(remote, cache):
    with pytest.raises(RuntimeError):
        swebench.build_commit_index(REPO, "0" * 40, cache_dir=cache)


# ----- tasks -----


@pytest.fixture
def dataset(remote, monkeypatch):
    """Serve a fake dataset that, like the real one, also has evaluation-only columns."""
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    table = pa.table(
        {
            "instance_id": ["acme__shop-1"],
            "repo": [REPO],
            "base_commit": [remote["first"]],
            "problem_statement": ["Cart total is wrong after tax."],
            "version": ["1.0"],
            "created_at": ["2026-01-01T00:00:00Z"],
            "patch": [SECRET],
            "test_patch": [SECRET],
            "FAIL_TO_PASS": [SECRET],
            "PASS_TO_PASS": [SECRET],
            "hints_text": [SECRET],
        }
    )
    downloads = []

    def fake_fetch(url, dest):
        downloads.append(url)
        pq.write_table(table, dest)

    monkeypatch.setattr(swebench, "_fetch", fake_fetch)
    return downloads


def test_load_task_keeps_only_whitelisted_fields(dataset, cache):
    task = swebench.load_task("acme__shop-1", cache)
    assert task.repo == REPO
    assert task.problem_statement == "Cart total is wrong after tax."
    assert not hasattr(task, "patch")

    cached = "".join(p.read_text(encoding="utf-8") for p in (cache / "tasks").iterdir())
    assert SECRET not in cached
    assert not list(cache.rglob("*.parquet"))  # the raw download is deleted

    swebench.load_task("acme__shop-1", cache)
    assert len(dataset) == 1  # served from the cache the second time
    assert swebench.DATASET_REVISION in dataset[0]


def test_unknown_task(dataset, cache):
    with pytest.raises(KeyError):
        swebench.load_task("acme__shop-999", cache)


def test_build_task_index_end_to_end(dataset, cache, monkeypatch):
    index = swebench.build_task_index("acme__shop-1", cache_dir=cache)
    assert index.get("shop/pricing.py::Cart.total") is not None
    assert index.metadata["instance_id"] == "acme__shop-1"
    assert index.metadata["dataset_revision"] == swebench.DATASET_REVISION
    assert index.metadata["index_sha256"] == index.digest()
    assert (cache / "index" / "acme__shop-1.json").exists()

    calls = []
    real_build = swebench.build_commit_index
    monkeypatch.setattr(
        swebench, "build_commit_index", lambda *a, **k: calls.append(1) or real_build(*a, **k)
    )
    assert swebench.build_task_index("acme__shop-1", cache_dir=cache).digest() == index.digest()
    assert calls == []  # cached

    swebench.build_task_index("acme__shop-1", cache_dir=cache, max_text_chars=50)
    swebench.build_task_index("acme__shop-1", cache_dir=cache, max_text_chars=50, rebuild=True)
    assert calls == [1, 1]  # different limits, then an explicit rebuild


# ----- validation and cache location -----


@pytest.mark.parametrize("bad", ["../escape", "a/b", ""])
def test_rejects_unsafe_instance_ids(bad, cache):
    with pytest.raises(ValueError):
        swebench.build_task_index(bad, cache_dir=cache)


def test_rejects_bad_repo_names(cache):
    with pytest.raises(ValueError):
        swebench.ensure_repo("not-a-repo", cache)


def test_cache_dir_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(swebench.CACHE_ENV_VAR, str(tmp_path / "elsewhere"))
    cache = swebench.resolve_cache_dir()
    assert cache == tmp_path / "elsewhere"
    assert (cache / ".gitignore").read_text(encoding="utf-8") == "*\n"


def test_build_time_survives_the_cache(dataset, cache):
    built = swebench.build_task_index("acme__shop-1", cache_dir=cache)
    seconds = built.metadata["build_seconds"]
    assert seconds >= 0
    assert swebench.build_task_index("acme__shop-1", cache_dir=cache).metadata["build_seconds"] == seconds


def test_cache_without_build_time_is_rebuilt(dataset, cache):
    from src.repository.indexer import RepositoryIndex

    built = swebench.build_task_index("acme__shop-1", cache_dir=cache)
    del built.metadata["build_seconds"]
    built.save(cache / "index" / "acme__shop-1.json")
    assert "build_seconds" in swebench.build_task_index("acme__shop-1", cache_dir=cache).metadata
    assert "build_seconds" in RepositoryIndex.load(cache / "index" / "acme__shop-1.json").metadata


def test_run_structural_records_timing(dataset, cache, tmp_path):
    import importlib.util

    from src.localization.structural import structural_ranking

    script = Path(__file__).parents[1] / "scripts" / "run_structural.py"
    spec = importlib.util.spec_from_file_location("run_structural", script)
    run_structural = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_structural)

    lexical = tmp_path / "bm25.json"
    lexical.write_text(
        json.dumps(
            [
                {
                    "instance_id": "acme__shop-1",
                    "ranked_files": [
                        {"rank": 1, "path": "shop/pricing.py", "bm25_score": 3.0},
                        {"rank": 2, "path": "tests/test_pricing.py", "bm25_score": 1.0},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "structural.json"
    run_structural.main(["--lexical", str(lexical), "-o", str(output), "--cache-dir", str(cache)])

    (task,) = json.loads(output.read_text(encoding="utf-8"))
    timing = task["timing"]
    index = swebench.build_task_index("acme__shop-1", cache_dir=cache)
    assert timing["index_build_seconds"] == index.metadata["build_seconds"]
    assert timing["index_load_seconds"] >= 0 and timing["structural_seconds"] >= 0
    assert "Python" in timing["measured_on"]
    expected = structural_ranking(index, [("shop/pricing.py", 3.0), ("tests/test_pricing.py", 1.0)])
    assert [f["file"] for f in task["ranked_files"]] == [c.file for c in expected]
