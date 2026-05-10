"""
services/cleanup_service.py
Handles the Garbage Collection Queue with a background retry loop.
Linux version — no Windows chmod(0o777) tricks needed; os.remove works directly.
"""

import os
import re
import time
import threading

# Store the base names of cancelled/skipped files permanently for the session
TRASH_QUEUE = set()

_MEDIA_EXTS = frozenset([
    ".mp4", ".mkv", ".webm", ".flv", ".avi", ".mov", ".wmv",
    ".m4a", ".mp3", ".opus", ".wav", ".ogg", ".aac", ".flac"
])

_META_EXTS = frozenset([
    ".jpg", ".jpeg", ".png", ".webp",
    ".vtt", ".srt", ".ass", ".ttml",
    ".json", ".description", ".mhtml", ".xml"
])


def add_to_trash(base_name: str):
    """Adds a cancelled file's base name to the trash queue."""
    if base_name:
        TRASH_QUEUE.add(base_name.lower())


def _force_delete(path: str):
    """
    Attempts to delete a file. On Linux, file locks are per-process —
    once yt-dlp/ffmpeg exit the lock is immediately released, so a simple
    os.remove is sufficient. Fails silently so the retry loop can retry.
    """
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _is_yt_dlp_debris(filename: str) -> bool:
    """Accurately spots yt-dlp temporary markers."""
    lower = filename.lower()
    return bool(re.search(r'\.(f\d{1,4}|temp|part|ytdl|frag|tmp)\b', lower))


def get_valid_media_stems(directory: str):
    """Scans the folder and returns stems of successfully finished media files."""
    valid_stems = set()
    for root, _, files in os.walk(directory):
        if root[len(directory):].count(os.sep) > 1:
            continue
        for file in files:
            lower = file.lower()
            stem, ext = os.path.splitext(lower)
            if ext in _MEDIA_EXTS and not _is_yt_dlp_debris(lower):
                valid_stems.add(stem)
    return valid_stems


def _sweep_directories(directories):
    """The actual cleaning logic that scans the folders."""
    for d in directories:
        if not d or not os.path.exists(d):
            continue

        valid_media_stems = get_valid_media_stems(d)

        for root, _, files in os.walk(d):
            if root[len(d):].count(os.sep) > 1:
                continue

            for file in files:
                file_path = os.path.join(root, file)
                lower_file = file.lower()
                file_stem, ext = os.path.splitext(lower_file)

                # 1. Always kill obvious yt-dlp debris (.part, .ytdl, etc.)
                if _is_yt_dlp_debris(lower_file):
                    _force_delete(file_path)
                    continue

                # 2. True Orphan Detection — metadata with no finished video
                if ext in _META_EXTS:
                    is_orphan = True
                    for v_stem in valid_media_stems:
                        if lower_file.startswith(v_stem):
                            is_orphan = False
                            break
                    if is_orphan:
                        _force_delete(file_path)
                        continue

                # 3. Targeted Queue fallback for edge cases
                for trash_base in TRASH_QUEUE:
                    if lower_file.startswith(trash_base + ".") or file_stem == trash_base:
                        if ext not in _MEDIA_EXTS:
                            _force_delete(file_path)
                        break


def run_garbage_collector(directories):
    """
    Spawns a background thread that sweeps directories 5 times over ~10 seconds.
    On Linux, yt-dlp releases file handles almost immediately after process exit,
    so the initial delay is shorter (1 s instead of 2 s).
    """
    def _work():
        time.sleep(1.0)  # Linux releases locks faster than Windows
        for _ in range(5):
            _sweep_directories(directories)
            time.sleep(1.5)
        # We do NOT clear TRASH_QUEUE — cancelled files stay blacklisted for the session.

    t = threading.Thread(target=_work, daemon=True)
    t.start()
