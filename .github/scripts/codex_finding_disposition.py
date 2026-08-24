#!/usr/bin/env python3
"""Publish a merge status from current Codex review-thread dispositions.

The script deliberately executes from the trusted default branch. It reads pull
request review threads through GraphQL and writes one commit status per open PR
head. Current unresolved Codex P0/P1 findings fail the status; resolved or
outdated findings and P2/P3 advisories do not.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, NamedTuple, Sequence


API_ROOT = "https://api.github.com"
GRAPHQL_URL = f"{API_ROOT}/graphql"
CODEX_LOGIN = "chatgpt-codex-connector"
STATUS_CONTEXT = "codex-finding-disposition"
PRIORITY_BADGE = re.compile(r"!\[P([0-3]) Badge\]")


class Finding(NamedTuple):
    priority: int
    url: str
    path: str
    line: int | None


class Evaluation(NamedTuple):
    findings: tuple[Finding, ...]
    blockers: tuple[Finding, ...]
    advisories: tuple[Finding, ...]
    status_state: str

    @property
    def blocking_count(self) -> int:
        return len(self.blockers)


def evaluate_threads(threads: Sequence[dict[str, Any]]) -> Evaluation:
    """Classify current structured findings from the Codex connector."""

    findings: list[Finding] = []
    for thread in threads:
        if thread.get("isResolved") or thread.get("isOutdated"):
            continue
        for comment in thread.get("comments", {}).get("nodes", ()):
            if (comment.get("author") or {}).get("login") != CODEX_LOGIN:
                continue
            match = PRIORITY_BADGE.search(str(comment.get("body") or ""))
            if not match:
                continue
            findings.append(
                Finding(
                    priority=int(match.group(1)),
                    url=str(comment.get("url") or ""),
                    path=str(thread.get("path") or ""),
                    line=thread.get("line"),
                )
            )

    ordered = tuple(sorted(findings, key=lambda item: (item.priority, item.url)))
    blockers = tuple(item for item in ordered if item.priority <= 1)
    advisories = tuple(item for item in ordered if item.priority > 1)
    return Evaluation(
        findings=ordered,
        blockers=blockers,
        advisories=advisories,
        status_state="failure" if blockers else "success",
    )


def status_payload(evaluation: Evaluation, pull_request_url: str) -> dict[str, str]:
    """Build the stable commit-status payload consumed by the main ruleset."""

    count = evaluation.blocking_count
    if count:
        noun = "finding" if count == 1 else "findings"
        description = f"{count} unresolved current Codex P0/P1 {noun} blocks merge"
    else:
        description = "No unresolved current Codex P0/P1 findings"
    return {
        "state": evaluation.status_state,
        "context": STATUS_CONTEXT,
        "description": description,
        "target_url": pull_request_url,
    }


class GitHubClient:
    def __init__(self, repository: str, token: str) -> None:
        owner, separator, name = repository.partition("/")
        if not separator or not owner or not name:
            raise ValueError("repository must be in OWNER/REPO form")
        if not token:
            raise ValueError("GITHUB_TOKEN or GH_TOKEN is required")
        self.repository = repository
        self.owner = owner
        self.name = name
        self.token = token

    def _request(self, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "27vette-codex-finding-disposition",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="GET" if data is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub API request failed: {exc.reason}") from exc

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = self._request(GRAPHQL_URL, {"query": query, "variables": variables})
        if response.get("errors"):
            raise RuntimeError(f"GitHub GraphQL errors: {json.dumps(response['errors'])}")
        return response["data"]

    def list_open_pull_request_numbers(self) -> list[int]:
        query = """
        query($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            pullRequests(states: OPEN, first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
              nodes { number }
              pageInfo { hasNextPage endCursor }
            }
          }
        }
        """
        numbers: list[int] = []
        cursor: str | None = None
        while True:
            data = self.graphql(
                query,
                {"owner": self.owner, "name": self.name, "cursor": cursor},
            )
            connection = data["repository"]["pullRequests"]
            numbers.extend(int(node["number"]) for node in connection["nodes"])
            if not connection["pageInfo"]["hasNextPage"]:
                return numbers
            cursor = connection["pageInfo"]["endCursor"]

    def pull_request(self, number: int) -> dict[str, Any]:
        query = """
        query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
              number
              url
              state
              headRefOid
              reviewThreads(first: 100, after: $cursor) {
                nodes {
                  isResolved
                  isOutdated
                  path
                  line
                  comments(first: 100) {
                    nodes {
                      author { login }
                      body
                      url
                    }
                  }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
          }
        }
        """
        cursor: str | None = None
        pull_request: dict[str, Any] | None = None
        threads: list[dict[str, Any]] = []
        while True:
            data = self.graphql(
                query,
                {
                    "owner": self.owner,
                    "name": self.name,
                    "number": number,
                    "cursor": cursor,
                },
            )
            current = data["repository"]["pullRequest"]
            if current is None:
                raise RuntimeError(f"pull request #{number} was not found")
            if pull_request is None:
                pull_request = {
                    "number": current["number"],
                    "url": current["url"],
                    "state": current["state"],
                    "headRefOid": current["headRefOid"],
                }
            connection = current["reviewThreads"]
            threads.extend(connection["nodes"])
            if not connection["pageInfo"]["hasNextPage"]:
                pull_request["reviewThreads"] = threads
                return pull_request
            cursor = connection["pageInfo"]["endCursor"]

    def set_status(self, sha: str, payload: dict[str, str]) -> None:
        self._request(
            f"{API_ROOT}/repos/{self.repository}/statuses/{sha}",
            payload,
        )


def evaluate_pull_request(
    client: GitHubClient,
    number: int,
    *,
    dry_run: bool,
) -> Evaluation:
    pull_request = client.pull_request(number)
    evaluation = evaluate_threads(pull_request["reviewThreads"])
    payload = status_payload(evaluation, pull_request["url"])

    print(
        f"PR #{number}: {payload['state']} — {payload['description']} "
        f"({len(evaluation.advisories)} P2/P3 advisory finding(s))"
    )
    for finding in evaluation.findings:
        location = finding.path
        if finding.line is not None:
            location = f"{location}:{finding.line}"
        print(f"  P{finding.priority} {location} {finding.url}")

    if not dry_run:
        client.set_status(pull_request["headRefOid"], payload)
    return evaluation


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub repository in OWNER/REPO form (default: GITHUB_REPOSITORY)",
    )
    parser.add_argument(
        "--pr-number",
        action="append",
        type=int,
        default=[],
        help="Evaluate one PR; repeat for multiple. Defaults to every open PR.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and report findings without writing commit statuses.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    try:
        client = GitHubClient(args.repository, token)
        numbers = args.pr_number or client.list_open_pull_request_numbers()
        for number in numbers:
            evaluate_pull_request(client, number, dry_run=args.dry_run)
    except (RuntimeError, ValueError) as exc:
        print(f"codex finding disposition failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
