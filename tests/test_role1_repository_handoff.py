from src.repository.indexer import (
    RepositoryIndex,
    build_index,
)


def test_repository_index_runtime_handoff(
    tmp_path,
):
    """
    Role 1 / Role 2 integration contract.

    Verify that Role 1 can:
    - build a RepositoryIndex,
    - map source locations,
    - update the index after agent edits,
    - persist and reload the updated index.
    """

    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "a.py").write_text(
        "import b\n"
        "\n"
        "def f():\n"
        "    return b.g()\n",
        encoding="utf-8",
    )

    (repo / "b.py").write_text(
        "def g():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    base = build_index(repo)

    assert base.files == [
        "a.py",
        "b.py",
    ]

    assert base.imports == {
        "a.py": ["b.py"],
    }

    assert (
        base.find_enclosing(
            "a.py",
            4,
        ).symbol
        == "f"
    )

    updated_source = (
        "import b\n"
        "\n"
        "# inserted 1\n"
        "# inserted 2\n"
        "# inserted 3\n"
        "def f():\n"
        "    return b.g()\n"
    )

    updated = base.with_updated_files({
        "a.py": updated_source,
    })

    assert (
        updated.find_enclosing(
            "a.py",
            7,
        ).symbol
        == "f"
    )

    assert (
        updated.digest()
        != base.digest()
    )

    assert (
        updated.metadata[
            "updated_files"
        ]
        == ["a.py"]
    )

    path = tmp_path / "index.json"

    updated.save(path)

    loaded = RepositoryIndex.load(path)

    assert (
        loaded.digest()
        == updated.digest()
    )