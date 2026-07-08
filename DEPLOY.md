# Deployment Guide (Local/Home Network)

## Prerequisites

- Local machine or always-on LAN host.
- Git.
- Docker with Docker Compose.
- Python 3 and Node.js/npm for local verification commands.

## Local Setup

Install backend and frontend dependencies:

```bash
make setup
```

Run the local verification suite before deploying:

```bash
make verify
```

This runs backend tests, frontend lint, frontend production build, and Docker Compose config validation.

## Deploy

1. Clone repo to the host:
   ```bash
   git clone https://github.com/bdaileySNHU/GameButler.git
   cd GameButler
   ```

2. Start the containers:
   ```bash
   make up
   ```

3. Access at `http://<host-ip>:8095` from any device on the LAN.

**Note:** Nginx inside the frontend container proxies `/api` to the backend, so port 8095 is the only port you need to expose.

## Steam Sync (optional)

To enable one-click library sync, set two environment variables for the backend container:

- **STEAM_API_KEY** — Get one at https://steamcommunity.com/dev/apikey
- **STEAM_ID** — Your 64-bit SteamID, findable at https://steamid.io

Pass them when starting the containers:

```bash
STEAM_API_KEY=XXXXXXXX STEAM_ID=7656119XXXXXXXXXX docker compose up -d --build
```

Or save them in a `.env` file next to `compose.yaml`:

```
STEAM_API_KEY=XXXXXXXX
STEAM_ID=7656119XXXXXXXXXX
```

Then run `docker compose up -d --build`.

**Note:** Your Steam profile's "Game details" must be public for the API to return your library. Without these vars the Sync Steam button returns a friendly "not configured" error; CSV upload keeps working regardless.

### Auto-Sync

When the Steam vars are set, the backend syncs automatically: once at startup, then every `SYNC_INTERVAL_HOURS` (default 24). Override the interval or disable it in the same `.env` file:

```
SYNC_INTERVAL_HOURS=12   # sync twice a day
SYNC_INTERVAL_HOURS=0    # disable auto-sync (manual button still works)
```

Auto-sync keeps the activity feed's playtime history accurate without needing to click Sync Steam.

## Non-Steam Games (optional)

Games added manually (Switch, PlayStation, etc.) can get art and genres automatically via [RAWG](https://rawg.io/apidocs) — grab a free API key and add it to the same `.env` file:

```
RAWG_API_KEY=XXXXXXXX
```

Without the key, manual games still work — they just use placeholder cards until you add art another way.

## Health Check

After the containers start, verify the local deployment:

```bash
make health
```

The health check verifies:

- Docker Compose has `backend` and `frontend` services running.
- The frontend responds at `http://localhost:8095`.
- The API responds through the frontend proxy at `http://localhost:8095/api/health`.
- The SQLite database file exists at `data/gamebutler.db`.

Override defaults when checking a remote LAN host:

```bash
FRONTEND_URL=http://<host-ip>:8095 make health
```

## Updating

Pull the latest code and rebuild:

```bash
git pull && make up && make health
```

Library data survives rebuilds — it lives in the SQLite file under `./data/`, which is volume-mounted.

## Backup & Restore

The entire library is one file: `./data/gamebutler.db`.

Create a timestamped backup under `./backups/`:

```bash
make backup
```

Restore from a backup:

```bash
make down
make restore BACKUP=backups/gamebutler-YYYYMMDD-HHMMSS.db
make up
make restart && make health
```

`make restore` saves the current DB to `backups/pre-restore-YYYYMMDD-HHMMSS.db` before replacing it.

For automated backups, run `make backup` from cron or copy `./data/gamebutler.db` with `rsync`.

After manually copying a DB file into place, restart the containers:

```bash
make restart
```

## Optional Niceties

- Give the host a DHCP reservation or static IP so the URL never changes.
- Install Tailscale on the host for access away from home. This avoids port-forwarding and keeps the app off the public internet.

## Troubleshooting

- **Port conflict on 8095:** Change the host side of `ports:` in `docker-compose.yml`.
- **Check logs:** `make logs`, or `docker compose logs -f backend` / `docker compose logs -f frontend`.
- **Validate Compose config:** `make compose-config`.
