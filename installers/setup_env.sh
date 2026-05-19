#!/usr/bin/env bash
# installers/setup_env.sh
# Genera .env de pill.ai leyendo las API keys del relay existente.
# Correr en el servidor: bash installers/setup_env.sh

set -e

RELAY_ENV="/var/www/html/vilarkptl.com/ai-monitor/relay/.env"
PILL_DIR="/var/www/html/pill.ai"
OUT="$PILL_DIR/.env"

if [ ! -f "$RELAY_ENV" ]; then
  echo "ERROR: no encontré $RELAY_ENV"
  exit 1
fi

# Extraer valores sin imprimirlos en pantalla
DEEPSEEK_API_KEY=$(grep '^DEEPSEEK_API_KEY=' "$RELAY_ENV" | cut -d= -f2-)
GEMINI_API_KEY=$(grep '^GOOGLE_API_KEY=' "$RELAY_ENV" | cut -d= -f2-)
ANTHROPIC_API_KEY=$(grep '^ANTHROPIC_API_KEY=' "$RELAY_ENV" | cut -d= -f2-)

# Validar que se encontraron
missing=0
[ -z "$DEEPSEEK_API_KEY" ]  && echo "WARN: DEEPSEEK_API_KEY no encontrada en relay .env"  && missing=$((missing+1))
[ -z "$GEMINI_API_KEY" ]    && echo "WARN: GOOGLE_API_KEY no encontrada en relay .env"    && missing=$((missing+1))
[ -z "$ANTHROPIC_API_KEY" ] && echo "WARN: ANTHROPIC_API_KEY no encontrada en relay .env" && missing=$((missing+1))

if [ "$missing" -eq 3 ]; then
  echo "ERROR: no se encontró ninguna key en $RELAY_ENV"
  exit 1
fi

# Pedir datos que no vienen del relay
read -rp "PILLAI_ADMIN_SECRET (presiona Enter para generar uno): " ADMIN_SECRET
if [ -z "$ADMIN_SECRET" ]; then
  ADMIN_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
fi

read -rp "MySQL URL [default: mysql+pymysql://root:@localhost/pillai]: " DB_URL
DB_URL="${DB_URL:-mysql+pymysql://root:@localhost/pillai}"

# Escribir .env (sin mostrar los valores en pantalla)
cat > "$OUT" <<EOF
# pill.ai server environment — generado por installers/setup_env.sh
# NUNCA subir este archivo a git

PILLAI_ADMIN_SECRET=${ADMIN_SECRET}

PILLAI_DB_URL=${DB_URL}

GEMINI_API_KEY=${GEMINI_API_KEY}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

PILLAI_MODEL_FAST=gemini/gemini-2.0-flash-exp
PILLAI_MODEL_MEDIUM=deepseek/deepseek-chat
PILLAI_MODEL_PRO=deepseek/deepseek-chat

PILLAI_GRACE_DAYS=7
PILLAI_CACHE_DIR=~/.pill.ai
EOF

chmod 600 "$OUT"
echo ""
echo "OK: $OUT creado con permisos 600"
echo "Siguiente paso: make server"
