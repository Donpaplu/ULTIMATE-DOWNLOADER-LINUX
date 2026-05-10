"""
routes/download_routes.py
Handles /api/download for all 7 modes:
  best_vid, custom_vid, audio, best_pl, custom_pl, audio_pl, batch

Linux fixes:
  - Removed --remote-components ejs:github (causes issues on some yt-dlp versions;
    use yt-dlp's built-in JS interpreter or install node separately if needed)
  - All subprocess calls routed through process_service which uses start_new_session=True
  - Output directories auto-created with os.makedirs if they don't exist
"""

from flask import Blueprint, request
import os
import re
import shlex

import services.process_service as ps
from services.process_service import run_cmd
from utils.helpers import stream, cookies_args, get_session_paths
from config.settings import YTDLP_BIN

download_bp = Blueprint("download", __name__)


def _parse_rate(raw: str) -> list:
    """Normalise user-typed speed limit and return yt-dlp --limit-rate args."""
    rate = raw.strip().upper()
    if not rate:
        return []
    rate = re.sub(r"\s+", "", rate)
    rate = re.sub(r"MBPS|MB/S|MB", "M", rate)
    rate = re.sub(r"KBPS|KB/S|KB", "K", rate)
    return ["--limit-rate", rate]


def _ensure_dir(path: str):
    """Create directory if it doesn't exist. Silently ignored on error."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


@download_bp.route("/api/download", methods=["POST"])
def download():
    d = request.json or {}

    mode       = d.get("mode", "best_vid")
    url        = d.get("url", "").strip()
    cust_path  = d.get("cust_path", "").strip()
    subs       = bool(d.get("subs", False))
    vformat    = d.get("vformat", "").strip()
    extra      = d.get("extra", "").strip()
    afmt       = d.get("afmt", "mp3")
    qual       = str(d.get("qual", 0))
    batch_file = d.get("batch_file", "").strip()
    pl_items   = d.get("pl_items", "").strip()
    batch_mode = d.get("batch_mode", "video")

    sp      = get_session_paths(d)
    ck_path = sp["ck"]

    rate_args  = _parse_rate(d.get("rate", ""))
    ck         = cookies_args(ck_path)
    extra_args = shlex.split(extra) if extra else []
    items_args = ["--playlist-items", pl_items] if pl_items else []

    subs_args = (
        ["--write-subs", "--write-auto-subs",
         "--sub-langs", "en.*,hi.*",
         "--embed-subs", "--convert-subs", "srt",
         "--compat-options", "no-keep-subs"]
        if subs else []
    )

    # Base args common to almost every command
    base_args = [YTDLP_BIN, "--newline", "--ignore-errors"] + ck + rate_args

    thumb_args = ["--embed-thumbnail", "--convert-thumbnails", "jpg"]

    BEST_FMT     = "bv*+ba/b"
    BEST_VID_FMT = BEST_FMT

    def generate():
        # ── 1. Best Video ─────────────────────────────────────
        if mode == "best_vid":
            saveto = cust_path or sp["vid"]
            _ensure_dir(saveto)
            cmd = (base_args
                   + ["-f", BEST_VID_FMT, "--merge-output-format", "mp4"]
                   + thumb_args + subs_args
                   + ["-N", "8", "--add-metadata",
                      "-o", os.path.join(saveto, "%(title)s.%(ext)s"), url])
            yield from run_cmd(cmd)
            yield f"\n[DIR] {saveto}\n"

        # ── 2. Custom Video ───────────────────────────────────
        elif mode == "custom_vid":
            saveto = cust_path or sp["vid"]
            _ensure_dir(saveto)
            fmt = vformat or BEST_VID_FMT
            cmd = (base_args
                   + ["-f", fmt, "--merge-output-format", "mp4"]
                   + thumb_args + subs_args + extra_args
                   + ["--add-metadata",
                      "-o", os.path.join(saveto, "%(title)s.%(ext)s"), url])
            yield from run_cmd(cmd)
            yield f"\n[DIR] {saveto}\n"

        # ── 3. Audio Only ─────────────────────────────────────
        elif mode == "audio":
            saveto = cust_path or sp["mus"]
            _ensure_dir(saveto)
            cmd = (base_args
                   + ["-f", "ba/b",
                      "-x", "--audio-format", afmt,
                      "--audio-quality", qual,
                      "--add-metadata", "-N", "4"]
                   + thumb_args
                   + ["-o", os.path.join(saveto, "%(title)s.%(ext)s"), url])
            yield from run_cmd(cmd)
            yield f"\n[DIR] {saveto}\n"

        # ── 4. Best Playlist ──────────────────────────────────
        elif mode == "best_pl":
            saveto = cust_path or sp["pl"]
            _ensure_dir(saveto)
            cmd = (base_args
                   + ["-f", BEST_FMT, "--merge-output-format", "mp4"]
                   + thumb_args + subs_args + items_args
                   + ["--add-metadata", "-N", "8",
                      "-o", os.path.join(saveto,
                          "%(playlist_title)s",
                          "%(playlist_index)s - %(title)s.%(ext)s"),
                      url])
            yield from run_cmd(cmd)
            yield f"\n[DIR] {saveto}\n"

        # ── 5. Custom Playlist ────────────────────────────────
        elif mode == "custom_pl":
            saveto = cust_path or sp["pl"]
            _ensure_dir(saveto)
            fmt = vformat or BEST_FMT
            cmd = (base_args
                   + ["-f", fmt, "--merge-output-format", "mp4"]
                   + thumb_args + subs_args + items_args
                   + ["-o", os.path.join(saveto,
                          "%(playlist_title)s",
                          "%(playlist_index)s - %(title)s.%(ext)s"),
                      url])
            yield from run_cmd(cmd)
            yield f"\n[DIR] {saveto}\n"

        # ── 6. Audio Playlist ─────────────────────────────────
        elif mode == "audio_pl":
            saveto = cust_path or sp["mus_pl"]
            _ensure_dir(saveto)
            cmd = (base_args
                   + ["-f", "ba/b",
                      "-x", "--audio-format", afmt,
                      "--add-metadata"]
                   + thumb_args + items_args
                   + ["-N", "4",
                      "-o", os.path.join(saveto,
                          "%(playlist_title)s",
                          "%(playlist_index)s - %(title)s.%(ext)s"),
                      url])
            yield from run_cmd(cmd)
            yield f"\n[DIR] {saveto}\n"

        # ── 7. Batch (.txt) — Per-URL loop in Python ──────────
        elif mode == "batch":
            if not batch_file or not os.path.exists(batch_file):
                yield "[ERR] Invalid batch file path.\n"
                return

            clean_urls = []
            with open(batch_file, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip().lstrip("\ufeff\u200b")
                    if line and not line.startswith("#"):
                        clean_urls.append(line)

            if not clean_urls:
                yield "[ERR] No valid URLs found in batch file.\n"
                return

            total  = len(clean_urls)
            saveto = cust_path or sp["vid"]
            _ensure_dir(saveto)
            fmt    = vformat if vformat else ("ba/b" if batch_mode == "audio" else BEST_FMT)

            for i, single_url in enumerate(clean_urls, 1):
                if ps.STOP_ALL_FLAG:
                    ps.STOP_ALL_FLAG = False
                    yield "\n[SYSTEM] Batch cancelled by user.\n"
                    break

                yield f"[BATCH_ITEM] {i} of {total}\n"

                if batch_mode == "audio":
                    cmd = (base_args
                           + ["-f", fmt,
                              "-x", "--audio-format", afmt,
                              "--add-metadata", "-N", "4"]
                           + thumb_args + extra_args
                           + ["-o", os.path.join(saveto, "%(title)s.%(ext)s"),
                              single_url])
                else:
                    cmd = (base_args
                           + ["-f", fmt, "--merge-output-format", "mp4"]
                           + thumb_args + subs_args + extra_args
                           + ["--add-metadata", "-N", "8",
                              "-o", os.path.join(saveto, "%(title)s.%(ext)s"),
                              single_url])

                yield from run_cmd(cmd)

            if ps.STOP_ALL_FLAG:
                ps.STOP_ALL_FLAG = False

            yield f"\n[DIR] Batch done → {saveto}\n"

        else:
            yield f"[ERR] Unknown mode: {mode}\n"

    return stream(generate())
