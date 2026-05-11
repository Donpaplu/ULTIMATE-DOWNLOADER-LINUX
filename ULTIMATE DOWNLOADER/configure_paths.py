#!/usr/bin/env python3
"""
configure_paths.py — Interactive path configurator for Ultimate Downloader
Lets you pick output directories and cookies file using a native GUI dialog,
then writes the choices permanently into config/settings.py.

Dialog priority:
  1. kdialog   (native KDE — best on Fedora KDE)
  2. zenity    (GTK — fallback for GNOME / other DEs)
  3. Terminal  (plain input — works everywhere, no GUI needed)
"""

import os
import re
import subprocess
import sys

# ── Locate config/settings.py relative to this script ────────
SCRIPT_DIR  = os.path.dirname(os.path.realpath(__file__))
SETTINGS    = os.path.join(SCRIPT_DIR, "config", "settings.py")

# ── Colours for terminal output ───────────────────────────────
R  = "\033[0;31m"
G  = "\033[0;32m"
Y  = "\033[1;33m"
C  = "\033[0;36m"
B  = "\033[1;34m"
NC = "\033[0m"

def _cmd(c): return subprocess.run(["which", c], capture_output=True).returncode == 0

HAS_KDIALOG = _cmd("kdialog")
HAS_ZENITY  = _cmd("zenity")


# ── Dialog wrappers ────────────────────────────────────────────

def pick_folder(title: str, start: str = "") -> str | None:
    """Open a native folder-picker dialog. Returns chosen path or None."""
    start = start if (start and os.path.isdir(start)) else os.path.expanduser("~")

    if HAS_KDIALOG:
        r = subprocess.run(
            ["kdialog", "--getexistingdirectory", start, "--title", title],
            capture_output=True, text=True
        )
        return r.stdout.strip() if r.returncode == 0 else None

    if HAS_ZENITY:
        r = subprocess.run(
            ["zenity", "--file-selection", "--directory",
             f"--title={title}", f"--filename={start}/"],
            capture_output=True, text=True
        )
        return r.stdout.strip() if r.returncode == 0 else None

    # Terminal fallback
    print(f"\n{Y}[Folder picker not available — type the path manually]{NC}")
    val = input(f"  {title}\n  Current: {start}\n  New path (Enter = keep): ").strip()
    return val if val else None


def pick_file(title: str, start: str = "", filter_name: str = "Text files",
              filter_pat: str = "*.txt") -> str | None:
    """Open a native file-picker dialog. Returns chosen file path or None."""
    start_dir = os.path.dirname(start) if (start and os.path.exists(start)) \
                else os.path.expanduser("~")

    if HAS_KDIALOG:
        r = subprocess.run(
            ["kdialog", "--getopenfilename", start_dir,
             f"{filter_name} ({filter_pat})", "--title", title],
            capture_output=True, text=True
        )
        return r.stdout.strip() if r.returncode == 0 else None

    if HAS_ZENITY:
        r = subprocess.run(
            ["zenity", "--file-selection",
             f"--title={title}",
             f"--filename={start}",
             f"--file-filter={filter_name} | {filter_pat}"],
            capture_output=True, text=True
        )
        return r.stdout.strip() if r.returncode == 0 else None

    print(f"\n{Y}[File picker not available — type the path manually]{NC}")
    val = input(f"  {title}\n  Current: {start}\n  New path (Enter = keep): ").strip()
    return val if val else None


# ── Read current values from settings.py ─────────────────────

def read_settings() -> dict:
    """Parse the current path values from config/settings.py."""
    if not os.path.exists(SETTINGS):
        print(f"{R}[ERROR]{NC} Cannot find {SETTINGS}")
        sys.exit(1)

    content = open(SETTINGS).read()
    keys = ["COOKIES", "OUTDIR", "PL_OUTDIR", "MUSIC_OUTDIR", "MUSIC_PL_OUTDIR"]
    vals = {}
    for k in keys:
        m = re.search(rf'^{k}\s*=\s*["\'](.+?)["\']', content, re.MULTILINE)
        vals[k] = m.group(1) if m else ""
    return vals


# ── Write updated values back to settings.py ─────────────────

def write_settings(new_vals: dict):
    """Replace the path assignments in config/settings.py in-place."""
    content = open(SETTINGS).read()

    for key, val in new_vals.items():
        # Match:  KEY  =  "..." or '...'
        # Replace the quoted value, preserve surrounding whitespace
        escaped = val.replace("\\", "\\\\")
        content = re.sub(
            rf'^({key}\s*=\s*)["\'].*?["\']',
            rf'\g<1>"{escaped}"',
            content,
            flags=re.MULTILINE
        )

    with open(SETTINGS, "w") as f:
        f.write(content)


