"""
routes/tools_routes.py
Handles /api/tools — yt-dlp maintenance & info tools.
Linux: subprocess.run() calls don't need CREATE_NO_WINDOW.
"""

from flask import Blueprint, request
import subprocess
import json
import os

from services.process_service import run_cmd, _silent_run_kwargs
from utils.helpers import stream, cookies_args, get_session_paths
from config.settings import YTDLP_BIN, OUTDIR

tools_bp = Blueprint("tools", __name__)


@tools_bp.route("/api/tools", methods=["POST"])
def tools():
    d     = request.json or {}
    tool  = d.get("tool", "")
    url   = d.get("url", "").strip()
    fcode = d.get("fcode", "").strip()

    sp     = get_session_paths(d)
    ck     = cookies_args(sp["ck"])
    outdir = sp.get("vid", OUTDIR)

    def generate():
        if tool == "update":
            yield "[ Updating yt-dlp... ]\n"
            yield from run_cmd([YTDLP_BIN, "-U"])

        elif tool == "cache":
            yield "[ Clearing yt-dlp cache... ]\n"
            yield from run_cmd([YTDLP_BIN, "--rm-cache-dir"])

        elif tool == "version":
            yield "[ yt-dlp version ]\n"
            yield from run_cmd([YTDLP_BIN, "--version"])

        elif tool == "formats":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            yield f"[ Available formats for: {url} ]\n"
            yield from run_cmd([YTDLP_BIN] + ck + ["-F", url])

        elif tool == "subs":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            yield f"[ Available subtitles for: {url} ]\n"
            yield from run_cmd([YTDLP_BIN] + ck + ["--list-subs", url])

        elif tool == "info":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            yield f"[ Metadata for: {url} ]\n\n"
            try:
                res = subprocess.run(
                    [YTDLP_BIN] + ck + ["--dump-json", "--no-playlist", url],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30,
                    **_silent_run_kwargs()
                )
                meta = json.loads(res.stdout)
                fields = ["title", "uploader", "channel", "upload_date",
                          "duration_string", "view_count", "like_count",
                          "webpage_url", "description"]
                for k in fields:
                    if k in meta:
                        val = str(meta[k])
                        if k == "description":
                            val = val[:400] + " ..." if len(val) > 400 else val
                        yield f"  {k:<20}: {val}\n"
            except Exception as exc:
                yield f"[ERR] Could not parse metadata: {exc}\n"

        elif tool == "get_url":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            fmt = fcode or "bv*+ba/b"
            yield f"[ Direct URL (format: {fmt}) ]\n"
            yield from run_cmd([YTDLP_BIN] + ck + ["-f", fmt, "-g", url])

        elif tool == "thumbnail":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            yield f"[ Downloading thumbnail → {outdir} ]\n"
            yield from run_cmd(
                [YTDLP_BIN] + ck
                + ["--write-thumbnail", "--convert-thumbnails", "jpg",
                   "--skip-download",
                   "-o", os.path.join(outdir, "%(title)s.%(ext)s"), url]
            )

        elif tool == "subs_only":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            yield f"[ Downloading subtitles only → {outdir} ]\n"
            yield from run_cmd(
                [YTDLP_BIN] + ck
                + ["--write-subs", "--write-auto-subs",
                   "--sub-langs", "en.*,hi.*",
                   "--skip-download",
                   "-o", os.path.join(outdir, "%(title)s.%(ext)s"), url]
            )

        elif tool == "description":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            yield f"[ Downloading description → {outdir} ]\n"
            yield from run_cmd(
                [YTDLP_BIN] + ck
                + ["--write-description", "--skip-download",
                   "-o", os.path.join(outdir, "%(title)s.%(ext)s"), url]
            )

        elif tool == "resume":
            if not url:
                yield "[ERR] A URL is required.\n"
                return
            yield f"[ Resuming download: {url} ]\n"
            yield from run_cmd(
                [YTDLP_BIN, "--newline"] + ck
                + ["-f", "bv*+ba[original]/bv*+ba/b",
                   "--continue", "--merge-output-format", "mp4",
                   "--add-metadata", "-N", "8",
                   "-o", os.path.join(outdir, "%(title)s.%(ext)s"), url]
            )

        else:
            yield f"[ERR] Unknown tool: '{tool}'\n"

    return stream(generate())
