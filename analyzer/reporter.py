"""
Renders an AnalysisReport to the terminal (Rich) and optionally to a Markdown file.
"""

from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from .feature_analyzer import AnalysisReport, StandoutFeature, CodePointer

console = Console()


def _language_from_path(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    mapping = {"py": "python", "ts": "typescript", "js": "javascript",
                "go": "go", "rs": "rust", "java": "java", "rb": "ruby",
                "sh": "bash", "yml": "yaml", "yaml": "yaml"}
    return mapping.get(ext, "text")


def _render_code_pointer(cp: CodePointer, index: int) -> None:
    lang = _language_from_path(cp.file)
    loc = ""
    if cp.line_start:
        loc = f"  lines {cp.line_start}"
        if cp.line_end and cp.line_end != cp.line_start:
            loc += f"–{cp.line_end}"

    label = f"[bold cyan]{cp.file}[/bold cyan]{loc}"
    if cp.github_url:
        label += f"\n[dim]{cp.github_url}[/dim]"

    console.print(f"  [yellow]Code Pointer #{index + 1}[/yellow]  {label}")
    if cp.snippet.strip():
        syntax = Syntax(
            cp.snippet.strip(),
            lang,
            theme="monokai",
            line_numbers=bool(cp.line_start),
            start_line=cp.line_start or 1,
            padding=(0, 2),
        )
        console.print(syntax)
    console.print()


def _render_feature(feat: StandoutFeature, idx: int) -> None:
    console.print(Rule(
        f"[bold green] Feature {idx + 1} — {feat.name} [/bold green]",
        style="green",
    ))
    console.print(f"[bold white on dark_green]  {feat.tagline}  [/bold white on dark_green]")
    console.print()

    # How it works
    console.print("[bold underline]How It Works[/bold underline]")
    console.print(Markdown(feat.how_it_works))
    console.print()

    # Implementation pattern badge
    if feat.implementation_pattern:
        console.print(
            f"[bold]Pattern:[/bold] [italic magenta]{feat.implementation_pattern}[/italic magenta]"
        )
        console.print()

    # Related files table
    if feat.related_files:
        tbl = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        tbl.add_column("File", style="cyan")
        for f in feat.related_files:
            tbl.add_row(f)
        console.print("[bold]Related Files[/bold]")
        console.print(tbl)

    # Code pointers
    if feat.code_pointers:
        console.print("[bold]Implementation Locations[/bold]")
        for i, cp in enumerate(feat.code_pointers):
            _render_code_pointer(cp, i)


def render_report(report: AnalysisReport) -> None:
    """Pretty-print the full analysis report to the terminal."""
    console.print()
    console.print(Panel(
        f"[bold white]{report.repo_name}[/bold white]\n"
        f"[dim]{report.remote_url}[/dim]\n"
        f"[dim]commit {report.commit_hash[:8] if report.commit_hash else 'unknown'}[/dim]",
        title="[bold blue]  Git Repository Analysis  [/bold blue]",
        border_style="blue",
        expand=False,
    ))
    console.print()

    # Summary
    console.print("[bold]Project Summary[/bold]")
    console.print(Markdown(report.summary))
    console.print()

    # Tech stack
    if report.tech_stack:
        console.print(
            "[bold]Tech Stack:[/bold]  "
            + "  ".join(f"[cyan]{t}[/cyan]" for t in report.tech_stack)
        )
        console.print()

    console.print(Rule("[bold blue]Standout Features[/bold blue]", style="blue"))
    console.print()

    for i, feat in enumerate(report.features):
        _render_feature(feat, i)
        console.print()


def export_markdown(report: AnalysisReport, output_path: str) -> None:
    """Write the report to a Markdown file."""
    lines = [
        f"# {report.repo_name} — Feature Analysis",
        "",
        f"> **Repo:** {report.remote_url}  ",
        f"> **Commit:** `{report.commit_hash[:8] if report.commit_hash else 'unknown'}`",
        "",
        "## Project Summary",
        "",
        report.summary,
        "",
        "## Tech Stack",
        "",
        ", ".join(f"`{t}`" for t in report.tech_stack),
        "",
        "---",
        "",
        "## Standout Features",
        "",
    ]

    for i, feat in enumerate(report.features, 1):
        lines += [
            f"### {i}. {feat.name}",
            "",
            f"**{feat.tagline}**",
            "",
            "#### How It Works",
            "",
            feat.how_it_works,
            "",
        ]
        if feat.implementation_pattern:
            lines += [f"**Pattern:** *{feat.implementation_pattern}*", ""]

        if feat.related_files:
            lines += ["**Related Files:**", ""]
            for f in feat.related_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if feat.code_pointers:
            lines += ["#### Implementation Locations", ""]
            for cp in feat.code_pointers:
                loc = ""
                if cp.line_start:
                    loc = f" (lines {cp.line_start}"
                    if cp.line_end and cp.line_end != cp.line_start:
                        loc += f"–{cp.line_end}"
                    loc += ")"
                lines.append(f"**`{cp.file}`{loc}**")
                if cp.github_url:
                    lines.append(f"[View on GitHub]({cp.github_url})")
                lines.append("")
                if cp.snippet.strip():
                    lang = _language_from_path(cp.file)
                    lines += [f"```{lang}", cp.snippet.strip(), "```", ""]

        lines += ["---", ""]

    Path(output_path).write_text("\n".join(lines))
    console.print(f"\n[green]Report saved to:[/green] {output_path}")
