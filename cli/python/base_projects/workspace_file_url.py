from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse

from base_projects.command_helpers import ProjectUsageError


INVALID_PERCENT_ESCAPE_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
LOCAL_FILE_URL_AUTHORITIES = frozenset(("", "localhost"))


def resolve_workspace_file_url(source: str) -> Path:
    try:
        parsed = urlparse(source)
    except ValueError as exc:
        raise ProjectUsageError("Malformed workspace file URL.") from exc

    if parsed.scheme.lower() != "file":
        raise ProjectUsageError("Workspace source is not a file:// URL.")
    if parsed.netloc.lower() not in LOCAL_FILE_URL_AUTHORITIES:
        raise ProjectUsageError(
            "Workspace file URLs support only an empty or localhost authority. "
            "Use file:///absolute/path or file://localhost/absolute/path."
        )
    if parsed.params or parsed.query or parsed.fragment:
        raise ProjectUsageError(
            "Workspace file URLs cannot include parameters, a query, or a fragment. "
            "Percent-encode those characters when they belong to the path."
        )
    if INVALID_PERCENT_ESCAPE_RE.search(parsed.path):
        raise ProjectUsageError(
            "Workspace file URL path contains malformed percent encoding. "
            "Encode a literal percent sign as %25."
        )

    try:
        decoded_path = unquote(parsed.path, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ProjectUsageError(
            "Workspace file URL path contains invalid UTF-8 percent encoding."
        ) from exc
    if not decoded_path.startswith("/") or decoded_path.startswith("//"):
        raise ProjectUsageError(
            "Workspace file URL path must be an absolute local path. Use file:///absolute/path."
        )
    if "\x00" in decoded_path:
        raise ProjectUsageError("Workspace file URL path cannot contain a NUL byte.")

    return Path(decoded_path).expanduser().resolve(strict=False)
