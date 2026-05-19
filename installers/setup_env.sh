#!/usr/bin/env bash
# installers/setup_env.sh
# Genera .env de pill.ai leyendo keys y DB del relay/backend existente.
# Correr en el servidor: bash installers/setup_env.sh

set -e

RELAY_ENV="/var/www/html/vilarkptl.com/ai-monitor/relay/.env"
BACKEND_ENV="/var/www/html/vilarkptl.com/ai-monitor/backend/.env"
PILL_DIR="/var/www/html/pill.ai"
OUT="$PILL_DIR/.env"

# ── Verificar archivos fuente ─────────────────────────────────────────────
for f in "$RELAY_ENV" "$BACKEND_ENV"; do
  [ -f "$f" ] || { echo "ERROR: no encontré $f"; exit 1; }
done

# ── Leer API keys (sin imprimirlas) ──────────────────────────────────────
DEEPSEEK_API_KEY=$(grep -oP 'DEEPSEEK_API_KEY=\K.*' "$RELAY_ENV")
GEMINI_API_KEY=$(grep -oP 'GOOGLE_API_KEY=\K.*' "$RELAY_ENV")

# ── Leer credenciales MySQL ───────────────────────────────────────────────
DB_HOST=$(grep -oP 'DB_HOST=\K.*' "$BACKEND_ENV")
DB_USER=$(grep -oP 'DB_USER=\K.*' "$BACKEND_ENV")
DB_PASS=$(grep -oP 'DB_PASS=\K.*' "$BACKEND_ENV")
DB_NAME=$(grep -oP 'DB_NAME=\K.*' "$BACKEND_ENV")
DB_HOST="${DB_HOST:-localhost}"
DB_URL="mysql+pymysql://${DB_USER}:${DB_PASS}@${DB_HOST}/${DB_NAME:-pillai}"

# ── Crear DB si no existe ────────────────────────────────────────────────
mysql -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" \
  -e "CREATE DATABASE IF NOT EXISTS \`${DB_NAME:-pillai}\`;" 2>/dev/null \
  && echo "OK: base de datos ${DB_NAME:-pillai} lista" \
  || echo "WARN: no se pudo crear la DB (puede que ya exista)"

# ── Generar admin secret automáticamente ─────────────────────────────────
ADMIN_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# ── Escribir .env ─────────────────────────────────────────────────────────
cat > "$OUT" <<EOF
# pill.ai server environment — generado por installers/setup_env.sh
# NUNCA subir este archivo a git

PILLAI_ADMIN_SECRET=${ADMIN_SECRET}

PILLAI_DB_URL=${DB_URL}

GEMINI_API_KEY=${GEMINI_API_KEY}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}

PILLAI_MODEL_FAST=gemini/gemini-2.0-flash-exp
PILLAI_MODEL_MEDIUM=deepseek/deepseek-chat
PILLAI_MODEL_PRO=deepseek/deepseek-chat

PILLAI_GRACE_DAYS=7
PILLAI_CACHE_DIR=~/.pill.ai
EOF

chmod 600 "$OUT"
echo "OK: $OUT creado (chmod 600)"
echo "OK: PILLAI_ADMIN_SECRET generado automáticamente"
echo ""
echo "Siguiente paso:"
echo "  source /var/www/html/pill.ai/.venv/bin/activate && make server"

