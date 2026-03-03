"""DataUpdateCoordinator for YT-DLP playlist downloads."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.persistent_notification import async_create as pn_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_AUTO_UPDATE,
    CONF_DOWNLOAD_PATH,
    CONF_FORMAT,
    CONF_PLAYLIST_URL,
    CONF_REPLACE_EXISTING,
    CONF_SCAN_INTERVAL,
    DEFAULT_AUTO_UPDATE,
    DEFAULT_FORMAT,
    DEFAULT_REPLACE_EXISTING,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FORMAT_AUDIO,
    STATUS_DOWNLOADING,
    STATUS_ERROR,
    STATUS_IDLE,
    STATUS_UPDATING,
)

_LOGGER = logging.getLogger(__name__)


class _YtDlpLogger:
    """Redirects yt-dlp internal messages to the HA logger.

    Without this, yt-dlp writes directly to stdout/stderr when quiet=False,
    or produces no output at all when quiet=True.  This class routes every
    yt-dlp log line through the standard HA logging system so they appear in
    Settings → System → Logs and in home-assistant.log.
    """

    def __init__(self, video_errors: list[str]) -> None:
        self._video_errors = video_errors

    def debug(self, msg: str) -> None:
        _LOGGER.debug("[yt-dlp] %s", msg)

    def info(self, msg: str) -> None:
        # yt-dlp marks download progress lines as info — keep them at debug
        # level to avoid flooding the log.
        if msg.startswith("[download]"):
            _LOGGER.debug("[yt-dlp] %s", msg)
        else:
            _LOGGER.info("[yt-dlp] %s", msg)

    def warning(self, msg: str) -> None:
        _LOGGER.warning("[yt-dlp] %s", msg)

    def error(self, msg: str) -> None:
        _LOGGER.error("[yt-dlp] %s", msg)
        self._video_errors.append(msg)


def _get_option(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Read from entry.options first, fall back to entry.data."""
    return entry.options.get(key, entry.data.get(key, default))


