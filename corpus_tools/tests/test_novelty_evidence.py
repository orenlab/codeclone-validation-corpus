"""Novelty expectations must be evaluated from evidence, never from a default.

A clone group that carries no usable ``novelty`` value is not a "known" group:
it is a group whose novelty the report cannot tell us. Counting it as "known"
turns absence of evidence into evidence and hides the exact failure that made
these tests necessary -- a broken baseline step read as a semantic change.

Run:

    uv run --with pytest pytest corpus_tools/tests
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from corpus_tools.runner import CommandResult
from corpus_tools.verify_expectation import verify_single_run

# The reason line a scenario must show when novelty cannot be evaluated.
MISSING_NOVELTY_REASON = (
    "novelty missing from report — cannot evaluate novelty expectations"
)

# Sentinel for "this group has no novelty key at all".
ABSENT = object()


def _function_clone_group(index: int, novelty: object) -> dict[str, Any]:
    group: dict[str, Any] = {
        "id": f"clone-function-{index}",
        "family": "clones",
        "category": "functions",
        "kind": "clone_group",
        "clone_kind": "functions",
        "confidence": "high",
        "count": 2,
        "items": [
            {"relative_path": f"pkg/mod_{index}.py", "qualname": f"alpha_{index}"},
            {"relative_path": f"pkg/mod_{index}.py", "qualname": f"beta_{index}"},
        ],
    }
    if novelty is not ABSENT:
        group["novelty"] = novelty
    return group


def _report(*novelty_values: object) -> dict[str, Any]:
    """Build a minimal report whose function clone groups carry given novelty."""
    return {
        "findings": {
            "groups": {
                "clones": {
                    "functions": [
                        _function_clone_group(index, novelty)
                        for index, novelty in enumerate(novelty_values)
                    ],
                    "blocks": [],
                    "segments": [],
                }
            }
        }
    }


def _result() -> CommandResult:
    return CommandResult(
        exit_code=0,
        stdout="",
        stderr="",
        report_path=Path("report.json"),
    )


def _verify(report: dict[str, Any], expect: dict[str, Any]):
    return verify_single_run(report=report, expect=expect, result=_result())


def _messages(outcome) -> list[str]:
    return [error.message for error in outcome.errors]


def test_absent_novelty_is_not_a_known_group() -> None:
    """A report with no novelty field must not satisfy a "known" expectation."""
    outcome = _verify(
        _report(ABSENT, ABSENT),
        {"clones": {"function_groups": {"new": 0, "known": 2}}},
    )

    assert not outcome.ok, (
        "two groups with no novelty field silently satisfied known=2; "
        "absence of evidence was accepted as evidence"
    )
    assert any(MISSING_NOVELTY_REASON in message for message in _messages(outcome)), (
        f"expected the explicit reason line, got {_messages(outcome)}"
    )


def test_unavailable_novelty_is_not_a_known_group() -> None:
    """`unavailable` is the engine saying it cannot tell -- never "known"."""
    outcome = _verify(
        _report("unavailable", "unavailable"),
        {"clones": {"function_groups": {"new": 0, "known": 2}}},
    )

    assert not outcome.ok, (
        "novelty=unavailable was tallied as known; the engine's honest "
        "opacity signal was converted into a positive claim"
    )
    assert any(MISSING_NOVELTY_REASON in message for message in _messages(outcome)), (
        f"expected the explicit reason line, got {_messages(outcome)}"
    )


def test_missing_novelty_does_not_cascade_into_a_count_mismatch() -> None:
    """The G01 incident: a broken baseline must not read as a count mismatch.

    With novelty absent the old tally reported ``new 1 -> 0`` and
    ``known 1 -> 2``, which reads as a semantic change in the fixture. The
    only true statement is that novelty could not be evaluated at all.
    """
    outcome = _verify(
        _report(ABSENT, ABSENT),
        {"clones": {"function_groups": {"new": 1, "known": 1}}},
    )

    assert not outcome.ok
    messages = _messages(outcome)
    assert len(messages) == 1, (
        f"expected one novelty-missing reason, got a cascade: {messages}"
    )
    assert MISSING_NOVELTY_REASON in messages[0], messages


def test_expectations_without_novelty_are_unaffected() -> None:
    """A scenario that never asserts novelty must not start failing."""
    outcome = _verify(
        _report(ABSENT, ABSENT),
        {
            "exit_code": 0,
            "findings": {"exact_total_active": 2, "exact_by_kind": {"function": 2}},
        },
    )

    assert outcome.ok, _messages(outcome)


def test_evidenced_novelty_is_still_evaluated() -> None:
    """Real novelty evidence keeps working, both matching and mismatching."""
    matching = _verify(
        _report("new", "known"),
        {"clones": {"function_groups": {"new": 1, "known": 1}}},
    )
    assert matching.ok, _messages(matching)

    mismatching = _verify(
        _report("new", "known"),
        {"clones": {"function_groups": {"new": 2}}},
    )
    assert not mismatching.ok
    messages = _messages(mismatching)
    assert len(messages) == 1, messages
    assert "function_groups.new expected 2, got 1" in messages[0], messages
    assert MISSING_NOVELTY_REASON not in messages[0], messages
