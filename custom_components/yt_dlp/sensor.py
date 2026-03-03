"""Sensor entity for YT-DLP."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
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
    async_add_entities([YtDlpStatusSensor(coordinator, entry)])


class YtDlpStatusSensor(CoordinatorEntity[YtDlpCoordinator], SensorEntity):
    """Reports the current download status and metadata for a playlist entry."""

    _attr_icon = "mdi:youtube"
    _attr_has_entity_name = True
    _attr_name = "Status"

    def __init__(self, coordinator: YtDlpCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_status"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="yukabuki",
            model="YT-DLP Downloader",
            configuration_url="https://github.com/yukabuki/ha-yt-dlp",
        )

    @property
    def native_value(self) -> str:
        return self.coordinator.status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "playlist_url": self.coordinator.playlist_url,
            "format": self.coordinator.format,
            "download_path": self.coordinator.download_path,
            "replace_existing": self.coordinator.replace_existing,
            "auto_update": self.coordinator.auto_update,
            "files_downloaded_last_run": self.coordinator.files_downloaded,
        }

        if self.coordinator.last_run:
            attrs["last_run"] = self.coordinator.last_run.isoformat()

            if self.coordinator.update_interval:
                next_run = self.coordinator.last_run + self.coordinator.update_interval
                attrs["next_run"] = next_run.isoformat()

        if self.coordinator.error:
            attrs["last_error"] = self.coordinator.error

        return attrs