class YtDlpCoordinator(DataUpdateCoordinator):
    """Manages scheduled and on-demand yt-dlp playlist downloads."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._status: str = STATUS_IDLE
        self._last_run: datetime | None = None
        self._files_downloaded: int = 0
        self._error: str | None = None
        self._video_errors: list[str] = []
        self._is_downloading: bool = False
        # Avoid a download on the very first coordinator refresh (startup).
        self._first_refresh_done: bool = False

        hours = int(_get_option(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(hours=hours),
        )

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    @property
    def playlist_url(self) -> str:
        return _get_option(self.entry, CONF_PLAYLIST_URL, "")

    @property
    def download_path(self) -> str:
        return _get_option(self.entry, CONF_DOWNLOAD_PATH, "")

    @property
    def format(self) -> str:
        return _get_option(self.entry, CONF_FORMAT, DEFAULT_FORMAT)

    @property
    def replace_existing(self) -> bool:
        return _get_option(self.entry, CONF_REPLACE_EXISTING, DEFAULT_REPLACE_EXISTING)

    @property
    def auto_update(self) -> bool:
        return _get_option(self.entry, CONF_AUTO_UPDATE, DEFAULT_AUTO_UPDATE)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        return self._status

    @property
    def last_run(self) -> datetime | None:
        return self._last_run

    @property
    def files_downloaded(self) -> int:
        return self._files_downloaded

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def video_errors(self) -> list[str]:
        return self._video_errors

    def _build_state(self) -> dict[str, Any]:
        return {
            "status": self._status,
            "last_run": self._last_run,
            "files_downloaded": self._files_downloaded,
            "error": self._error,
            "video_errors": list(self._video_errors),
        }

    # ------------------------------------------------------------------
    # DataUpdateCoordinator
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Called by the internal timer.

        The very first call (on HA startup) only returns initial state so the
        entry setup completes immediately.  Every subsequent call runs the
        actual download.
        """
        if not self._first_refresh_done:
            self._first_refresh_done = True
            _LOGGER.debug("YT-DLP coordinator initialised for '%s'", self.entry.title)
            return self._build_state()

        if self._is_downloading:
            _LOGGER.debug(
                "Download already in progress for '%s', skipping scheduled run",
                self.entry.title,
            )
            return self.data or self._build_state()

        # Set status NOW (async context) and push it to entities immediately,
        # before the executor thread starts.  Without this the sensor would
        # stay on "idle" for the entire duration of the download.
        self._is_downloading = True
        self._status = STATUS_DOWNLOADING
        self._error = None
        self._video_errors = []
        self.async_update_listeners()

        result = await self.hass.async_add_executor_job(self._run_download)
        await self._async_maybe_notify(result)
        return result

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def async_download_now(self) -> None:
        """Manually trigger a download and push the result to listeners."""
        if self._is_downloading:
            _LOGGER.warning(
                "Download already in progress for '%s'", self.entry.title
            )
            return

        # Same as above: set downloading state before entering the executor
        # so the sensor reflects it immediately.
        self._is_downloading = True
        self._status = STATUS_DOWNLOADING
        self._error = None
        self._video_errors = []
        self.async_update_listeners()

        result = await self.hass.async_add_executor_job(self._run_download)
        self.async_set_updated_data(result)
        await self._async_maybe_notify(result)

    async def async_update_ytdlp(self) -> bool:
        """Update yt-dlp to the latest version and return True on success."""
        return await self.hass.async_add_executor_job(self._run_pip_update_standalone)

    async def _async_maybe_notify(self, result: dict[str, Any]) -> None:
        """Create a persistent HA notification when a download has errors."""
        notif_id = f"{DOMAIN}_{self.entry.entry_id}_error"
        fatal_error: str | None = result.get("error")
        video_errors: list[str] = result.get("video_errors", [])

        if fatal_error:
            pn_create(
                self.hass,
                title=f"YT-DLP — Erreur : {self.entry.title}",
                message=(
                    f"Une erreur fatale s'est produite lors du téléchargement.\n\n"
                    f"**Erreur :** {fatal_error}\n\n"
                    f"**Playlist :** {self.playlist_url}\n\n"
                    f"Vérifiez les logs (`Paramètres → Système → Journaux`) "
                    f"pour plus de détails."
                ),
                notification_id=notif_id,
            )
        elif video_errors:
            errors_text = "\n".join(f"- {e}" for e in video_errors[:10])
            suffix = f"\n- … et {len(video_errors) - 10} autres" if len(video_errors) > 10 else ""
            pn_create(
                self.hass,
                title=f"YT-DLP — Avertissements : {self.entry.title}",
                message=(
                    f"{result.get('files_downloaded', 0)} fichier(s) téléchargé(s), "
                    f"mais {len(video_errors)} vidéo(s) ont rencontré une erreur :\n\n"
                    f"{errors_text}{suffix}\n\n"
                    f"**Playlist :** {self.playlist_url}"
                ),
                notification_id=notif_id,
            )

    # ------------------------------------------------------------------
    # Blocking helpers (executor thread)
    # ------------------------------------------------------------------

    def _do_pip_update(self) -> bool:
        """Run pip install -U yt-dlp and clear module cache on success.

        Does NOT touch self._status — caller manages status.
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "--quiet"],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            # Clear cached yt-dlp modules so the next import loads the fresh version.
            for key in list(sys.modules.keys()):
                if key == "yt_dlp" or key.startswith("yt_dlp."):
                    del sys.modules[key]
            _LOGGER.info("yt-dlp pip update complete. stdout=%s", result.stdout.strip())
            return True
        except subprocess.CalledProcessError as exc:
            _LOGGER.error("yt-dlp pip update failed: %s", exc.stderr)
            return False
        except subprocess.TimeoutExpired:
            _LOGGER.error("yt-dlp pip update timed out after 120 s")
            return False

    def _run_pip_update_standalone(self) -> bool:
        """Update yt-dlp with proper status transitions (for service call)."""
        self._status = STATUS_UPDATING
        success = self._do_pip_update()
        self._status = STATUS_IDLE
        return success

    def _run_download(self) -> dict[str, Any]:
        """Execute the yt-dlp playlist download. Runs inside an executor thread."""
        # Import here so a freshly pip-installed version is picked up after
        # module cache was cleared by _do_pip_update().
        try:
            import yt_dlp  # noqa: PLC0415
        except ImportError as exc:
            self._status = STATUS_ERROR
            self._error = "yt-dlp is not installed"
            self._last_run = datetime.now()
            _LOGGER.error("yt-dlp not found: %s", exc)
            return self._build_state()

        # Note: _is_downloading, _status, _error, _video_errors are already
        # set by the calling async method before entering the executor.

        # Optional auto-update before download (no status change here).
        if self.auto_update:
            _LOGGER.debug("Auto-updating yt-dlp before download run")
            self._do_pip_update()
            # Re-import after potential cache clear
            try:
                import yt_dlp  # noqa: PLC0415, F811
            except ImportError:
                pass

        # Ensure destination directory exists.
        try:
            os.makedirs(self.download_path, exist_ok=True)
        except OSError as exc:
            self._is_downloading = False
            self._status = STATUS_ERROR
            self._error = f"Cannot create download path: {exc}"
            self._last_run = datetime.now()
            _LOGGER.error("Cannot create path '%s': %s", self.download_path, exc)
            return self._build_state()

        downloaded_files: list[str] = []
        ytdlp_logger = _YtDlpLogger(self._video_errors)

        def _progress_hook(d: dict) -> None:
            if d.get("status") == "finished":
                filename = d.get("filename", "")
                downloaded_files.append(filename)
                _LOGGER.info("[yt-dlp] Fichier téléchargé : %s", filename)

        outtmpl = os.path.join(
            self.download_path,
            "%(playlist_title)s",
            "%(title)s.%(ext)s",
        )

        ydl_opts: dict[str, Any] = {
            "outtmpl": outtmpl,
            "nooverwrites": not self.replace_existing,
            "ignoreerrors": True,
            # Route all yt-dlp output through the HA logger instead of stdout.
            "logger": ytdlp_logger,
            "progress_hooks": [_progress_hook],
        }

        if self.format == FORMAT_AUDIO:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        else:
            ydl_opts["format"] = "bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mkv"

        _LOGGER.info(
            "Starting download: playlist=%s  path=%s  format=%s",
            self.playlist_url,
            self.download_path,
            self.format,
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.playlist_url])

            self._files_downloaded = len(downloaded_files)
            self._last_run = datetime.now()
            self._status = STATUS_IDLE
            self._is_downloading = False
            _LOGGER.info(
                "Download finished for '%s': %d file(s)",
                self.entry.title,
                self._files_downloaded,
            )
        except Exception as exc:  # noqa: BLE001
            self._status = STATUS_ERROR
            self._error = str(exc)
            self._last_run = datetime.now()
            self._is_downloading = False
            _LOGGER.error(
                "Download error for '%s': %s", self.entry.title, exc
            )

        return self._build_state()
