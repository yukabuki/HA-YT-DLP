"""YT-DLP Home Assistant Integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, PLATFORMS, SERVICE_DOWNLOAD_NOW, SERVICE_UPDATE_YTDLP
from .coordinator import YtDlpCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_DOWNLOAD_NOW_SCHEMA = vol.Schema(
    {vol.Optional("config_entry_id"): cv.string}
)
SERVICE_UPDATE_YTDLP_SCHEMA = vol.Schema({})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up YT-DLP from a config entry."""
    coordinator = YtDlpCoordinator(hass, entry)

    # First refresh initialises state without triggering a download.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload coordinator when options are saved.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register domain services once (guard against multiple entries).
    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # Remove services when no entries remain.
    if not hass.data.get(DOMAIN):
        for svc in (SERVICE_DOWNLOAD_NOW, SERVICE_UPDATE_YTDLP):
            if hass.services.has_service(DOMAIN, svc):
                hass.services.async_remove(DOMAIN, svc)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change so the new interval is applied."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration-level services (idempotent)."""

    if not hass.services.has_service(DOMAIN, SERVICE_DOWNLOAD_NOW):

        async def _handle_download_now(call: ServiceCall) -> None:
            entry_id: str | None = call.data.get("config_entry_id")
            coordinators: list[YtDlpCoordinator] = list(
                hass.data.get(DOMAIN, {}).values()
            )
            if entry_id:
                coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
                if coordinator is None:
                    _LOGGER.error(
                        "download_now: config_entry_id '%s' not found", entry_id
                    )
                    return
                await coordinator.async_download_now()
            else:
                for coordinator in coordinators:
                    await coordinator.async_download_now()

        hass.services.async_register(
            DOMAIN,
            SERVICE_DOWNLOAD_NOW,
            _handle_download_now,
            schema=SERVICE_DOWNLOAD_NOW_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_YTDLP):

        async def _handle_update_ytdlp(call: ServiceCall) -> None:
            coordinator = next(
                iter(hass.data.get(DOMAIN, {}).values()), None
            )
            if coordinator is None:
                _LOGGER.error("update_ytdlp: no active YT-DLP entry found")
                return
            success = await coordinator.async_update_ytdlp()
            if success:
                _LOGGER.info("yt-dlp updated successfully")
            else:
                _LOGGER.error("yt-dlp update failed — check logs")

        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_YTDLP,
            _handle_update_ytdlp,
            schema=SERVICE_UPDATE_YTDLP_SCHEMA,
        )
