#!/usr/bin/env python3
"""
Git Repository Analyser
=======================
Clones (or reads) a git repository, scans the source code, and uses
Claude to identify standout features — explaining exactly how each is
implemented with links to specific files and line numbers.

Usage:
    python main.py <repo-url-or-local-path> [--output report.md] [--model claude-sonnet-4-6]

Examples:
    python main.py https://github.com/anthropics/anthropic-sdk-python
    python main.py /path/to/local/repo --output my_report.md
    python main.py https://github.com/tiangolo/fastapi --model claude-opus-4-8
"""

import os
import sys
import tempfile
import argparse
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from analyzer import scan_local_repo, clone_repo, analyze, render_report, export_markdown

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyse a git repository and surface its standout features.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "repo",
        help="GitHub URL (https://github.com/...) or local path to a git repo",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Save the report as a Markdown file (e.g. report.md)",
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-sonnet-4-6",
        help="Claude model to use (default: claude-sonnet-4-6)",
    )
    return parser.parse_args()


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.startswith("git@")


def main():
    args = parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY environment variable is not set.")
        console.print("Set it with:  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    repo_arg = args.repo
    tmp_dir = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:

        # Step 1 — Clone or point to local repo
        if is_url(repo_arg):
            task = progress.add_task("Cloning repository...", total=None)
            tmp_dir = tempfile.mkdtemp(prefix="repo_analysis_")
            try:
                local_path = clone_repo(repo_arg, tmp_dir)
            except Exception as e:
                console.print(f"[bold red]Clone failed:[/bold red] {e}")
                sys.exit(1)
            progress.remove_task(task)
        else:
            local_path = str(Path(repo_arg).resolve())
            if not Path(local_path).is_dir():
                console.print(f"[bold red]Error:[/bold red] Path not found: {local_path}")
                sys.exit(1)

        # Step 2 — Scan filesystem
        task = progress.add_task("Scanning source files...", total=None)
        scan = scan_local_repo(local_path)
        progress.remove_task(task)

        console.print(
            f"[dim]Scanned {len(scan.files)} files  |  "
            f"remote: {scan.remote_url or 'local'}  |  "
            f"branch: {scan.default_branch}[/dim]"
        )

        # Step 3 — AI analysis
        task = progress.add_task(
            f"Analysing with [bold]{args.model}[/bold]...", total=None
        )
        try:
            report = analyze(scan, model=args.model)
        except Exception as e:
            console.print(f"[bold red]Analysis failed:[/bold red] {e}")
            sys.exit(1)
        progress.remove_task(task)

    # Step 4 — Render report
    render_report(report)

    # Step 5 — Export if requested
    if args.output:
        export_markdown(report, args.output)

    # Cleanup temp clone
    if tmp_dir:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
