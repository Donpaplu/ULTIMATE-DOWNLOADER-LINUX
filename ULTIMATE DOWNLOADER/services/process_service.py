"""
services/process_service.py
Handles subprocess creation, streaming, and control flags.
Linux version — no Windows STARTUPINFO / creationflags needed.
"""

import subprocess
import sys
import os

# ── Global state ────────────────────────────────────────────
CURRENT_PROC  = None   # Active streaming subprocess
STOP_ALL_FLAG = False  # Set True → batch loop will break after current file ends


# ── Platform helpers ─────────────────────────────────────────
def _streaming_popen_kwargs() -> dict:
    """
    Returns extra kwargs for Popen used in run_cmd().
    On Linux: start the process in a new process group so we can
    send SIGINT/SIGTERM to the whole group (yt-dlp + ffmpeg children)
    without affecting the Flask parent.
    """
    if sys.platform == "win32":
        # Windows path kept for cross-platform safety but not used on Linux
        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        return {
            "startupinfo": si,
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP,
        }
    # Linux: new session → own process group → SIGINT won't hit Flask
    return {"start_new_session": True}


def _silent_run_kwargs() -> dict:
    """
    Extra kwargs for one-shot subprocess.run() calls (format fetch, metadata, etc.).
    On Linux there are no console windows to suppress; returns empty dict.
    On Windows returns CREATE_NO_WINDOW for safety.
    """
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


# ── Core command runner (generator) ─────────────────────────
def run_cmd(cmd):
    """
    Runs cmd as a subprocess, yielding each line of stdout/stderr.
    Sets CURRENT_PROC so control routes can pause/kill it.
    """
    global CURRENT_PROC

    cmd = [str(c) for c in cmd]

    try:
        yield f"[CMD] {' '.join(cmd)}\n\n"

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **_streaming_popen_kwargs(),
        )
        CURRENT_PROC = proc

        for line in iter(proc.stdout.readline, ""):
            yield line

        proc.stdout.close()
        proc.wait()

        if proc.returncode == 0:
            yield "\n[OK] Process completed successfully.\n"
        else:
            # returncode 1 / -2 (SIGINT) / -15 (SIGTERM) are normal on skip/cancel
            if proc.returncode not in (1, -1, -2, -15, 4294967295):
                yield f"\n[ERR] Process exited with code {proc.returncode}\n"

    except FileNotFoundError:
        yield (
            f"[ERR] '{cmd[0]}' not found.\n"
            "Ensure yt-dlp is installed: run ./start.sh to activate the venv,\n"
            "or: pip install yt-dlp\n"
        )
    except Exception as exc:
        yield f"[ERR] {exc}\n"
    finally:
        CURRENT_PROC = None
