# The Local — DM-019/WORKS

Matrix-based communication network for the workplace democracy movement.

**Domain:** `thelocal.chat`
**Stack:** Synapse + PostgreSQL + Element Web + LiveKit + Caddy
**Repo:** `design-machines-studio/the-local`

---

## Architecture

```
thelocal.chat (Caddy — automatic TLS)
├── thelocal.chat            → Element Web + .well-known discovery
├── matrix.thelocal.chat     → Synapse API (port 8008)
│   ├── /livekit/jwt/*       → JWT auth service (port 8080)
│   └── /livekit/sfu/*       → LiveKit SFU WebSocket (port 7880)

Direct (not proxied):
    7881/tcp                 → LiveKit TCP fallback
    50100-50200/udp          → LiveKit WebRTC media streams

Internal:
    Synapse → PostgreSQL (Docker network)
```

---

## Prerequisites

### 1. Register the domain

Register `thelocal.chat` on Hover.

### 2. Create a DO droplet

- **Image:** Ubuntu 24.04 LTS
- **Plan:** $12/mo (1 vCPU, 2GB RAM)
- **Region:** Toronto (closest to Chris/Brian/TACO)
- **Auth:** Add your SSH key
- **Hostname:** `thelocal`

### 3. Set DNS records on Hover

| Type | Host | Value |
|------|------|-------|
| A | @ | `DROPLET_IP` |
| A | matrix | `DROPLET_IP` |

---

## Deploy

```bash
ssh root@DROPLET_IP

# Install Docker + Compose
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker
apt-get update -qq && apt-get install -y -qq docker-compose-plugin git

# Clone and setup
git clone git@github.com:design-machines-studio/the-local.git /opt/thelocal
cd /opt/thelocal
chmod +x setup.sh
./setup.sh
```

The script generates secrets, templates configs, opens firewall ports, and starts all 6 services.

### Create your admin account

```bash
docker compose exec synapse register_new_matrix_user \
  -u trav -p YOUR_SECURE_PASSWORD -a \
  -c /data/homeserver.yaml \
  http://localhost:8008
```

Log in at `https://thelocal.chat`.

---

## Phase 1: DM workspace

**Create a Space:** "The Local Design Machines" (private, invite-only)

**Create rooms:**
- `#general` — day-to-day
- `#watercooler` — off-topic
- `#assembly` — Assembly development

**Create accounts:**

```bash
# Chris Galloway
docker compose exec synapse register_new_matrix_user \
  -u chris -p THEIR_PASSWORD --no-admin \
  -c /data/homeserver.yaml http://localhost:8008

# Brian Richards (TACO)
docker compose exec synapse register_new_matrix_user \
  -u brian -p THEIR_PASSWORD --no-admin \
  -c /data/homeserver.yaml http://localhost:8008
```

Share `https://thelocal.chat` + credentials. They can change passwords after first login.

**Video calls:** Start a call from any room using the phone/video icon. 1:1 and group calls are handled by Element Call via the self-hosted LiveKit SFU. No external service needed.

**Mobile apps:** Chris and Brian can install Element X (iOS/Android), set the homeserver to `thelocal.chat`, and log in with their credentials. Push notifications work out of the box.

---

## Phase 1.5: TACO workspace

Same server, new Space.

**Create Space:** "The Local TACO" (private)

**Rooms:** `#general`, `#governance`, `#projects`

**Shared room (optional):** `#dm-taco` between DM and TACO for pilot work.

Create accounts for other TACO members as needed.

---

## Phase 2: Solid State and beyond

1. Create "The Commons" Space (public to all server members)
2. Cross-co-op rooms: `#introductions`, `#resources`, `#news`
3. Private Spaces per co-op
4. Enable federation when ready (edit `homeserver.yaml`, remove `federation_domain_whitelist`)

---

## Management

```bash
cd /opt/thelocal

# Logs
docker compose logs -f              # All services
docker compose logs -f synapse       # Just Synapse
docker compose logs -f livekit       # Just LiveKit

# Restart
docker compose restart

# Update all images
docker compose pull && docker compose up -d

# Pull config changes from GitHub
git pull
# If templates changed, re-generate active configs:
source .env
sed -e "s|%%POSTGRES_PASSWORD%%|${POSTGRES_PASSWORD}|g" \
    -e "s|%%REGISTRATION_SECRET%%|${REGISTRATION_SECRET}|g" \
    -e "s|%%MACAROON_SECRET%%|${MACAROON_SECRET}|g" \
    -e "s|%%FORM_SECRET%%|${FORM_SECRET}|g" \
    homeserver.yaml > homeserver.yaml.active
docker compose restart synapse

# Backup PostgreSQL
docker compose exec postgres pg_dump -U synapse synapse > backup-$(date +%Y%m%d).sql

# Backup media
docker compose cp synapse:/data/media_store ./media-backup-$(date +%Y%m%d)

# Create user
docker compose exec synapse register_new_matrix_user \
  -u USERNAME -p PASSWORD --no-admin \
  -c /data/homeserver.yaml http://localhost:8008
```

---

## Files

| File | Purpose | Git? |
|------|---------|------|
| `docker-compose.yml` | All 6 services | ✅ |
| `Caddyfile` | Reverse proxy + TLS | ✅ |
| `homeserver.yaml` | Synapse config (template) | ✅ |
| `homeserver.yaml.active` | Synapse config (with secrets) | ❌ |
| `element-config.json` | Element Web config | ✅ |
| `livekit/livekit.yaml` | LiveKit config (template) | ✅ |
| `livekit/livekit.yaml.active` | LiveKit config (with secrets) | ❌ |
| `well-known/matrix/server` | Federation delegation | ✅ |
| `well-known/matrix/client` | Client discovery + LiveKit | ✅ |
| `thelocal.chat.log.config` | Logging config | ✅ |
| `setup.sh` | First-time setup | ✅ |
| `.env` | All secrets | ❌ |

---

## Ports

| Port | Protocol | Service | Purpose |
|------|----------|---------|---------|
| 80 | TCP | Caddy | HTTP → HTTPS redirect |
| 443 | TCP | Caddy | HTTPS (all web traffic) |
| 7881 | TCP | LiveKit | WebRTC TCP fallback |
| 50100-50200 | UDP | LiveKit | WebRTC media streams |

Ensure all four are open in DO's firewall and the droplet's UFW.

---

## Security

- Registration **disabled** — accounts via CLI only
- Federation **disabled** — enable when ready for Tier 2
- E2EE **off by default** — enable per-room for sensitive topics
- Presence **disabled** — saves resources
- `.env`, `*.active` files contain secrets — never commit

---

## Costs

| Item | Cost |
|------|------|
| Domain (thelocal.chat) | ~$10-15/yr |
| DO droplet (1 vCPU, 2GB) | $12/mo |
| **Total** | ~$13/mo |

---

*Design Machines OÜ · DM-019/WORKS · March 2026*
