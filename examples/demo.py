"""
Quick demo — analyse a well-known open-source repo.

Run:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/demo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analyzer import clone_repo, scan_local_repo, analyze, render_report, export_markdown

DEMO_REPO = "https://github.com/pallets/flask"

if __name__ == "__main__":
    print(f"Cloning {DEMO_REPO} ...")
    local_path = clone_repo(DEMO_REPO)

    print("Scanning source files...")
    scan = scan_local_repo(local_path)
    print(f"  Found {len(scan.files)} files")

    print("Analysing with Claude...")
    report = analyze(scan)

    render_report(report)
    export_markdown(report, "flask_analysis.md")
    print("\nDone! Report saved to flask_analysis.md")
