"""Fetch live GitHub repository and contribution totals and update hero SVGs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def fetch_github_stats(username: str, token: str) -> tuple[int, int]:
    """Query GitHub GraphQL API for repository and contribution counts."""
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(privacy: PUBLIC) {
          totalCount
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{username}-profile-updater",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")

    user = data["data"]["user"]
    repo_count = int(user["repositories"]["totalCount"])
    total_contribs = int(user["contributionsCollection"]["contributionCalendar"]["totalContributions"])
    return repo_count, total_contribs


def update_hero_counts(repo_count: int, total_contribs: int) -> None:
    """Update REPOSITORIES and CONTRIBUTIONS numbers in hero-dark.svg and hero-light.svg."""
    for name in ("hero-dark.svg", "hero-light.svg"):
        path = ASSETS / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r'(<text id="stat-repos"[^>]*>)[^<]*(</text>)',
            rf"\g<1>{repo_count}\g<2>",
            text,
        )
        text = re.sub(
            r'(<text id="stat-contribs"[^>]*>)[^<]*(</text>)',
            rf"\g<1>{total_contribs}\g<2>",
            text,
        )
        path.write_text(text, encoding="utf-8")


def main() -> int:
    username = os.environ.get("GITHUB_USERNAME", "a-ldnstntng")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN is required to fetch GitHub GraphQL stats.", file=sys.stderr)
        return 1

    repo_count, total_contribs = fetch_github_stats(username, token)
    update_hero_counts(repo_count, total_contribs)
    print(f"Updated hero SVGs for {username}: {repo_count} repos, {total_contribs} contributions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
