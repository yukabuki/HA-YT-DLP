"""Button entity for YT-DLP (manual download trigger)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YtDlpCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: YtDlpCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([YtDlpDownloadButton(coordinator, entry)])


class YtDlpDownloadButton(CoordinatorEntity[YtDlpCoordinator], ButtonEntity):
    """Press to start an immediate playlist download."""

    _attr_icon = "mdi:download"
    _attr_has_entity_name = True
    _attr_name = "Download Now"

    def __init__(self, coordinator: YtDlpCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_download_now"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="yukabuki",
            model="YT-DLP Downloader",
            configuration_url="https://github.com/yukabuki/ha-yt-dlp",
        )

    async def async_press(self) -> None:
        """Trigger an immediate download."""
        await self.coordinator.async_download_now()
