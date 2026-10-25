from src.agent.context import (
    augment_task_with_localization,
    format_localization_context,
)
from src.agent.contracts import (
    FailureEvent,
    LocalizationCandidate,
)

from src.agent.context import (
    augment_task_with_localization,
    format_localization_context,
    select_prompt_candidates,
)


def test_localization_context_format():
    candidates = [
        LocalizationCandidate(
            file="src/parser.py",
            symbol="parse_header",
            symbol_type="function",
            rank=1,
            score=0.87,
            reason="BM25 + structure",
        )
    ]

    text = format_localization_context(
        candidates
    )

    assert "src/parser.py" in text
    assert "parse_header" in text
    assert "0.8700" in text


def test_condition_context_can_be_added():
    task = "Fix the parser bug."

    candidates = [
        LocalizationCandidate(
            file="src/parser.py",
            symbol=None,
            symbol_type=None,
            rank=1,
            score=0.8,
            reason="lexical",
        )
    ]

    result = (
        augment_task_with_localization(
            task,
            candidates,
        )
    )

    assert task in result
    assert "src/parser.py" in result
    assert (
        "Repository localization guidance"
        in result
    )


def test_failure_event_schema():
    event = FailureEvent(
        exception_type="TypeError",
        traceback_files=[
            "src/parser.py"
        ],
        traceback_symbols=[
            "parse_header"
        ],
        failing_tests=[
            "test_parser"
        ],
        source="pytest",
        locatable=True,
    )

    assert event.locatable is True
    assert (
        event.traceback_files[0]
        == "src/parser.py"
    )

def test_prompt_candidates_respect_top_k():
    candidates = [
        LocalizationCandidate(
            file="src/c.py",
            rank=3,
            score=0.3,
        ),
        LocalizationCandidate(
            file="src/a.py",
            rank=1,
            score=0.9,
        ),
        LocalizationCandidate(
            file="src/b.py",
            rank=2,
            score=0.6,
        ),
    ]

    from src.agent.context import (
        select_prompt_candidates,
    )

    result = select_prompt_candidates(
        candidates,
        top_k=2,
    )

    assert [
        candidate.file
        for candidate in result
    ] == [
        "src/a.py",
        "src/b.py",
    ]


def test_prompt_candidates_none_keeps_all():
    candidates = [
        LocalizationCandidate(
            file="src/a.py",
            rank=1,
            score=0.9,
        ),
        LocalizationCandidate(
            file="src/b.py",
            rank=2,
            score=0.6,
        ),
    ]

    from src.agent.context import (
        select_prompt_candidates,
    )

    result = select_prompt_candidates(
        candidates,
        top_k=None,
    )

    assert len(result) == 2


def test_prompt_candidates_reject_invalid_top_k():
    from src.agent.context import (
        select_prompt_candidates,
    )

    try:
        select_prompt_candidates(
            [],
            top_k=0,
        )

    except ValueError as exc:
        assert (
            "positive integer"
            in str(exc)
        )

    else:
        raise AssertionError(
            "top_k=0 should be rejected."
        )

def test_index_record_is_shared_definition():
    from src.agent.contracts import (
        IndexRecord as AgentIndexRecord,
    )
    from src.repository.models import (
        IndexRecord as RepositoryIndexRecord,
    )

    assert (
        AgentIndexRecord
        is RepositoryIndexRecord
    )