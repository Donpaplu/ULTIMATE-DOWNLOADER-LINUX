"""
routes/format_routes.py
Handles /api/get_formats — fetches format list for the picker modal.
Linux: _silent_run_kwargs() returns {} so no platform-specific flags needed.
"""

from flask import Blueprint, request
import subprocess
import json
import re
import os

from services.process_service import _silent_run_kwargs
from utils.helpers import cookies_args, get_session_paths
from config.settings import (
    YTDLP_BIN, COOKIES, OUTDIR, PL_OUTDIR, MUSIC_OUTDIR, MUSIC_PL_OUTDIR,
    LANG_MAP
)

format_bp = Blueprint("format", __name__)


def _lang_label(raw_lang: str) -> str:
    """Convert ISO language code to human-readable name."""
    if not raw_lang:
        return ""
    code = raw_lang.lower().split("-")[0].split("_")[0]
    return LANG_MAP.get(code, raw_lang)


@format_bp.route("/api/get_formats", methods=["POST"])
def get_formats():
    d          = request.json or {}
    url        = d.get("url", "").strip()
    batch_file = d.get("batch_file", "").strip()
    pl_items   = d.get("pl_items", "").strip()

    # For batch mode: grab first URL from the file to preview formats
    if not url and batch_file:
        if os.path.exists(batch_file):
            with open(batch_file, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        url = line
                        break
        if not url:
            return (
                json.dumps({"error": "No valid URL found in batch file."}),
                400, {"Content-Type": "application/json"}
            )

    if not url:
        return (
            json.dumps({"error": "URL required"}),
            400, {"Content-Type": "application/json"}
        )

    sp = get_session_paths(d)
    ck = cookies_args(sp["ck"])

    target_item = "1"
    if pl_items:
        m = re.search(r"\d+", pl_items)
        if m:
            target_item = m.group()

    try:
        res = subprocess.run(
            [YTDLP_BIN] + ck + ["-J", "--playlist-items", target_item, url],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=45,
            **_silent_run_kwargs()
        )

        if res.returncode != 0:
            err_hint = res.stderr[:300] if res.stderr else "Unknown error"
            return (
                json.dumps({"error": f"yt-dlp failed: {err_hint}"}),
                500, {"Content-Type": "application/json"}
            )

        info = json.loads(res.stdout)

        # Unwrap playlist wrapper if needed
        if info.get("_type") == "playlist" or "entries" in info:
            entries = [e for e in info.get("entries", []) if e]
            if not entries:
                return (
                    json.dumps({"error": "Playlist is empty or unavailable."}),
                    400, {"Content-Type": "application/json"}
                )
            info = entries[0]

        formats = []
        for f in info.get("formats", []):
            fs     = f.get("filesize") or f.get("filesize_approx")
            fs_str = f"{fs / 1_048_576:.1f} MB" if isinstance(fs, (int, float)) else "—"

            lang_code  = f.get("language") or ""
            lang_label = _lang_label(lang_code)

            note = str(f.get("format_note", "") or "")
            if not lang_label and note:
                for code, name in LANG_MAP.items():
                    if code in note.lower() or name.lower() in note.lower():
                        lang_label = name
                        break

            formats.append({
                "id":         str(f.get("format_id", "?")),
                "ext":        str(f.get("ext", "?")),
                "resolution": str(
                    f.get("resolution")
                    or (f"{f.get('height')}p" if f.get("height") else "audio only")
                ),
                "fps":      str(f.get("fps", "") or ""),
                "vcodec":   str(f.get("vcodec", "none") or "none").split(".")[0],
                "acodec":   str(f.get("acodec", "none") or "none").split(".")[0],
                "filesize": fs_str,
                "note":     note,
                "language": lang_label,
            })

        return (
            json.dumps({"title": info.get("title", ""), "formats": formats}),
            200, {"Content-Type": "application/json"}
        )

    except json.JSONDecodeError:
        return (
            json.dumps({"error": "Could not parse yt-dlp output. Is the URL valid?"}),
            500, {"Content-Type": "application/json"}
        )
    except Exception as exc:
        return (
            json.dumps({"error": f"Server Error: {str(exc)}"}),
            500, {"Content-Type": "application/json"}
        )


@format_bp.route("/api/config", methods=["GET"])
def get_config():
    return (
        json.dumps({
            "cookies":         COOKIES,
            "outdir":          OUTDIR,
            "pl_outdir":       PL_OUTDIR,
            "music_outdir":    MUSIC_OUTDIR,
            "music_pl_outdir": MUSIC_PL_OUTDIR,
        }),
        200, {"Content-Type": "application/json"}
    )
