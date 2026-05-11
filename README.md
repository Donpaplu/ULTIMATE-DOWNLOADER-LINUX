# yt-dlp Ultimate Downloader — Linux Edition

A local web UI for yt-dlp built with Flask. Runs in your browser at `localhost:5000` and wraps yt-dlp with a clean interface for downloading videos, playlists, and audio.

---

## Features

- **7 download modes** — single video, custom format, audio only, playlist (best/custom/audio), and batch (.txt)
- **Format picker** — browse all available formats in a modal and select up to two to merge
- **Live progress** — dual progress bars (video + audio track) with speed, ETA, and file counter
- **Playback controls** — pause, resume, skip current file, or cancel everything mid-download
- **Tools panel** — update yt-dlp, clear cache, inspect formats, list subtitles, fetch metadata, download thumbnails/subtitles/descriptions separately
- **Cookies support** — point it at your browser-exported cookies.txt for age-gated or member content
- **Speed limiter** — works across all modes
- **Fragment cleanup** — automatically removes .part/.ytdl files and orphaned metadata on cancel/skip
- **Session path overrides** — change output directories per-session from the UI without editing config

---

## Requirements

- Fedora / RPM-based Linux (uses `dnf`)
- Python 3.9+
- ffmpeg (installed by `install_deps.sh`)
- AtomicParsley (optional, for audio thumbnail embedding)

---

## Quick Start

```bash
# First time only
chmod +x install_deps.sh start.sh
./install_deps.sh        # installs ffmpeg + Python deps via dnf (needs sudo)

# Every launch
./start.sh               # sets up venv, installs Python packages, opens browser
```

Browser opens automatically at **http://127.0.0.1:5000**

---

## Configuration

Edit `config/settings.py` to set your permanent output paths and cookies file:

```python
COOKIES         = "/path/to/cookies.txt"
OUTDIR          = "/path/to/videos"
PL_OUTDIR       = "/path/to/videos/Playlists"
MUSIC_OUTDIR    = "/path/to/videos/Music"
MUSIC_PL_OUTDIR = "/path/to/videos/Music/Playlists"
```

Or override any of these per-session from the **Path Settings** panel at the bottom of the UI.

---

## Project Structure

```
├── app.py                  — Flask entry point
├── start.sh                — Launcher (creates venv, installs packages)
├── install_deps.sh         — System dependency installer (run once)
├── config/settings.py      — Paths and constants — edit this
├── routes/                 — API endpoints (download, tools, formats, control)
├── services/               — Subprocess management and fragment cleanup
├── templates/index.html    — Single-page UI
└── static/                 — CSS and JS
```

---

## Stack

- **Backend** — Python / Flask, yt-dlp, psutil
- **Frontend** — Vanilla JS, plain CSS (no frameworks)
- **Downloader** — yt-dlp + ffmpeg
