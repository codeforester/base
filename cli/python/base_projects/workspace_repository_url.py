from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import SplitResult
from urllib.parse import unquote_plus
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from base_cli.redaction import REDACTED
from base_cli.redaction import is_secret_key
from base_cli.redaction import redact_text_value


SCP_REPOSITORY_URL_RE = re.compile(r"^(?P<userinfo>[^@\s]+)@(?P<location>[^:\s]+:.+)$")
URL_PARAMETER_SEPARATOR_RE = re.compile(r"([&;])")
NETWORK_REPOSITORY_URL_SCHEMES = frozenset(("git", "https", "ssh"))


def redact_repository_url(value: str) -> str:
    if Path(value).is_absolute():
        return value

    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value):
        return REDACTED

    scp_match = None if "://" in value else SCP_REPOSITORY_URL_RE.match(value)
    if scp_match is not None:
        userinfo = scp_match.group("userinfo")
        sanitized_userinfo = userinfo if userinfo == "git" else REDACTED
        sanitized = f"{sanitized_userinfo}@{scp_match.group('location')}"
        return redact_url_suffix_parameters(sanitized)

    parsed = parse_repository_url(value)
    if parsed is None:
        return REDACTED

    netloc = parsed.netloc
    userinfo, separator, host = netloc.rpartition("@")
    if separator and userinfo != "git":
        netloc = f"{REDACTED}@{host}"
    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            redact_url_parameters(parsed.query),
            redact_url_parameters(parsed.fragment),
        )
    )


def redact_workspace_source(value: str) -> str:
    """Redact credentials and secret URL parameters from a workspace source."""
    sanitized = redact_text_value(value)
    if Path(value).is_absolute():
        return redact_url_suffix_parameters(sanitized)

    sanitized = redact_repository_url(value)
    if sanitized != REDACTED:
        return sanitized
    if "://" not in value:
        return redact_url_suffix_parameters(redact_text_value(value))
    return redact_url_suffix_parameters(redact_text_value(value))


def repository_url_problem(value: str) -> str | None:
    if Path(value).is_absolute():
        return None
    if value.startswith("http://"):
        return "insecure_http"

    sanitized = redact_repository_url(value)
    if sanitized == REDACTED:
        return "invalid"
    if sanitized != value:
        return "sensitive"
    return None


def parse_repository_url(value: str) -> SplitResult | None:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme in NETWORK_REPOSITORY_URL_SCHEMES:
        return parsed if valid_network_repository_url(parsed) else None
    if parsed.scheme == "file":
        return parsed
    return None


def valid_network_repository_url(parsed: SplitResult) -> bool:
    try:
        hostname = parsed.hostname
        _port = parsed.port
    except ValueError:
        return False
    return bool(parsed.netloc and hostname)


def redact_url_suffix_parameters(value: str) -> str:
    base_and_query, fragment_separator, fragment = value.partition("#")
    base, query_separator, query = base_and_query.partition("?")
    sanitized = base
    if query_separator:
        sanitized = f"{sanitized}?{redact_url_parameters(query)}"
    if fragment_separator:
        sanitized = f"{sanitized}#{redact_url_parameters(fragment)}"
    return sanitized


def redact_url_parameters(value: str) -> str:
    parts = URL_PARAMETER_SEPARATOR_RE.split(value)
    for index in range(0, len(parts), 2):
        key, separator, _parameter_value = parts[index].partition("=")
        if separator and is_secret_key(unquote_plus(key)):
            parts[index] = f"{key}={REDACTED}"
    return "".join(parts)
