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
│   ├── /livekit/sfu/*       → LiveKit SFU WebSocket (port 7880)
│   ├── /github/*            → Hookshot GitHub webhooks (port 9000)
│   ├── /oauth               → Hookshot GitHub OAuth callback
│   ├── /webhook/*           → Hookshot generic webhooks
│   └── /figma/*             → Hookshot Figma webhooks (disabled)

Direct (not proxied):
    7881/tcp                 → LiveKit TCP fallback
    50100-50200/udp          → LiveKit WebRTC media streams

Internal:
    Synapse → PostgreSQL (Docker network)
    Synapse ↔ Hookshot (appservice, port 9993)
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

The script generates secrets, templates configs, opens firewall ports, and starts all 7 services.

Until you complete [Hookshot: GitHub App](#hookshot-github-app) below, `setup.sh` renders the bridge config **without** the GitHub block — hookshot exits on a missing private key, and a crash-looping bridge would take feeds and generic webhooks down with it. Re-run `./setup.sh` once the App exists and the block comes back automatically.

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

## Integrations (Hookshot)

[matrix-hookshot](https://matrix-org.github.io/matrix-hookshot/latest/) bridges GitHub, RSS/Atom feeds, and generic webhooks into rooms. It is a Matrix **application service**, not a plain webhook receiver — it registers with Synapse via `hookshot/registration.yml.active`, mounted into Synapse at `/data/hookshot-registration.yaml`.

**Synapse refuses to start if that file is missing.** Always run `./setup.sh` before restarting Synapse after a `git pull`.

### Hookshot: GitHub App

Create the App at <https://github.com/settings/apps/new>, under the `design-machines-studio` org so it can be installed on multiple repos.

| Field | Value |
|-------|-------|
| Webhook URL | `https://matrix.thelocal.chat/github/webhook` |
| Webhook secret | value of `GITHUB_WEBHOOK_SECRET` in `.env` |
| Callback URL | `https://matrix.thelocal.chat/oauth` |

The Callback URL must match `oauth.redirect_uri` in `hookshot/config.yml` **character for character** — no trailing slash.

**Repository permissions:** Actions (read), Contents (read), Discussions (read & write), Issues (read & write), Metadata (read), Projects (read & write), Pull requests (read & write)

**Organization permissions:** none needed.

Hookshot's upstream docs ask for Team Discussions (read & write). GitHub [retired Team Discussions](https://github.blog/changelog/2023-02-08-sunset-notice-team-discussions/) in favour of Organization Discussions, so that permission no longer appears on the App form. Skip it. The Repository-level "Discussions" permission above is a different thing and is still required.

**Subscribe to events:** commit comment, create, delete, discussion, discussion comment, issue comment, issues, project, project card, project column, pull request, pull request review, pull request review comment, push, release, repository, workflow run

Then, on the droplet:

```bash
cd /opt/thelocal

# App ID + OAuth credentials from the App's settings page
nano .env    # set GITHUB_APP_ID, GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET

# Private key: "Generate a private key" downloads a .pem — scp it up
chmod 600 hookshot/github-key.pem

./setup.sh
docker compose up -d --force-recreate hookshot
```

Finally, **install** the App on the repos you want bridged.

### Connecting a room

Create `#dm-github:thelocal.chat`, invite `@hookshot:thelocal.chat`, then:

```
!hookshot github login                                    # OAuth, once per person
!hookshot github repo design-machines-studio/the-local
!hookshot feed https://example.com/feed.xml               # RSS/Atom
!hookshot webhook assembly-governance                     # returns a generic webhook URL
```

Anyone on `thelocal.chat` can run commands; `@trav` has admin. Adjust in the `permissions` block of `hookshot/config.yml`.

### Upgrading an existing install

`setup.sh` skips secret generation entirely when `.env` exists, so an install that predates Hookshot needs these appended by hand before running it:

```bash
cd /opt/thelocal
cat >> .env << EOF

HOOKSHOT_AS_TOKEN=$(openssl rand -hex 32)
HOOKSHOT_HS_TOKEN=$(openssl rand -hex 32)
GITHUB_WEBHOOK_SECRET=$(openssl rand -hex 32)
GITHUB_APP_ID=REPLACE_ME
GITHUB_OAUTH_CLIENT_ID=REPLACE_ME
GITHUB_OAUTH_CLIENT_SECRET=REPLACE_ME
FIGMA_TEAM_ID=REPLACE_ME
FIGMA_ACCESS_TOKEN=REPLACE_ME
FIGMA_PASSCODE=REPLACE_ME
EOF
```

`setup.sh` will abort with a clear message if the two Hookshot tokens are absent.

### Figma

Figma webhooks require a **paid Figma team plan**. The `figma:` block in `hookshot/config.yml` is commented out; on a Starter team, hookshot fails to register the webhook at startup. Uncomment it, fill the three `FIGMA_*` values in `.env`, and re-run `./setup.sh`. The `/figma/*` Caddy route is already in place.

### Resource note

Hookshot is a Node process, roughly 150-250MB resident. On the 2GB droplet, check after deploy:

```bash
docker stats --no-stream
```

If total RAM sits above 80%, resize the droplet.

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
# Re-generate all active configs (idempotent — reuses existing .env):
./setup.sh
# git pull swaps inodes; Docker bind mounts track inodes, not names:
docker compose up -d --force-recreate synapse caddy hookshot element

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
| `docker-compose.yml` | All 7 services | ✅ |
| `Caddyfile` | Reverse proxy + TLS | ✅ |
| `homeserver.yaml` | Synapse config (template) | ✅ |
| `homeserver.yaml.active` | Synapse config (with secrets) | ❌ |
| `element-config.json` | Element Web config | ✅ |
| `livekit/livekit.yaml` | LiveKit config (template) | ✅ |
| `livekit/livekit.yaml.active` | LiveKit config (with secrets) | ❌ |
| `hookshot/config.yml` | Hookshot bridge config (template) | ✅ |
| `hookshot/registration.yml` | Hookshot appservice registration (template) | ✅ |
| `hookshot/*.active` | Hookshot configs (with secrets) | ❌ |
| `hookshot/passkey.pem` | Encrypts stored OAuth tokens | ❌ |
| `hookshot/github-key.pem` | GitHub App private key | ❌ |
| `well-known/matrix/server` | Federation delegation | ✅ |
| `well-known/matrix/client` | Client discovery + LiveKit | ✅ |
| `thelocal.chat.log.config` | Logging config | ✅ |
| `setup.sh` | First-time setup | ✅ |
| `templates/` | Branded Synapse email + web page templates (overrides Synapse defaults) | ✅ |
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

- Registration **token-gated** — accounts created via CLI or shared registration tokens
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
