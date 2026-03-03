"""Constants for the YT-DLP integration."""

DOMAIN = "yt_dlp"
PLATFORMS = ["sensor", "button"]

# Config / Options keys
CONF_PLAYLIST_URL = "playlist_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DOWNLOAD_PATH = "download_path"
CONF_FORMAT = "format"
CONF_REPLACE_EXISTING = "replace_existing"
CONF_AUTO_UPDATE = "auto_update"

# Format values
FORMAT_AUDIO = "audio"
FORMAT_VIDEO = "video"
FORMAT_OPTIONS = [FORMAT_AUDIO, FORMAT_VIDEO]

# Scan interval values (hours as strings for selector)
SCAN_INTERVAL_OPTIONS = ["12", "24", "48"]

# Defaults
DEFAULT_SCAN_INTERVAL = "24"
DEFAULT_FORMAT = FORMAT_AUDIO
DEFAULT_REPLACE_EXISTING = False
DEFAULT_AUTO_UPDATE = True

# Service names
SERVICE_DOWNLOAD_NOW = "download_now"
SERVICE_UPDATE_YTDLP = "update_ytdlp"

# Status values
STATUS_IDLE = "idle"
STATUS_DOWNLOADING = "downloading"
STATUS_UPDATING = "updating"
STATUS_ERROR = "error"
