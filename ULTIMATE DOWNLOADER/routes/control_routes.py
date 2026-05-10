"""
routes/control_routes.py
Handles /api/control and /api/shutdown.
Linux version — uses POSIX signals (SIGINT/SIGTERM/SIGKILL) instead of
Windows Console Control Events. Pause/Resume use SIGSTOP/SIGCONT.
"""

from flask import Blueprint, request
import json
import sys
import os
import signal
import threading
import time

import psutil
import services.process_service as ps
from services.cleanup_service import add_to_trash, run_garbage_collector
from utils.helpers import get_session_paths

control_bp = Blueprint("control", __name__)


def _json(obj, code=200):
    return json.dumps(obj), code, {"Content-Type": "application/json"}


def _resume_process_tree(p: psutil.Process):
    """
    Resumes a suspended process and all its children.
    On Linux uses SIGCONT; on Windows uses psutil's resume().
    Critical: must wake processes before sending kill signals so they
    can process the signal and release file handles cleanly.
    """
    try:
        for child in p.children(recursive=True):
            try:
                if sys.platform == "win32":
                    child.resume()
                else:
                    child.send_signal(signal.SIGCONT)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if sys.platform == "win32":
            p.resume()
        else:
            p.send_signal(signal.SIGCONT)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


def _kill_tree(p: psutil.Process):
    """Kill the process and all its children (ffmpeg, etc.)."""
    for child in p.children(recursive=True):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        p.kill()
    except psutil.NoSuchProcess:
        pass


@control_bp.route("/api/control", methods=["POST"])
def control():
    d      = request.json or {}
    action = d.get("action", "")
    mode   = d.get("mode", "")
    sp     = get_session_paths(d)

    current_file = d.get("current_file", "")
    if current_file:
        just_the_filename = os.path.basename(current_file)
        base_name = os.path.splitext(just_the_filename)[0]
    else:
        base_name = ""

    active_dirs = [sp["vid"], sp["pl"], sp["mus"], sp["mus_pl"]]

    # No process running
    if not ps.CURRENT_PROC or ps.CURRENT_PROC.poll() is not None:
        if action == "cancel_all":
            run_garbage_collector(active_dirs)
            return _json({"status": "Cleaned up leftover files"})
        return _json({"error": "No active process"}, 400)

    try:
        p = psutil.Process(ps.CURRENT_PROC.pid)

        # ── Pause ────────────────────────────────────────────
        if action == "pause":
            # Linux: SIGSTOP cannot be caught or ignored — guaranteed pause
            for child in p.children(recursive=True):
                try:
                    child.send_signal(signal.SIGSTOP)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            p.send_signal(signal.SIGSTOP)
            return _json({"status": "Paused"})

        # ── Resume ───────────────────────────────────────────
        elif action == "resume":
            _resume_process_tree(p)
            return _json({"status": "Resumed"})

        # ── Skip Current File ─────────────────────────────────
        elif action == "cancel_current":
            is_batch = (mode == "batch")

            # Wake up first so it can process signals and release locks
            _resume_process_tree(p)

            if is_batch:
                # Batch mode: kill current yt-dlp process; Python loop continues to next URL
                _kill_tree(p)
            else:
                # Playlist mode: SIGINT → yt-dlp skips current item and continues
                # We send to the process group (negative pid) so ffmpeg children also get it
                try:
                    os.killpg(os.getpgid(ps.CURRENT_PROC.pid), signal.SIGINT)
                except (ProcessLookupError, OSError):
                    try:
                        p.send_signal(signal.SIGINT)
                    except psutil.NoSuchProcess:
                        pass

            add_to_trash(base_name)
            run_garbage_collector(active_dirs)
            return _json({"status": "Skipping current file — cleaning fragments"})

        # ── Cancel All ───────────────────────────────────────
        elif action == "cancel_all":
            ps.STOP_ALL_FLAG = True
            _resume_process_tree(p)
            _kill_tree(p)
            add_to_trash(base_name)
            run_garbage_collector(active_dirs)
            return _json({"status": "Cancelled everything — sweeping fragments"})

        else:
            return _json({"error": "Unknown action"}, 400)

    except psutil.NoSuchProcess:
        return _json({"error": "Process already ended"}, 400)
    except Exception as e:
        return _json({"error": str(e)}, 500)


# ── Shutdown endpoint ─────────────────────────────────────────
@control_bp.route("/api/shutdown", methods=["POST"])
def shutdown():
    def _do_exit():
        time.sleep(0.6)
        os._exit(0)

    threading.Thread(target=_do_exit, daemon=True).start()
    return _json({"status": "Server shutting down. You can close this tab."})
