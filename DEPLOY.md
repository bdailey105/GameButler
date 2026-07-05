# Deployment Guide (Home Network)

## Prerequisites

- Always-on host on your LAN with Docker + Docker Compose installed. Git installed.

## Deploy

1. Clone repo to the host:
   ```bash
   git clone https://github.com/bdaileySNHU/GameButler.git
   cd GameButler
   ```

2. Start the containers:
   ```bash
   docker compose up -d --build
   ```

3. Access at `http://<host-ip>:8095` from any device on the LAN.

**Note:** Nginx inside the frontend container proxies `/api` to the backend, so port 8095 is the only port you need to expose.

## Updating

Pull the latest code and rebuild:

```bash
git pull && docker compose up -d --build
```

Library data survives rebuilds — it lives in the SQLite file under `./data/`, which is volume-mounted.

## Backup

The entire library is one file: `./data/gamebutler.db`. Copy it anywhere (use `cron` + `rsync` if desired for automated backups). Restore by copying it back and restarting the containers:

```bash
docker compose restart
```

## Optional Niceties

- Give the host a DHCP reservation or static IP so the URL never changes.
- Install Tailscale on the host for access away from home. This avoids port-forwarding and keeps the app off the public internet.

## Troubleshooting

- **Port conflict on 8095:** Change the host side of `ports:` in `docker-compose.yml`.
- **Check logs:** `docker compose logs -f backend` or `docker compose logs -f frontend`.
