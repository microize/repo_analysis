"""
Uses Claude to identify standout features in a codebase and pinpoint
the exact files + line ranges where each feature is implemented.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from .git_scanner import RepoScan


@dataclass
class CodePointer:
    file: str
    line_start: Optional[int]
    line_end: Optional[int]
    snippet: str
    github_url: str = ""


@dataclass
class StandoutFeature:
    name: str
    tagline: str                    # one-line hook (e.g. "Self-Healing Execution")
    how_it_works: str               # 2-4 paragraph explanation
    implementation_pattern: str     # e.g. "retry loop + exponential backoff"
    code_pointers: list[CodePointer] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    repo_name: str
    remote_url: str
    commit_hash: str
    summary: str
    tech_stack: list[str]
    features: list[StandoutFeature]


SYSTEM_PROMPT = """\
You are an expert software architect and code analyst. Your job is to read a \
git repository's source files, identify the most technically interesting \
standout features, and explain precisely how each feature is implemented — \
pointing to specific files and approximate line numbers.

You MUST return a single JSON object with this exact schema:

{
  "repo_name": "<short name>",
  "summary": "<2-3 sentence project overview>",
  "tech_stack": ["<tech1>", "<tech2>", ...],
  "features": [
    {
      "name": "<Feature Name>",
      "tagline": "<One punchy line, e.g. 'Self-Healing Retry Engine'>",
      "how_it_works": "<3-5 paragraphs explaining the mechanism in depth>",
      "implementation_pattern": "<Pattern name, e.g. 'Exponential back-off with jitter'>",
      "code_pointers": [
        {
          "file": "<relative file path>",
          "line_start": <integer or null>,
          "line_end": <integer or null>,
          "snippet": "<the key 2-8 lines of code that show the feature>"
        }
      ],
      "related_files": ["<file1>", "<file2>"]
    }
  ]
}

Rules:
- Return ONLY the JSON object. No markdown, no code fences, no commentary.
- Identify 3 to 6 features. Prefer genuinely novel or technically deep ones.
- For each feature provide at least 2 code_pointers pointing to the actual \
  implementation lines. If you cannot find exact lines, set line_start/line_end \
  to null but still provide a representative snippet from the file.
- how_it_works must be detailed and educational — explain WHY the pattern is \
  clever, not just WHAT it does.
- Be specific about filenames — use the exact relative paths provided.
"""


def _build_user_message(scan: RepoScan) -> str:
    parts = [
        f"# Repository: {scan.remote_url or scan.root}",
        f"Branch: {scan.default_branch}  Commit: {scan.commit_hash[:8] if scan.commit_hash else 'unknown'}",
        "",
        "## File Tree",
        "```",
        scan.file_tree[:3000] if scan.file_tree else "(empty)",
        "```",
        "",
    ]

    if scan.readme:
        parts += [
            "## README",
            scan.readme[:3000],
            "",
        ]

    parts.append("## Source Files")
    for rec in scan.files:
        parts += [
            f"\n### FILE: {rec.path}",
            f"```{rec.language}",
            rec.content,
            "```",
        ]

    return "\n".join(parts)


def _make_github_url(remote_url: str, commit: str, file_path: str,
                     line_start: Optional[int], line_end: Optional[int]) -> str:
    """Convert a remote git URL + file path into a GitHub permalink."""
    if not remote_url:
        return ""
    # Normalise SSH → HTTPS
    url = remote_url
    url = re.sub(r"^git@github\.com:", "https://github.com/", url)
    url = re.sub(r"\.git$", "", url)
    if "github.com" not in url:
        return ""
    ref = commit[:40] if commit else "HEAD"
    link = f"{url}/blob/{ref}/{file_path}"
    if line_start:
        link += f"#L{line_start}"
        if line_end and line_end != line_start:
            link += f"-L{line_end}"
    return link


def analyze(scan: RepoScan, model: str = "claude-sonnet-4-6") -> AnalysisReport:
    """Send the scanned repo to Claude and parse the structured feature report."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)

    user_msg = _build_user_message(scan)

    response = client.messages.create(
        model=model,
        max_tokens=8096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()

    # Strip accidental markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)

    features: list[StandoutFeature] = []
    for f in data.get("features", []):
        pointers: list[CodePointer] = []
        for cp in f.get("code_pointers", []):
            gh_url = _make_github_url(
                scan.remote_url,
                scan.commit_hash,
                cp.get("file", ""),
                cp.get("line_start"),
                cp.get("line_end"),
            )
            pointers.append(CodePointer(
                file=cp.get("file", ""),
                line_start=cp.get("line_start"),
                line_end=cp.get("line_end"),
                snippet=cp.get("snippet", ""),
                github_url=gh_url,
            ))

        features.append(StandoutFeature(
            name=f.get("name", ""),
            tagline=f.get("tagline", ""),
            how_it_works=f.get("how_it_works", ""),
            implementation_pattern=f.get("implementation_pattern", ""),
            code_pointers=pointers,
            related_files=f.get("related_files", []),
        ))

    return AnalysisReport(
        repo_name=data.get("repo_name", "Unknown"),
        remote_url=scan.remote_url,
        commit_hash=scan.commit_hash,
        summary=data.get("summary", ""),
        tech_stack=data.get("tech_stack", []),
        features=features,
    )
