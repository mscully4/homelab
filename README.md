# homelab

Source of truth for what runs on this server. Not every service's compose
file lives in this repo — some already have their own git history elsewhere
and are linked rather than duplicated, to avoid two copies drifting apart.

## Docker Compose stacks

| Service | Compose file | Notes |
|---|---|---|
| Immich (photos) | [`immich-app/docker-compose.yml`](immich-app/docker-compose.yml) | server + postgres + redis. Photo/DB storage lives outside this repo at `/mnt/immich` |
| Home Assistant | [`home-assistant/docker-compose.yml`](home-assistant/docker-compose.yml) | + mosquitto, ring-mqtt. Only hand-authored YAML under `config/` is tracked — runtime state, db, logs, and deps are gitignored |
| Docker registry | [`registry/docker-compose.yml`](registry/docker-compose.yml) | new — wasn't tracked before |
| Cloak browser | [`cloakbrowser/docker-compose.yml`](cloakbrowser/docker-compose.yml) | new — wasn't tracked before. Headless browser bound to localhost:9222 |

`immich-app/` and `home-assistant/` were moved into this repo from `~/immich-app`
and `~/home-assistant` on 2026-07-11. Both use relative bind-mount paths
(`.env`, `./config`, etc.) that resolve based on the compose file's own
location, so they had to be stopped (`docker compose down`), moved, then
started again from here (`docker compose up -d`) — a plain `mv` alone would
leave running containers pointed at the old, now-gone paths.

`~/docker-vpn-sidecar` ([GitHub](https://github.com/mscully4/docker-vpn-sidecar)) is the
original standalone VPN sidecar repo. Its `vpn` service definition was later
copied into poly-ball's compose file, where it actually runs today. The
standalone repo itself isn't deployed from — kept for reference/reuse.

## Native services (not Docker)

- **Plex Media Server** — installed via apt, managed by systemd
  (`plexmediaserver.service`). No compose equivalent; config lives under
  `/var/lib/plexmediaserver`.

## Secrets

Each stack's `.env` file holds real credentials and is gitignored — see
`.env.example` in the respective directory (where one exists) for the
expected keys. Never commit `.env` itself.

## Cleanup log

- 2026-07-11: removed PiGallery2 (container, image, `pigallery2_db-data` +
  stray `pigallery_db-data` volumes, config dir). Photo library at
  `/xplct/images` was untouched (read-only mount).
- 2026-07-11: removed Nextcloud AIO mastercontainer (was never fully set up —
  no sub-containers, 5.7KB config volume).
- 2026-07-11: removed `duke-bot` systemd service (Telegram bot, source left
  at `~/duke`).
- 2026-07-11: stopped `arb-scanner` / `copy-trader` (poly-ball) — disabled,
  not deleted (superseded by full removal below same day).
- 2026-07-11: removed poly-ball entirely (no longer used) — all 5 containers,
  images, and named volumes (`grafana_data`, `prometheus_data`) deleted.
  Code remains on [GitHub](https://github.com/mscully4/poly-ball); the
  gitignored `data/` directory (price history, accounts, state — 2.9GB) was
  not in source control, so it was archived to `~/archive/poly-ball-data`
  instead of deleted. `~/docker-vpn-sidecar` ([GitHub](https://github.com/mscully4/docker-vpn-sidecar))
  is now fully unused too but was left as-is (not asked to remove it).
