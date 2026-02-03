# Stremio to M3U Playlist

Automatically converts a Stremio addon into an M3U playlist.

## Playlist Link

```
https://raw.githubusercontent.com/fnsc/stremio-m3u/main/playlist.m3u
```

> **Replace `YOUR_USER` and `YOUR_REPOSITORY` with your own data!**

## How it works

- The playlist is updated **automatically every 6 hours**
- You can also update it manually at: `Actions` → `Update M3U Playlist` → `Run workflow`

## Setup

### Change the source addon

1. Go to `Settings` → `Secrets and variables` → `Actions` → `Variables`
2. Create a variable called `ADDON_URL`
3. Enter the URL of your addon (e.g.: `https://example.baby-beamup.club/`)

Or edit directly in the `stremio_to_m3u.py` file:
```python
ADDON_URL = 'https://your-url-here/'
```

### Change update frequency

Edit the `.github/workflows/update-playlist.yml` file:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
```

Examples:
- `'0 */1 * * *'` = every 1 hour
- `'0 */12 * * *'` = every 12 hours
- `'0 0 * * *'` = once a day (midnight)

## How to use the playlist

Paste the link into any IPTV player:

- **VLC**: Media → Open Network Stream → Paste the link
- **Kodi**: Add M3U list in PVR IPTV Simple Client
- **TiviMate**: Add playlist → M3U Playlist → Paste the link
- **IPTV Smarters**: Add user → Load Playlist → M3U URL

## License

Personal use. Does not host any content, only converts public links.
