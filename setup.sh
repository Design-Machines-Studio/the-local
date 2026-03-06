#!/bin/bash
# ═══════════════════════════════════════════════════════════
# The Local — First-time setup
# DM-019/WORKS · thelocal.chat
#
# Run once on a fresh Ubuntu 24.04 DO droplet after cloning.
# Generates secrets, templates configs, starts everything.
# ═══════════════════════════════════════════════════════════

set -euo pipefail

echo ""
echo "═══════════════════════════════════════════════════"
echo "  The Local — thelocal.chat"
echo "  Matrix + Element Call for workplace democracy"
echo "═══════════════════════════════════════════════════"
echo ""

# ─── Preflight ───────────────────────────────────────────
if [ ! -f "docker-compose.yml" ]; then
  echo "✗ Run this from the repo root."
  exit 1
fi

# ─── Step 1: Generate secrets ────────────────────────────
echo "→ Step 1: Secrets"

if [ -f ".env" ]; then
  echo "  .env exists — using existing secrets."
  echo "  (Delete .env and re-run to regenerate.)"
else
  echo "  Generating secrets..."

  POSTGRES_PASSWORD=$(openssl rand -hex 32)
  REGISTRATION_SECRET=$(openssl rand -hex 32)
  MACAROON_SECRET=$(openssl rand -hex 32)
  FORM_SECRET=$(openssl rand -hex 32)
  LIVEKIT_KEY="thelocal$(openssl rand -hex 4)"
  LIVEKIT_SECRET=$(openssl rand -hex 32)

  cat > .env << EOF
# The Local — Secrets
# Generated $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT COMMIT

POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
REGISTRATION_SECRET=${REGISTRATION_SECRET}
MACAROON_SECRET=${MACAROON_SECRET}
FORM_SECRET=${FORM_SECRET}
LIVEKIT_KEY=${LIVEKIT_KEY}
LIVEKIT_SECRET=${LIVEKIT_SECRET}
EOF

  chmod 600 .env
  echo "  ✓ Secrets saved to .env"
fi

# ─── Step 2: Template configs ────────────────────────────
echo ""
echo "→ Step 2: Config files"

set -a
source .env
set +a

# Synapse config
sed \
  -e "s|%%POSTGRES_PASSWORD%%|${POSTGRES_PASSWORD}|g" \
  -e "s|%%REGISTRATION_SECRET%%|${REGISTRATION_SECRET}|g" \
  -e "s|%%MACAROON_SECRET%%|${MACAROON_SECRET}|g" \
  -e "s|%%FORM_SECRET%%|${FORM_SECRET}|g" \
  homeserver.yaml > homeserver.yaml.active
chmod 600 homeserver.yaml.active
echo "  ✓ homeserver.yaml.active"

# LiveKit config
sed \
  -e "s|%%LIVEKIT_KEY%%|${LIVEKIT_KEY}|g" \
  -e "s|%%LIVEKIT_SECRET%%|${LIVEKIT_SECRET}|g" \
  livekit/livekit.yaml > livekit/livekit.yaml.active
chmod 600 livekit/livekit.yaml.active
echo "  ✓ livekit/livekit.yaml.active"

# ─── Step 3: Signing key ────────────────────────────────
echo ""
echo "→ Step 3: Signing key"

docker pull matrixdotorg/synapse:latest -q 2>/dev/null

# Generate key into volume
docker run --rm \
  -v thelocal_synapse_data:/data \
  -e SYNAPSE_SERVER_NAME=thelocal.chat \
  -e SYNAPSE_REPORT_STATS=no \
  matrixdotorg/synapse:latest generate 2>/dev/null || true

# Ensure media store
docker run --rm \
  -v thelocal_synapse_data:/data \
  matrixdotorg/synapse:latest \
  sh -c "mkdir -p /data/media_store && chown 991:991 /data/media_store" 2>/dev/null || true

echo "  ✓ Signing key generated"

# ─── Step 4: Firewall ───────────────────────────────────
echo ""
echo "→ Step 4: Firewall"

if command -v ufw &> /dev/null; then
  ufw allow 80/tcp    comment "HTTP"          2>/dev/null || true
  ufw allow 443/tcp   comment "HTTPS"         2>/dev/null || true
  ufw allow 7881/tcp  comment "LiveKit TCP"   2>/dev/null || true
  ufw allow 50100:50200/udp comment "LiveKit WebRTC" 2>/dev/null || true
  echo "  ✓ UFW rules added (80, 443, 7881, 50100-50200/udp)"
else
  echo "  ⚠ UFW not found. Ensure these ports are open:"
  echo "    80/tcp, 443/tcp, 7881/tcp, 50100-50200/udp"
fi

# ─── Step 5: Start ──────────────────────────────────────
echo ""
echo "→ Step 5: Starting services"

docker compose up -d
echo "  Waiting for services..."
sleep 15

RUNNING=$(docker compose ps --format "{{.State}}" | grep -c "running" || true)
TOTAL=$(docker compose ps --format "{{.State}}" | wc -l)
echo "  ✓ ${RUNNING}/${TOTAL} services running"

if [ "$RUNNING" -lt "$TOTAL" ]; then
  echo ""
  echo "  ⚠ Some services may still be starting. Check:"
  echo "    docker compose logs -f"
fi

# ─── Done ────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo ""
echo "  The Local is starting up."
echo ""
echo "  Chat:     https://thelocal.chat"
echo "  Synapse:  https://matrix.thelocal.chat"
echo "  Calls:    Built into Element (LiveKit SFU)"
echo ""
echo "  Caddy needs 1-2 min for TLS certificates."
echo ""
echo "  ─── Create your admin account ─────────────────"
echo ""
echo "  docker compose exec synapse register_new_matrix_user \\"
echo "    -u trav -p YOUR_SECURE_PASSWORD -a \\"
echo "    -c /data/homeserver.yaml \\"
echo "    http://localhost:8008"
echo ""
echo "  Then log in at https://thelocal.chat"
echo ""
echo "  ─── Ports to verify ───────────────────────────"
echo ""
echo "  80/tcp    — HTTP (Caddy redirect)"
echo "  443/tcp   — HTTPS (Caddy TLS)"
echo "  7881/tcp  — LiveKit TCP fallback"
echo "  50100-50200/udp — LiveKit WebRTC media"
echo ""
echo "═══════════════════════════════════════════════════"
