# pill.ai — Notas para el equipo de desarrollo

## Relay server (producción)

- **IP**: `143.198.228.78`
- **Puerto**: `8181`
- **URL**: `http://143.198.228.78:8181`
- **Directorio en servidor**: `/var/www/html/vilarkptl.com/pill-relay/`
- **Servicio systemd**: `pillai-relay` (auto-arranca en boot)
- **Verificar que corre**: `curl http://143.198.228.78:8181/health`

## Probar en Mac — Primera vez (setup completo)

```bash
# 1. Clonar el repo (crea la carpeta ~/pill.ai)
cd ~
git clone https://github.com/vilarkptl-lang/pill.ai.git
cd pill.ai
git checkout claude/add-licensing-system-KsFAw

# 2. Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install pystray keyboard pillow

# 3. Correr
export PILLAI_RELAY_URL=http://143.198.228.78:8181
python -m pill_ai.tray
```

## Probar en Mac — Uso diario (ya instalado)

```bash
cd ~/pill.ai
source .venv/bin/activate
export PILLAI_RELAY_URL=http://143.198.228.78:8181
python -m pill_ai.tray
```

Atajo de teclado para abrir el overlay: **Ctrl+Space**

## Construir el .exe para Windows

Desde la Mac o una máquina con Python 3.12:

```bash
cd ~/pill.ai
source .venv/bin/activate
export PILLAI_RELAY_URL=http://143.198.228.78:8181
python installers/build_exe.py
# Output: dist/pillai.exe
```

## Instalar en PC nueva (Windows)

```bat
pip install -e .
set PILLAI_RELAY_URL=http://143.198.228.78:8181
python -m pill_ai.tray
```

O simplemente copiar `dist/pillai.exe` al PC y ejecutarlo (doble clic o desde cmd).

## Rama de desarrollo activa

```
claude/add-licensing-system-KsFAw
```

## Deploy desde agentes (sin SSH)

Los agentes pueden hacer deploy llamando al webhook HTTP:

```bash
curl -X POST http://143.198.228.78:8181/admin/deploy \
  -H "x-deploy-secret: $PILLAI_DEPLOY_SECRET"
```

O desde Python:
```python
import requests
requests.post(
    "http://143.198.228.78:8181/admin/deploy",
    headers={"x-deploy-secret": DEPLOY_SECRET},
)
```

**Setup en el servidor (una sola vez):**
```bash
# Agregar al .env del servidor:
echo 'PILLAI_DEPLOY_SECRET=<secret-que-generes>' >> /var/www/html/vilarkptl.com/pill-relay/.env

# Asegurarse de que git pull funcione sin contraseña:
cd /var/www/html/vilarkptl.com/pill-relay
git remote set-url origin https://github.com/vilarkptl-lang/pill.ai.git
# Si el repo es privado, usar token:
# git remote set-url origin https://<token>@github.com/vilarkptl-lang/pill.ai.git
```

El deploy secret vive **solo en el `.env` del servidor** y en la variable de entorno de cada agente (`PILLAI_DEPLOY_SECRET`). Nunca se commitea al repo.

## Reglas de seguridad (NO violar)

- **Nunca** poner API keys de Anthropic/DeepSeek/Gemini en el repo
- **Nunca** commitear `.env`
- **Nunca** hardcodear la IP `201.149.87.114` en código
- Las API keys viven solo en el servidor (`/var/www/html/vilarkptl.com/pill-relay/.env`)
