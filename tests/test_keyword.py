"""Unit tests for BM25 lexical retrieval."""

from types import SimpleNamespace

from src.localization.keyword import BM25Retriever, tokenize


def make_index(documents):
    """Create a lightweight mock repository index."""

    records = []

    for path, text in documents.items():
        records.append(
            SimpleNamespace(
                path=path,
                retrieval_text=text,
            )
        )

    return SimpleNamespace(records=records)


def test_tokenize():
    assert tokenize("HttpResponse memoryview TEST_123") == [
        "httpresponse",
        "memoryview",
        "test_123",
    ]


def test_matching_document_ranks_first():
    index = make_index({
        "response.py": "HttpResponse memoryview bytes content",
        "models.py": "database queryset model fields",
        "template.py": "template rendering tags",
    })

    retriever = BM25Retriever(index)

    results = retriever.retrieve("HttpResponse memoryview")

    assert results[0][0] == "response.py"
    assert results[0][1] > 0


def test_nonmatching_documents_excluded():
    index = make_index({
        "response.py": "HttpResponse memoryview bytes",
        "models.py": "database queryset",
    })

    retriever = BM25Retriever(index)

    results = retriever.retrieve("memoryview")

    assert len(results) == 1
    assert results[0][0] == "response.py"


def test_top_k_limit():
    index = make_index({
        f"file_{i}.py": "memoryview bytes response"
        for i in range(20)
    })

    retriever = BM25Retriever(index)

    results = retriever.retrieve("memoryview", top_k=10)

    assert len(results) == 10
    assert all(score > 0 for _, score in results)


def test_deterministic_ranking():
    index = make_index({
        "b.py": "memoryview bytes",
        "a.py": "memoryview bytes",
    })

    retriever = BM25Retriever(index)

    results = retriever.retrieve("memoryview")

    assert results[0][0] == "a.py"
    assert results[1][0] == "b.py"


def test_empty_query():
    index = make_index({
        "response.py": "HttpResponse memoryview",
    })

    retriever = BM25Retriever(index)

    assert retriever.retrieve("") == []


def test_empty_index():
    index = make_index({})

    retriever = BM25Retriever(index)

    assert retriever.retrieve("memoryview") == []


def test_multiple_records_same_file():
    """Records from the same file should produce one ranked file."""

    index = SimpleNamespace(records=[
        SimpleNamespace(
            path="response.py",
            retrieval_text="HttpResponse",
        ),
        SimpleNamespace(
            path="response.py",
            retrieval_text="memoryview bytes",
        ),
        SimpleNamespace(
            path="models.py",
            retrieval_text="database queryset",
        ),
    ])

    retriever = BM25Retriever(index)

    results = retriever.retrieve("HttpResponse memoryview")

    assert len(results) == 1
    assert results[0][0] == "response.py"