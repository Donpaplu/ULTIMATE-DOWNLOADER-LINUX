# yt-dlp Ultimate Downloader — Linux Edition (Fedora KDE)

## Quick Start

### First-time setup (run once)
```bash
chmod +x install_deps.sh start.sh
./install_deps.sh        # installs ffmpeg, python3 via dnf (needs sudo)
./start.sh               # creates venv, installs Python packages, launches app
```

### Every subsequent launch
```bash
./start.sh
```
The browser opens automatically at **http://127.0.0.1:5000**

---

## Project Structure

```
ultimate-downloader-linux/
├── app.py                    ← Flask init, blueprint registration
├── start.sh                  ← One-click launcher (creates venv automatically)
├── install_deps.sh           ← System dependency installer (run once, needs sudo)
├── requirements.txt          ← Python packages (flask, psutil)
├── DEPENDENCIES.txt          ← Full dependency reference doc
├── config/
│   └── settings.py           ← Paths, constants, language map — EDIT THIS
├── routes/
│   ├── download_routes.py    ← /api/download  (all 7 modes)
│   ├── tools_routes.py       ← /api/tools
│   ├── format_routes.py      ← /api/get_formats, /api/config
│   └── control_routes.py     ← /api/control, /api/shutdown
├── services/
│   ├── process_service.py    ← subprocess runner, POSIX signals, flags
│   └── cleanup_service.py    ← fragment cleanup logic
├── utils/
│   └── helpers.py
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── logo.png              ← (optional) drop your logo here
├── venv/                     ← created automatically by start.sh
└── logs/
```

---

## Configuration

Edit **`config/settings.py`** to set permanent paths:

```python
COOKIES         = "/run/media/Papludon/Deepanshu/tools/ULTIMATE DOWNLAODER/cookies.txt"
OUTDIR          = "/run/media/Papludon/sda2/videos"
PL_OUTDIR       = "/run/media/Papludon/sda2/videos/Playlists"
MUSIC_OUTDIR    = "/run/media/Papludon/sda2/videos/Music"
MUSIC_PL_OUTDIR = "/run/media/Papludon/sda2/videos/Music/Playlists"
```

You can also override these per-session in the **Path Settings** panel in the UI (bottom of the page).

### Linux path format examples
| What                    | Example path                                    |
|-------------------------|-------------------------------------------------|
| External drive          | `/run/media/YourUser/DriveName/Videos`          |
| Home folder             | `/home/Papludon/Videos`                         |
| Batch .txt file         | `/home/Papludon/Downloads/urls.txt`             |
| Cookies file            | `/home/Papludon/.config/yt-dlp/cookies.txt`    |

---

## Linux-Specific Changes vs Windows Version

| Feature            | Windows                          | Linux (this version)             |
|--------------------|----------------------------------|----------------------------------|
| Process pause      | `psutil.suspend()` (Win32)       | `SIGSTOP` (guaranteed, uncatchable) |
| Process resume     | `psutil.resume()`                | `SIGCONT`                        |
| Skip current file  | `CTRL_BREAK_EVENT` via ctypes    | `SIGINT` to process group (pgid) |
| Cancel all         | `p.kill()` + tree kill           | `SIGKILL` to process tree        |
| No console popup   | `CREATE_NO_WINDOW` flag          | Not needed — no GUI consoles on Linux |
| Process isolation  | `CREATE_NEW_PROCESS_GROUP`       | `start_new_session=True` (own pgid) |
| File lock release  | Retry with `chmod(0o777)`        | Locks release immediately on process exit |
| Launcher           | `run_app.bat` + pythonw.exe      | `start.sh` + venv                |

---

## Fixes Inherited from Windows Version

All 7 original fixes are preserved and working on Linux:

1. **Cleanup** — retries for file locks (Linux releases faster, delay reduced to 1 s)
2. **Skip Current File** — batch kills process, playlist sends SIGINT to pgid
3. **Speed Limit for Audio Playlist** — rate field included in all modes
4. **Multi-Audio Language Names** — language column in format picker
5. **Batch Progress Bar** — [BATCH_ITEM] markers reset bars per file
6. **No Console Window Popup** — not applicable on Linux (no popups)
7. **Stop Server Button** — `/api/shutdown` endpoint with `os._exit(0)`

---

## Troubleshooting

**`yt-dlp: command not found`**
→ The venv binary is used automatically. If it fails, run `./start.sh` again.

**`ffmpeg not found`**
→ Run `./install_deps.sh` or manually: `sudo dnf install ffmpeg`

**`No module named 'flask'`**
→ Run `./start.sh` — it installs all Python packages into the venv first.

**Browser doesn't open automatically**
→ Open manually: http://127.0.0.1:5000

**Clipboard paste button doesn't work**
→ Allow clipboard access in your browser settings, or use Ctrl+V directly.

**`[download] ERROR: ... Sign in to confirm your age`**
→ Your cookies.txt is needed. Export it from Firefox/Chrome and update the path in settings.py.

**External drive path not working**
→ Make sure the drive is mounted. Check: `lsblk` or `ls /run/media/Papludon/`

---

## Updating yt-dlp

Either use the **⬆ Update yt-dlp** button in the Tools section of the UI,
or run from terminal:
```bash
./venv/bin/pip install --upgrade yt-dlp
```
