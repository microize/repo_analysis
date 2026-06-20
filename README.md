# Git Repository Analyser

Analyses any git repository and surfaces its **standout features** — explaining how each is implemented, with direct links to the exact files and line numbers in the source code.

Inspired by how you'd describe a project like *"Hermes agent is known for self-healing — here's the exact code that does it."*

---

## What It Does

1. **Clones** a GitHub repo (or reads a local path)
2. **Scans** all source files (up to 120 files, smart-prioritised)
3. **Analyses** the code using Claude AI
4. **Identifies** 3–6 standout/notable features
5. **Explains** each feature in depth: the mechanism, the pattern, and WHY it's clever
6. **Points** to specific files and line numbers, with GitHub permalink links

---

## Example Output

```
╭─────── Git Repository Analysis ───────╮
│  fastapi                               │
│  https://github.com/tiangolo/fastapi  │
│  commit a3f91c2                        │
╰────────────────────────────────────────╯

Project Summary
FastAPI is a modern, high-performance web framework for building APIs
with Python, based on standard Python type hints...

Tech Stack:  Python  Pydantic  Starlette  OpenAPI  AsyncIO

──────────── Feature 1 — Automatic OpenAPI Schema Generation ────────────
  Type-Hint-Driven API Docs With Zero Extra Code

How It Works
FastAPI inspects Python type annotations at startup using Pydantic models
and generates a full OpenAPI 3.0 schema automatically...

Pattern: Reflection + JSON Schema generation from Pydantic models

Related Files
  fastapi/openapi/utils.py
  fastapi/routing.py

Implementation Locations
  Code Pointer #1  fastapi/openapi/utils.py  lines 45–89
  https://github.com/tiangolo/fastapi/blob/a3f91c2.../fastapi/openapi/utils.py#L45-L89

  def get_openapi(...):
      ...
```

---

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Analyse a GitHub repo
python main.py https://github.com/tiangolo/fastapi

# Analyse and save Markdown report
python main.py https://github.com/anthropics/anthropic-sdk-python --output report.md

# Use a specific Claude model
python main.py https://github.com/pallets/flask --model claude-opus-4-8

# Analyse a local repo
python main.py /path/to/your/project
```

## Environment

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Architecture

```
main.py                    # CLI entry point
analyzer/
  __init__.py
  git_scanner.py           # Clone + scan repo filesystem
  feature_analyzer.py      # Claude API call + JSON parsing
  reporter.py              # Rich terminal renderer + Markdown exporter
requirements.txt
```

| Module | Responsibility |
|---|---|
| `git_scanner.py` | Walk the repo, collect source files with smart prioritisation |
| `feature_analyzer.py` | Build the prompt, call Claude, parse structured JSON output |
| `reporter.py` | Render Rich terminal UI and export Markdown with GitHub links |

---

## Supported Languages

Python, JavaScript, TypeScript, Go, Rust, Java, Kotlin, Ruby, PHP, C#, C/C++, Swift, Scala, Shell, YAML, SQL, Vue, Svelte, HTML, CSS, and more.
