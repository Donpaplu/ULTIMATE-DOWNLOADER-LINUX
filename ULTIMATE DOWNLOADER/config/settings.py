# ============================================================
# config/settings.py  — Edit paths here to make them permanent
# ============================================================

import os

# Default cookie file for YouTube authentication
COOKIES         = "/run/media/Papludon/Deepanshu/tools/ULTIMATE DOWNLAODER/cookies.txt"

# Output directories
OUTDIR          = "/run/media/Papludon/sda2/videos"
PL_OUTDIR       = "/run/media/Papludon/sda2/videos/Playlists"
MUSIC_OUTDIR    = "/run/media/Papludon/sda2/videos/Music"
MUSIC_PL_OUTDIR = "/run/media/Papludon/sda2/videos/Music/Playlists"

# yt-dlp executable — on Linux, use the venv binary or system PATH
# The startup script installs yt-dlp into the venv, so this path works:
YTDLP_BIN       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "bin", "yt-dlp")

# Fallback: if the venv binary doesn't exist, try system PATH
import shutil
if not os.path.exists(YTDLP_BIN):
    system_ytdlp = shutil.which("yt-dlp")
    YTDLP_BIN = system_ytdlp if system_ytdlp else "yt-dlp"

# Language code → human readable name mapping for format picker
LANG_MAP = {
    "en":  "English",  "hi":  "Hindi",   "fr":  "French",   "de":  "German",
    "es":  "Spanish",  "ja":  "Japanese","ko":  "Korean",   "zh":  "Chinese",
    "ru":  "Russian",  "ar":  "Arabic",  "pt":  "Portuguese","it": "Italian",
    "tr":  "Turkish",  "bn":  "Bengali", "pa":  "Punjabi",  "te":  "Telugu",
    "ta":  "Tamil",    "mr":  "Marathi", "gu":  "Gujarati", "kn":  "Kannada",
    "ml":  "Malayalam","ur":  "Urdu",    "ne":  "Nepali",   "si":  "Sinhala",
    "th":  "Thai",     "vi":  "Vietnamese","id": "Indonesian","ms": "Malay",
    "nl":  "Dutch",    "pl":  "Polish",  "sv":  "Swedish",  "no":  "Norwegian",
    "da":  "Danish",   "fi":  "Finnish", "cs":  "Czech",    "ro":  "Romanian",
    "hu":  "Hungarian","uk":  "Ukrainian","el": "Greek",    "he":  "Hebrew",
    "orig":"Original", "default":"Default",
}
