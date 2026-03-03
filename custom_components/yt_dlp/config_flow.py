"""Config flow and Options flow for YT-DLP."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

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
    FORMAT_OPTIONS,
    SCAN_INTERVAL_OPTIONS,
)


def _user_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name", default=defaults.get("name", "YouTube Playlist")): str,
            vol.Required(
                CONF_PLAYLIST_URL, default=defaults.get(CONF_PLAYLIST_URL, "")
            ): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.In(SCAN_INTERVAL_OPTIONS),
            vol.Required(
                CONF_DOWNLOAD_PATH, default=defaults.get(CONF_DOWNLOAD_PATH, "")
            ): str,
            vol.Required(
                CONF_FORMAT, default=defaults.get(CONF_FORMAT, DEFAULT_FORMAT)
            ): vol.In(FORMAT_OPTIONS),
            vol.Optional(
                CONF_REPLACE_EXISTING,
                default=defaults.get(CONF_REPLACE_EXISTING, DEFAULT_REPLACE_EXISTING),
            ): bool,
            vol.Optional(
                CONF_AUTO_UPDATE,
                default=defaults.get(CONF_AUTO_UPDATE, DEFAULT_AUTO_UPDATE),
            ): bool,
        }
    )


def _options_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_PLAYLIST_URL, default=defaults.get(CONF_PLAYLIST_URL, "")
            ): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.In(SCAN_INTERVAL_OPTIONS),
            vol.Required(
                CONF_DOWNLOAD_PATH, default=defaults.get(CONF_DOWNLOAD_PATH, "")
            ): str,
            vol.Required(
                CONF_FORMAT, default=defaults.get(CONF_FORMAT, DEFAULT_FORMAT)
            ): vol.In(FORMAT_OPTIONS),
            vol.Optional(
                CONF_REPLACE_EXISTING,
                default=defaults.get(CONF_REPLACE_EXISTING, DEFAULT_REPLACE_EXISTING),
            ): bool,
            vol.Optional(
                CONF_AUTO_UPDATE,
                default=defaults.get(CONF_AUTO_UPDATE, DEFAULT_AUTO_UPDATE),
            ): bool,
        }
    )


class YtDlpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input.get(CONF_PLAYLIST_URL, "")
            path = user_input.get(CONF_DOWNLOAD_PATH, "")

            if not url.startswith(("http://", "https://")):
                errors[CONF_PLAYLIST_URL] = "invalid_url"
            elif not path:
                errors[CONF_DOWNLOAD_PATH] = "invalid_path"
            else:
                title = user_input.pop("name", "YouTube Playlist")
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> YtDlpOptionsFlow:
        return YtDlpOptionsFlow(config_entry)


class YtDlpOptionsFlow(config_entries.OptionsFlow):
    """Allow the user to reconfigure an existing entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self._config_entry.data, **self._config_entry.options}

        if user_input is not None:
            url = user_input.get(CONF_PLAYLIST_URL, "")
            if not url.startswith(("http://", "https://")):
                errors[CONF_PLAYLIST_URL] = "invalid_url"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(user_input or current),
            errors=errors,
        )
