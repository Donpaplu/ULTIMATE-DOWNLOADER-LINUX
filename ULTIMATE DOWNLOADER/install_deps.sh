#!/usr/bin/env bash
# ============================================================
# install_deps.sh — Install ALL system dependencies
# Run ONCE before first launch. Requires sudo.
# Compatible with: Fedora 38/39/40/41 (KDE or any spin)
# ============================================================

set -eu

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 1. Check we're on a dnf-based system ─────────────────────
command -v dnf &>/dev/null || error "dnf not found. This script is for Fedora/RPM systems."

info "Updating package list…"
sudo dnf check-update -q || true   # returns 100 if updates available — not an error

# ── 2. Install Python 3 ───────────────────────────────────────
info "Installing Python 3…"
sudo dnf install -y python3 python3-pip

# ── 3. Enable RPM Fusion (needed for ffmpeg) ──────────────────
info "Enabling RPM Fusion Free & Non-Free repositories…"
FEDORA_VER=$(rpm -E %fedora)

# Free repo
sudo dnf install -y \
  "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-${FEDORA_VER}.noarch.rpm" \
  || warn "RPM Fusion Free may already be enabled — continuing."

# Non-Free repo (needed for ffmpeg on newer Fedora)
sudo dnf install -y \
  "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-${FEDORA_VER}.noarch.rpm" \
  || warn "RPM Fusion Non-Free may already be enabled — continuing."

# ── 4. Install ffmpeg ─────────────────────────────────────────
info "Installing ffmpeg (required for video/audio merging)…"
# On Fedora 41+ with rpmfusion, ffmpeg-free is in base repos.
# We try ffmpeg first, fall back to ffmpeg-free.
sudo dnf install -y ffmpeg 2>/dev/null || sudo dnf install -y ffmpeg-free || \
  warn "Could not install ffmpeg automatically. Install manually: sudo dnf install ffmpeg"

# ── 5. Install AtomicParsley (thumbnail embedding for audio) ──
info "Installing AtomicParsley (thumbnail embedding for MP3/M4A)…"
sudo dnf install -y atomicparsley || warn "AtomicParsley not available — audio thumbnails may not embed."

# ── 6. Verify ffmpeg ──────────────────────────────────────────
if command -v ffmpeg &>/dev/null; then
  info "ffmpeg OK: $(ffmpeg -version 2>&1 | head -1)"
else
  warn "ffmpeg not found in PATH. Video merging and format conversion will fail."
fi

# ── 7. Python venv + packages (delegated to start.sh) ────────
info "System dependencies installed."
echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  All done! Now run:  ./start.sh${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
