from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


README_CANDIDATES = (
    "README.md",
    "readme.md",
    "Readme.md",
)


class ReadmeInputError(ValueError):
    """Raised when a README source cannot be loaded."""


def load_readme(source: str) -> tuple[str, str]:
    """Load README text from stdin, a local path, a raw URL, or a GitHub repo URL."""
    if source == "-":
        return sys.stdin.read(), "stdin"

    if _is_url(source):
        if _is_github_readme_blob_url(source):
            return _fetch_github_blob_readme(source)
        if _is_github_repo_url(source):
            return _fetch_github_readme(source)
        return _fetch_url(source), source

    path = Path(source)
    try:
        return path.read_text(encoding="utf-8"), str(path)
    except FileNotFoundError as exc:
        raise ReadmeInputError(f"README file not found: {source}") from exc
    except OSError as exc:
        raise ReadmeInputError(f"Could not read README file {source}: {exc}") from exc


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_github_repo_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.netloc.lower() != "github.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) == 2 and not parts[1].endswith(".git")


def _is_github_readme_blob_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.netloc.lower() != "github.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return (
        len(parts) >= 5
        and parts[2] == "blob"
        and parts[-1] in README_CANDIDATES
    )


def _fetch_github_blob_readme(blob_url: str) -> tuple[str, str]:
    parsed = urlparse(blob_url)
    owner, repo, _, ref, *path_parts = [part for part in parsed.path.split("/") if part]
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{'/'.join(path_parts)}"
    return _fetch_url(raw_url), raw_url


def _fetch_github_readme(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url)
    owner, repo = [part for part in parsed.path.split("/") if part][:2]
    repo = repo.removesuffix(".git")
    refs = ("HEAD", "main", "master", "trunk")
    urls = [
        f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{name}"
        for ref in refs
        for name in README_CANDIDATES
    ]

    last_error = None
    for url in urls:
        try:
            return _fetch_url(url), url
        except ReadmeInputError as exc:
            last_error = exc

    detail = f" Last error: {last_error}" if last_error else ""
    raise ReadmeInputError(f"Could not fetch a public Markdown README for {repo_url}.{detail}")


def _fetch_url(url: str) -> str:
    if not re.match(r"^https?://", url):
        raise ReadmeInputError(f"Unsupported URL: {url}")

    request = Request(url, headers={"User-Agent": "readme-first-screen/0.1"})
    try:
        with urlopen(request, timeout=10) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise ReadmeInputError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        raise ReadmeInputError(f"Could not fetch {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ReadmeInputError(f"Timed out fetching {url}") from exc
