"""Rewrite the 'Latest projects' table in README.md from the GitHub API.

Picks the most recently pushed public, non-fork repositories (excluding the
profile repo itself) and renders them between the START/END markers.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

USER = os.environ.get("GH_USER", "huydata2026")
TOKEN = os.environ.get("GITHUB_TOKEN")
LIMIT = int(os.environ.get("PROJECT_LIMIT", "5"))
README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!--START_SECTION:projects-->", "<!--END_SECTION:projects-->"

LANG_COLORS = {
    "Python": "3776AB", "SQL": "4479A1", "Jupyter Notebook": "F37626",
    "Shell": "89E051", "Dockerfile": "2496ED", "HCL": "7B42BC",
    "JavaScript": "F7DF1E", "TypeScript": "3178C6", "HTML": "E34F26",
}


def fetch_repos() -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    r = requests.get(
        f"https://api.github.com/users/{USER}/repos",
        params={"per_page": 100, "sort": "pushed", "type": "owner"},
        headers=headers, timeout=30,
    )
    r.raise_for_status()
    repos = [x for x in r.json() if not x["fork"] and not x["archived"]
             and x["name"].lower() != USER.lower()]
    return repos[:LIMIT]


def badge(lang: str | None) -> str:
    if not lang:
        return ""
    color = LANG_COLORS.get(lang, "6B7280")
    label = lang.replace(" ", "%20").replace("-", "--")
    return f'<img src="https://img.shields.io/badge/{label}-{color}?style=flat-square" alt="{lang}"/>'


def rel_time(iso: str) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - dt).days
    if days == 0:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def render(repos: list[dict]) -> str:
    rows = ["| Repository | Description | Stack | Updated |", "|---|---|---|---|"]
    for r in repos:
        desc = (r["description"] or "_No description yet_").strip()
        stars = f" ⭐ {r['stargazers_count']}" if r["stargazers_count"] else ""
        rows.append(
            f"| [**{r['name']}**]({r['html_url']}){stars} | {desc} | "
            f"{badge(r['language'])} | {rel_time(r['pushed_at'])} |"
        )
    return "\n".join(rows)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(rf"{re.escape(START)}.*?{re.escape(END)}", re.S)
    if not pattern.search(text):
        raise SystemExit("Markers not found in README.md")
    table = render(fetch_repos())
    new = pattern.sub(f"{START}\n{table}\n{END}", text)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README updated.")
    else:
        print("README unchanged.")


if __name__ == "__main__":
    main()
