# torrents

VPN-tunneled qBittorrent stack. `gluetun` holds the ProtonVPN WireGuard tunnel;
`qbittorrent` runs with `network_mode: service:gluetun` so it has no network
path outside the tunnel (killswitch: stopping gluetun cuts qBittorrent's
connectivity immediately).

## First-time setup

1. Copy `.env.example` to `.env` and fill in `WIREGUARD_PRIVATE_KEY` (see
   comments in `.env.example` for where to get it) and confirm
   `DOWNLOADS_LOCATION` points at a real path.
2. Create the download folder structure on the host, owned by the `PUID`/`PGID`
   set in `.env`:

   ```bash
   sudo mkdir -p $DOWNLOADS_LOCATION/incomplete \
                $DOWNLOADS_LOCATION/complete/{books,video,audio,unsorted}
   sudo chown -R <PUID>:<PGID> $DOWNLOADS_LOCATION
   ```

3. `docker compose up -d`
4. In the qBittorrent WebUI (`http://<host>:8080`), under
   **Settings → Downloads**, set:
   - "Keep incomplete torrents in": `/downloads/incomplete`
   - Default save path: `/downloads/complete/unsorted`
   Then create a **category** per content type (`books`, `video`, `audio`),
   each with its save path set to `/downloads/complete/<category>` — the
   orchestrator passes `category` on `add_torrent` so files land in the right
   subfolder automatically.

## Filing

A completion hook (polling `get_completed()` or qBittorrent's "run on
completion" script) moves files out of `complete/<category>/` into the real
destination (Calibre watch folder, Plex media folders, podcast folder) —
via qBittorrent's own move/location API rather than an out-of-band `mv`, so
seeding isn't broken for the torrents you're keeping up.
