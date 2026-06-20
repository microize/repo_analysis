"""
Scans a git repository and collects structured metadata about its codebase.
"""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# File extensions we consider source code (skip binaries, assets, etc.)
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".swift", ".scala",
    ".sh", ".bash", ".zsh", ".yaml", ".yml", ".toml", ".json", ".md",
    ".vue", ".svelte", ".html", ".css", ".scss", ".sql",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", ".next", ".nuxt", "coverage", ".nyc_output", "vendor",
    "target", ".gradle", ".idea", ".vscode", "*.egg-info",
}

MAX_FILE_SIZE_BYTES = 100_000   # 100 KB per file
MAX_FILES_TO_READ = 120
MAX_CHARS_PER_FILE = 8_000


@dataclass
class FileRecord:
    path: str               # relative path inside the repo
    content: str
    language: str


@dataclass
class RepoScan:
    root: str               # absolute local path
    remote_url: str
    default_branch: str
    commit_hash: str
    files: list[FileRecord] = field(default_factory=list)
    readme: str = ""
    file_tree: str = ""


def _detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".jsx": "javascript", ".go": "go",
        ".rs": "rust", ".java": "java", ".kt": "kotlin", ".rb": "ruby",
        ".php": "php", ".cs": "csharp", ".cpp": "cpp", ".c": "c",
        ".h": "c", ".swift": "swift", ".scala": "scala",
        ".sh": "bash", ".bash": "bash", ".zsh": "bash",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".json": "json", ".md": "markdown", ".vue": "vue",
        ".svelte": "svelte", ".html": "html", ".css": "css",
        ".scss": "scss", ".sql": "sql",
    }
    return mapping.get(ext, "text")


def _get_git_info(repo_path: str) -> tuple[str, str, str]:
    """Returns (remote_url, default_branch, commit_hash)."""
    def run(cmd):
        try:
            return subprocess.check_output(
                cmd, cwd=repo_path, stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            return ""

    remote_url = run(["git", "remote", "get-url", "origin"])
    default_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit_hash = run(["git", "rev-parse", "HEAD"])
    return remote_url, default_branch, commit_hash


def _build_file_tree(root: Path, max_depth: int = 4) -> str:
    lines = []

    def walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                walk(entry, prefix + extension, depth + 1)

    walk(root, "", 0)
    return "\n".join(lines)


def _collect_files(root: Path) -> list[tuple[Path, str]]:
    """Walk repo and return (abs_path, rel_path) for source files."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            if fpath.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
            rel = str(fpath.relative_to(root))
            results.append((fpath, rel))
    return results


def scan_local_repo(repo_path: str) -> RepoScan:
    """Scan a locally cloned git repository and return a RepoScan."""
    root = Path(repo_path).resolve()
    remote_url, default_branch, commit_hash = _get_git_info(str(root))

    file_tree = _build_file_tree(root)

    # Collect and read source files
    all_files = _collect_files(root)

    # Prioritise important files: README, main entry points, config roots
    def priority(rel: str) -> int:
        lower = rel.lower()
        if "readme" in lower:
            return 0
        if lower in ("main.py", "index.ts", "index.js", "app.py", "server.py",
                     "main.go", "main.rs", "main.java", "app.ts"):
            return 1
        if lower.count("/") == 0:
            return 2   # root-level files
        return 3

    all_files.sort(key=lambda t: (priority(t[1]), t[1]))

    file_records: list[FileRecord] = []
    readme_content = ""

    for fpath, rel in all_files[:MAX_FILES_TO_READ]:
        try:
            content = fpath.read_text(errors="replace")
        except Exception:
            continue
        if len(content) > MAX_CHARS_PER_FILE:
            content = content[:MAX_CHARS_PER_FILE] + "\n... [truncated]"

        lang = _detect_language(rel)
        record = FileRecord(path=rel, content=content, language=lang)
        file_records.append(record)

        if "readme" in rel.lower() and not readme_content:
            readme_content = content

    return RepoScan(
        root=str(root),
        remote_url=remote_url,
        default_branch=default_branch,
        commit_hash=commit_hash,
        files=file_records,
        readme=readme_content,
        file_tree=file_tree,
    )


def clone_repo(url: str, dest: Optional[str] = None) -> str:
    """Clone a remote repo and return the local path."""
    import tempfile
    if dest is None:
        dest = tempfile.mkdtemp(prefix="repo_analysis_")
    subprocess.check_call(
        ["git", "clone", "--depth=1", url, dest],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return dest
