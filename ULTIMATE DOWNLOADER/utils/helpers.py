"""
utils/helpers.py
Shared utility functions: cookie args, session path extraction, streaming response.
"""

import os
from flask import Response, stream_with_context
from config.settings import COOKIES


def get_session_paths(d: dict) -> dict:
    """Extract session override paths from request payload."""
    sp = d.get("session_paths", {})
    from config.settings import OUTDIR, PL_OUTDIR, MUSIC_OUTDIR, MUSIC_PL_OUTDIR
    return {
        "vid":    sp.get("vid",    OUTDIR),
        "pl":     sp.get("pl",     PL_OUTDIR),
        "mus":    sp.get("mus",    MUSIC_OUTDIR),
        "mus_pl": sp.get("mus_pl", MUSIC_PL_OUTDIR),
        "ck":     sp.get("ck",     COOKIES),
    }


def cookies_args(cookie_path: str) -> list:
    """Returns --cookies flag list if the file exists, else empty list."""
    if cookie_path and os.path.exists(cookie_path):
        return ["--cookies", cookie_path]
    return []


def stream(gen) -> Response:
    """Wraps a generator into a streaming Flask response."""
    return Response(stream_with_context(gen), mimetype="text/plain")