# ── Pretty print a path diff ──────────────────────────────────

def show_change(label: str, old: str, new: str):
    if new and new != old:
        print(f"  {G}✔{NC} {label}")
        print(f"      {Y}old:{NC} {old or '(empty)'}")
        print(f"      {G}new:{NC} {new}")
    else:
        print(f"  {C}—{NC} {label}  {Y}(unchanged){NC}")


# ── Main menu ─────────────────────────────────────────────────

FIELDS = [
    ("OUTDIR",          "📁 Video Output Directory",          "folder"),
    ("PL_OUTDIR",       "📁 Playlist Output Directory",       "folder"),
    ("MUSIC_OUTDIR",    "📁 Music Output Directory",          "folder"),
    ("MUSIC_PL_OUTDIR", "📁 Music Playlist Output Directory", "folder"),
    ("COOKIES",         "🍪 Cookies File (.txt)",             "file"),
]

def header():
    print(f"\n{C}{'═'*56}{NC}")
    print(f"{C}   Ultimate Downloader — Path Configurator{NC}")
    if HAS_KDIALOG:
        print(f"{G}   GUI: kdialog (KDE native){NC}")
    elif HAS_ZENITY:
        print(f"{G}   GUI: zenity (GTK){NC}")
    else:
        print(f"{Y}   GUI: terminal fallback (kdialog/zenity not found){NC}")
    print(f"{C}{'═'*56}{NC}\n")


def menu(current: dict):
    print(f"{B}Current settings:{NC}")
    for i, (key, label, _) in enumerate(FIELDS, 1):
        val = current.get(key, "")
        status = G + "✔" + NC if val else R + "✘" + NC
        print(f"  {status} [{i}] {label}")
        print(f"        {Y}{val or '(not set)'}{NC}")
    print()
    print(f"  {B}[a]{NC} Change ALL at once")
    print(f"  {B}[s]{NC} Save & exit")
    print(f"  {B}[q]{NC} Quit without saving")
    print()


def pick_one(key: str, label: str, kind: str, current_val: str) -> str | None:
    print(f"\n{C}→ {label}{NC}")
    print(f"  Current: {Y}{current_val or '(not set)'}{NC}")

    if kind == "folder":
        chosen = pick_folder(label, current_val)
    else:
        chosen = pick_file(label, current_val,
                           filter_name="Cookie files / Text files",
                           filter_pat="*.txt")

    if chosen:
        print(f"  {G}Selected:{NC} {chosen}")
    else:
        print(f"  {Y}No selection — keeping current value.{NC}")
    return chosen


def run():
    header()

    if not os.path.exists(SETTINGS):
        print(f"{R}[ERROR]{NC} {SETTINGS} not found.")
        print("Make sure you're running this from the app's root folder.")
        sys.exit(1)

    current = read_settings()
    pending = dict(current)   # working copy — not written until [s]

    while True:
        menu(pending)
        choice = input("Choose [1-5 / a / s / q]: ").strip().lower()

        if choice == "q":
            print(f"\n{Y}Exiting without saving.{NC}\n")
            sys.exit(0)

        elif choice == "s":
            # Diff + confirm
            changes = {k: v for k, v in pending.items() if v != current.get(k)}
            if not changes:
                print(f"\n{Y}No changes to save.{NC}\n")
                sys.exit(0)

            print(f"\n{B}Changes to be written:{NC}")
            for key, label, _ in FIELDS:
                show_change(label, current.get(key, ""), pending.get(key, ""))

            confirm = input(f"\n{G}Write these to config/settings.py? [y/N]:{NC} ").strip().lower()
            if confirm == "y":
                write_settings(pending)
                print(f"\n{G}✔ config/settings.py updated successfully!{NC}")
                print(f"  Restart the app (./start.sh) for changes to take effect.\n")
                sys.exit(0)
            else:
                print(f"{Y}Not saved — continuing.{NC}\n")

        elif choice == "a":
            print(f"\n{B}Picking all paths one by one…{NC}")
            for key, label, kind in FIELDS:
                result = pick_one(key, label, kind, pending.get(key, ""))
                if result:
                    pending[key] = result

        elif choice in ("1", "2", "3", "4", "5"):
            idx = int(choice) - 1
            key, label, kind = FIELDS[idx]
            result = pick_one(key, label, kind, pending.get(key, ""))
            if result:
                pending[key] = result

        else:
            print(f"{Y}  Invalid choice — try again.{NC}")


if __name__ == "__main__":
    run()
