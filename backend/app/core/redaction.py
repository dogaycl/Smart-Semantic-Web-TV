"""Helpers for stripping secrets out of text that gets persisted or returned to clients.

Provider errors are built from raw HTTP client exceptions, which embed the full request
URL - including query parameters such as `key=<API_KEY>`. Those messages are stored on
`Channel.stream_error`, which `GET /api/channels` returns to any caller, so they must be
scrubbed before they leave the provider layer.
"""

from __future__ import annotations

import re

from app.core.config import get_settings

REDACTED = "<redacted>"

_SENSITIVE_QUERY_PARAM_RE = re.compile(
    r"(?i)\b(key|api_key|apikey|access_token|token|password|secret)=[^&\s'\"]+"
)


def redact_secrets(value: str | None) -> str | None:
    """Return `value` with API keys and other credential-shaped values masked."""
    if not value:
        return value

    redacted = _SENSITIVE_QUERY_PARAM_RE.sub(lambda match: f"{match.group(1)}={REDACTED}", value)

    # Also mask configured secrets verbatim, in case they appear outside a query string.
    settings = get_settings()
    for secret in (
        settings.youtube_api_key,
        settings.gemini_api_key,
        settings.tmdb_api_key,
        settings.tmdb_access_token,
    ):
        if secret and len(secret) >= 8:
            redacted = redacted.replace(secret, REDACTED)

    return redacted
