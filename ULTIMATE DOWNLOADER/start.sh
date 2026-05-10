#!/usr/bin/env bash
# ============================================================
# start.sh — Launch Ultimate Downloader (Linux)
# - Creates a Python venv inside the app folder on first run
# - Installs / upgrades Flask, psutil, yt-dlp into the venv
# - Starts Flask and opens the browser automatically
# ============================================================

set -eu

# ── Paths ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo -e "${CYAN}"
echo "  ██╗   ██╗██╗  ████████╗██╗███╗   ███╗ █████╗ ████████╗███████╗"
echo "  ██║   ██║██║  ╚══██╔══╝██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝"
echo "  ██║   ██║██║     ██║   ██║██╔████╔██║███████║   ██║   █████╗  "
echo "  ██║   ██║██║     ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  "
echo "  ╚██████╔╝███████╗██║   ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗"
echo "   ╚═════╝ ╚══════╝╚═╝   ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝"
echo "                    DOWNLOADER  —  Linux Edition"
echo -e "${NC}"

# ── Check Python 3 ───────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  error "python3 not found. Run: sudo dnf install python3"
fi

PYTHON3_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "System Python: $PYTHON3_VER"

# ── Create venv if it doesn't exist ──────────────────────────
if [ ! -d "$VENV_DIR" ]; then
  info "Creating virtual environment in $VENV_DIR …"
  python3 -m venv "$VENV_DIR" || error "Failed to create venv. Run: sudo dnf install python3-pip"
  info "Virtual environment created."
else
  info "Virtual environment found: $VENV_DIR"
fi

# ── Upgrade pip silently ──────────────────────────────────────
info "Upgrading pip…"
"$PIP" install --upgrade pip -q

# ── Install / upgrade Python dependencies ────────────────────
info "Installing Python dependencies (flask, psutil, yt-dlp)…"
"$PIP" install --upgrade -r "$SCRIPT_DIR/requirements.txt" -q
"$PIP" install --upgrade yt-dlp -q
info "Python packages up to date."

# ── Check ffmpeg ─────────────────────────────────────────────
if command -v ffmpeg &>/dev/null; then
  FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
  info "ffmpeg OK: $FFMPEG_VER"
else
  warn "ffmpeg NOT found in PATH!"
  warn "Video merging and format conversion will fail."
  warn "Run: ./install_deps.sh  (or: sudo dnf install ffmpeg)"
fi

# ── Check yt-dlp ─────────────────────────────────────────────
YTDLP_BIN="$VENV_DIR/bin/yt-dlp"
if [ -f "$YTDLP_BIN" ]; then
  info "yt-dlp OK: $($YTDLP_BIN --version 2>/dev/null || echo 'version check failed')"
else
  warn "yt-dlp binary not found at $YTDLP_BIN"
fi

echo ""
info "Starting Flask server on http://127.0.0.1:5000 …"
info "Browser will open automatically in ~2 seconds."
info "Press Ctrl+C to stop the server."
echo ""

# ── Launch Flask ─────────────────────────────────────────────
cd "$SCRIPT_DIR"
exec "$PYTHON" app.py
