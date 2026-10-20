from src.agent.context import (
    augment_task_with_localization,
    format_localization_context,
)
from src.agent.contracts import (
    FailureEvent,
    LocalizationCandidate,
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

def test_index_record_is_the_shared_definition():
    from src.agent.contracts import IndexRecord as ContractRecord
    from src.repository.models import IndexRecord

    assert ContractRecord is IndexRecord
