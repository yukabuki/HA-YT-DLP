# ha-yt-dlp

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/yukabuki/ha-yt-dlp)](https://github.com/yukabuki/ha-yt-dlp/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Home Assistant custom integration that uses **yt-dlp** to automatically download YouTube playlists on a schedule.

---

## Features

- Download any **public YouTube playlist** automatically every **12 / 24 / 48 hours**
- Choose format: **audio only (MP3)** or **video + audio (MKV)**
- Configure the **save path** freely (works great with media server volumes)
- Option to **replace** or **skip** already-downloaded files (default: skip)
- **Auto-updates yt-dlp** via pip before each download run (keeps up with YouTube changes)
- **Manual trigger** via button entity or Developer Tools action
- **Update yt-dlp** on-demand via a dedicated action
- Full support for **HACS**

---

## Requirements

| Dependency | Notes |
|---|---|
| Home Assistant ≥ 2024.1 | |
| [HACS](https://hacs.xyz) | For easy installation |
| **FFmpeg** | Required for audio extraction (MP3 format). Must be accessible in `PATH` inside the HA container. Most HA OS / Supervised installs already include it. |
| Internet access | HA needs to reach YouTube and PyPI (for yt-dlp updates). |

> **Docker / HA OS users:** make sure your download path is a volume that is mounted inside the container, e.g. `/media` or `/config/downloads`.

---

## Installation via HACS

1. In Home Assistant, open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/yukabuki/ha-yt-dlp` with category **Integration**.
3. Search for **YT-DLP Downloader** and click **Download**.
4. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **YT-DLP Downloader**.
3. Fill in the form:

| Field | Description |
|---|---|
| **Name** | Friendly name for this playlist (e.g. "Lo-fi Music") |
| **YouTube Playlist URL** | Full URL, e.g. `https://www.youtube.com/playlist?list=PLxxx` |
| **Download interval** | `12`, `24` or `48` hours |
| **Download path** | Absolute path inside HA, e.g. `/media/youtube/lofi` |
| **Format** | `audio` (MP3 192 kbps) or `video` (MKV best quality) |
| **Replace existing files** | `false` (default) skips already-downloaded files |
| **Auto-update yt-dlp** | `true` (default) — recommended |

You can add multiple integrations for different playlists.

---

## Entities

Each configured playlist creates a **device** with two entities:

| Entity | Type | Description |
|---|---|---|
| `sensor.<name>_status` | Sensor | Current state: `idle` / `downloading` / `updating` / `error` |
| `button.<name>_download_now` | Button | Press to start an immediate download |

### Sensor attributes

| Attribute | Description |
|---|---|
| `playlist_url` | Configured playlist URL |
| `format` | `audio` or `video` |
| `download_path` | Save location |
| `replace_existing` | Whether files are replaced |
| `auto_update` | Whether yt-dlp auto-updates |
| `files_downloaded_last_run` | Number of files downloaded in the last run |
| `last_run` | ISO timestamp of the last completed run |
| `next_run` | ISO timestamp of the next scheduled run |
| `last_error` | Error message from the last failed run (if any) |

---

## Actions (Developer Tools)

Navigate to **Developer Tools → Actions** to test the integration.

### `yt_dlp.download_now`

Trigger an immediate download.

```yaml
action: yt_dlp.download_now
data:
  config_entry_id: ""   # leave empty to download ALL playlists
```

### `yt_dlp.update_ytdlp`

Update yt-dlp to the latest version via pip.

```yaml
action: yt_dlp.update_ytdlp
```

---

## Automations example

```yaml
# Download every day at 3 AM
automation:
  - alias: "YT-DLP nightly download"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - action: yt_dlp.download_now
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Downloads fail with "sign in" errors | The playlist must be **public** and not age-restricted |
| Audio extraction fails | Ensure **FFmpeg** is installed and accessible in `PATH` |
| Files saved to wrong place | Use an **absolute path** that is mounted in the HA container |
| yt-dlp errors after YouTube changes | Run the `yt_dlp.update_ytdlp` action or enable auto-update |
| `yt-dlp not installed` error | Restart HA to allow it to install the pip requirement |

Enable debug logging for detailed output:

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.yt_dlp: debug
```

---

## Contributing

Pull requests and issues are welcome at [github.com/yukabuki/ha-yt-dlp](https://github.com/yukabuki/ha-yt-dlp).

---

## License

[MIT](LICENSE)
