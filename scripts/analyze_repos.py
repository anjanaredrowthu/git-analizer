#!/usr/bin/env python3
"""Analyze GitHub repositories for an organization and save matching results as JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

API_BASE = "https://api.github.com"
DEFAULT_OUTPUT = "reports/repositories.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch repositories from a GitHub organization, filter them based on "
            "Actions usage, contributor count, and recent updates, and save the results to JSON."
        )
    )
    parser.add_argument(
        "--org",
        default=os.getenv("GITHUB_ORG", ""),
        help="GitHub organization or user name to inspect.",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT),
        help="Path to write the JSON report.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN", ""),
        help="GitHub token for API requests (optional for public repositories).",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=int(os.getenv("RECENT_MONTHS", "3")),
        help="Number of recent months to consider for updates.",
    )
    return parser.parse_args()


def build_headers(token: str) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "git-analizer",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_paginated_json(url: str, headers: dict[str, str], params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    page = 1

    while True:
        current_params = dict(params or {})
        current_params.update({"page": page, "per_page": 100})
        response = requests.get(url, headers=headers, params=current_params, timeout=30)
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            raise ValueError(f"Expected a list response from {url}, got {type(batch).__name__}")
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return results


def fetch_repositories(org: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    endpoints = [
        f"{API_BASE}/orgs/{org}/repos",
        f"{API_BASE}/users/{org}/repos",
    ]

    for endpoint in endpoints:
        try:
            return fetch_paginated_json(endpoint, headers, params={"type": "all"})
        except requests.RequestException:
            continue

    raise RuntimeError(
        f"Unable to fetch repositories for '{org}'. Verify that the organization/user exists and that API access is allowed."
    )


def repo_has_actions(owner: str, repo_name: str, headers: dict[str, str]) -> bool:
    url = f"{API_BASE}/repos/{owner}/{repo_name}/actions/workflows"
    try:
        response = requests.get(url, headers=headers, params={"per_page": 1}, timeout=30)
        if response.status_code in (403, 404):
            return False
        response.raise_for_status()
        payload = response.json()
        return bool(payload.get("total_count", 0))
    except requests.RequestException:
        return False


def count_contributors(owner: str, repo_name: str, headers: dict[str, str]) -> int:
    url = f"{API_BASE}/repos/{owner}/{repo_name}/contributors"
    count = 0
    page = 1

    while True:
        response = requests.get(
            url,
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=30,
        )
        if response.status_code == 404:
            return 0
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            break
        count += len(batch)
        if len(batch) < 100:
            break
        page += 1

    return count


def is_recently_updated(updated_at: str, months: int) -> bool:
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    return updated >= cutoff


def build_report(org: str, repos: list[dict[str, Any]], months: int, headers: dict[str, str]) -> dict[str, Any]:
    matching_repositories = []

    for repo in repos:
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        repo_full_name = repo.get("full_name", f"{owner}/{repo_name}")

        has_actions = repo_has_actions(owner, repo_name, headers)
        contributors = count_contributors(owner, repo_name, headers)
        recently_updated = is_recently_updated(repo.get("updated_at", ""), months)

        if not (has_actions and contributors > 5 and recently_updated):
            continue

        matching_repositories.append(
            {
                "name": repo_name,
                "full_name": repo_full_name,
                "html_url": repo.get("html_url"),
                "default_branch": repo.get("default_branch"),
                "language": repo.get("language"),
                "updated_at": repo.get("updated_at"),
                "created_at": repo.get("created_at"),
                "stargazers_count": repo.get("stargazers_count", 0),
                "open_issues_count": repo.get("open_issues_count", 0),
                "contributors_count": contributors,
                "has_actions": has_actions,
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": generated_at,
        "organization": org,
        "criteria": {
            "has_actions": True,
            "contributors_count_greater_than": 5,
            "updated_within_last_months": months,
        },
        "summary": {
            "total_repositories_scanned": len(repos),
            "matching_repositories": len(matching_repositories),
        },
        "repositories": matching_repositories,
    }


def main() -> int:
    args = parse_args()
    org = args.org.strip()
    if not org:
        print("Error: provide --org or set GITHUB_ORG.", file=sys.stderr)
        return 1

    headers = build_headers(args.token)

    try:
        repositories = fetch_repositories(org, headers)
        report = build_report(org, repositories, args.months, headers)
    except requests.RequestException as exc:
        print(f"GitHub API request failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - surfaced to the user
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write("\n")

    print(f"Organization: {org}")
    print(f"Total repositories scanned: {report['summary']['total_repositories_scanned']}")
    print(f"Matching repositories: {report['summary']['matching_repositories']}")
    print(f"Report written to: {output_path}")

    for repo in report["repositories"]:
        print(
            f"- {repo['full_name']} | contributors={repo['contributors_count']} | updated={repo['updated_at']}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
