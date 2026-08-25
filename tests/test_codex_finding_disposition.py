"""Contract tests for the Codex P0/P1 disposition status gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "codex_finding_disposition.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "codex-finding-disposition.yml"
CODEX_LOGIN = "chatgpt-codex-connector"


def _load_module():
    spec = importlib.util.spec_from_file_location("codex_finding_disposition", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _comment(priority: str, *, author: str = CODEX_LOGIN, url: str = "https://example.test/finding"):
    return {
        "author": {"login": author},
        "body": (
            f"**<sub><sub>![{priority} Badge]"
            f"(https://img.shields.io/badge/{priority}-orange?style=flat)</sub></sub>  Finding"
        ),
        "url": url,
    }


def _thread(
    priority: str,
    *,
    resolved: bool = False,
    outdated: bool = False,
    author: str = CODEX_LOGIN,
):
    return {
        "isResolved": resolved,
        "isOutdated": outdated,
        "path": "example.py",
        "line": 12,
        "comments": {"nodes": [_comment(priority, author=author)]},
    }


def test_unresolved_current_codex_p1_blocks():
    gate = _load_module()

    result = gate.evaluate_threads([_thread("P1")])

    assert result.blocking_count == 1
    assert result.blockers[0].priority == 1
    assert result.status_state == "failure"


def test_p0_blocks_as_more_severe_than_p1():
    gate = _load_module()

    result = gate.evaluate_threads([_thread("P0")])

    assert result.blocking_count == 1
    assert result.blockers[0].priority == 0


def test_resolved_and_outdated_p1_findings_do_not_block():
    gate = _load_module()

    result = gate.evaluate_threads(
        [
            _thread("P1", resolved=True),
            _thread("P1", outdated=True),
        ]
    )

    assert result.blocking_count == 0
    assert result.status_state == "success"


def test_current_p2_is_reported_but_does_not_block():
    gate = _load_module()

    result = gate.evaluate_threads([_thread("P2")])

    assert result.blocking_count == 0
    assert [finding.priority for finding in result.advisories] == [2]
    assert result.status_state == "success"


def test_non_codex_priority_badge_is_ignored():
    gate = _load_module()

    result = gate.evaluate_threads([_thread("P1", author="someone-else")])

    assert result.blocking_count == 0
    assert result.findings == ()


def test_plain_text_priority_without_badge_is_ignored():
    gate = _load_module()
    thread = _thread("P2")
    thread["comments"]["nodes"] = [
        {
            "author": {"login": CODEX_LOGIN},
            "body": "This prose mentions P1 but is not a structured Codex finding.",
            "url": "https://example.test/reply",
        }
    ]

    result = gate.evaluate_threads([thread])

    assert result.findings == ()


def test_status_payload_uses_stable_context_and_pr_target():
    gate = _load_module()
    result = gate.evaluate_threads([_thread("P1")])

    payload = gate.status_payload(result, "https://github.com/acme/repo/pull/7")

    assert payload == {
        "state": "failure",
        "context": "codex-finding-disposition",
        "description": "1 unresolved current Codex P0/P1 finding blocks merge",
        "target_url": "https://github.com/acme/repo/pull/7",
    }


def test_workflow_uses_trusted_base_code_and_reconciles_resolution():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request_target:" in workflow
    assert "pull_request_review:" in workflow
    assert "pull_request_review_comment:" in workflow
    assert "schedule:" in workflow
    assert "statuses: write" in workflow
    assert "pull-requests: write" in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "persist-credentials: false" in workflow
    assert "github.event.repository.default_branch" in workflow
    assert "github.event.pull_request.head" not in workflow
    assert ".github/scripts/codex_finding_disposition.py" in workflow
    # Cancelled runs read as failures on the PR; Codex fires several events at
    # once, so overlapping runs must queue rather than cancel each other.
    assert "cancel-in-progress: false" in workflow


def _stale_badge_comment(priority: str, *, url: str = "https://example.test/stale"):
    """A Codex finding whose badge markup drifted away from the strict pattern."""

    return {
        "author": {"login": CODEX_LOGIN},
        "body": (
            f"**<sub><sub><img src='https://img.shields.io/badge/{priority}-orange'>"
            "</sub></sub>  Finding"
        ),
        "url": url,
    }


def _stale_thread(priority: str, **kwargs):
    thread = _thread(priority, **kwargs)
    thread["comments"]["nodes"] = [_stale_badge_comment(priority)]
    return thread


def test_drifted_badge_markup_errors_instead_of_passing_silently():
    gate = _load_module()

    result = gate.evaluate_threads([_stale_thread("P1")])

    assert result.parser_is_stale
    assert result.status_state == "error"
    assert [finding.priority for finding in result.stale_parser] == [1]
    # The finding is still counted, so a drifted badge never loses a blocker.
    assert result.blocking_count == 1


def test_drifted_badge_errors_even_for_non_blocking_priorities():
    gate = _load_module()

    result = gate.evaluate_threads([_stale_thread("P3")])

    assert result.blocking_count == 0
    assert result.status_state == "error"


def test_resolved_thread_with_drifted_badge_does_not_error():
    gate = _load_module()

    result = gate.evaluate_threads([_stale_thread("P1", resolved=True)])

    assert result.status_state == "success"
    assert result.stale_parser == ()


def test_codex_prose_without_any_badge_is_not_a_parser_failure():
    gate = _load_module()
    thread = _thread("P1")
    thread["comments"]["nodes"] = [
        {
            "author": {"login": CODEX_LOGIN},
            "body": "Thanks, this reply mentions P1 but carries no badge at all.",
            "url": "https://example.test/reply",
        }
    ]

    result = gate.evaluate_threads([thread])

    assert result.status_state == "success"
    assert result.stale_parser == ()


def test_status_payload_reports_a_stale_parser():
    gate = _load_module()
    result = gate.evaluate_threads([_stale_thread("P1")])

    payload = gate.status_payload(result, "https://github.com/acme/repo/pull/7")

    assert payload["state"] == "error"
    assert payload["description"] == (
        "Codex badge markup changed; disposition parser needs an update"
    )


def test_sticky_comment_lists_blockers_and_carries_the_marker():
    gate = _load_module()
    result = gate.evaluate_threads([_thread("P1"), _thread("P2")])

    body = gate.comment_body(result)

    assert body.startswith(gate.COMMENT_MARKER)
    assert "1 unresolved P0/P1 finding blocking merge" in body
    assert "[`example.py:12`](https://example.test/finding)" in body
    # P2 advisories are mirrored but folded away so they cannot be mistaken for blockers.
    assert "1 P2/P3 advisory (non-blocking)" in body


def test_sticky_comment_warns_when_the_parser_is_stale():
    gate = _load_module()
    result = gate.evaluate_threads([_stale_thread("P1")])

    body = gate.comment_body(result)

    assert "[!CAUTION]" in body
    assert "PRIORITY_BADGE" in body
