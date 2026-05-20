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

Los agentes controlan el servidor vía HTTP — sin SSH, mismo consumo de tokens.

### Endpoints disponibles

| Endpoint | Método | Qué hace |
|----------|--------|----------|
| `/admin/deploy` | POST | git pull + systemctl restart |
| `/admin/exec` | POST | Ejecutar cualquier comando bash |
| `/admin/logs` | GET | Ver logs de systemd o pm2 |

Todos requieren header `x-deploy-secret: $PILLAI_DEPLOY_SECRET`.

### Ejemplos de uso

```python
import requests, os

SECRET = os.environ["PILLAI_DEPLOY_SECRET"]
BASE   = "http://143.198.228.78:8181"
HEADERS = {"x-deploy-secret": SECRET}

# Deploy
requests.post(f"{BASE}/admin/deploy", headers=HEADERS)

# Comando bash (git pull, pm2, etc.)
r = requests.post(f"{BASE}/admin/exec", headers=HEADERS,
    json={"command": "pm2 status", "cwd": "/var/www/html/vilarkptl.com/pill-relay"})
print(r.json()["stdout"])

# Comando peligroso — el server exige confirmed=True (pedir permiso al usuario primero)
r = requests.post(f"{BASE}/admin/exec", headers=HEADERS,
    json={"command": "rm -rf /tmp/old", "confirmed": True})  # solo tras aprobación

# Logs
r = requests.get(f"{BASE}/admin/logs", headers=HEADERS,
    params={"service": "pillai-relay", "lines": 200})
print(r.json()["logs"])
```

### Setup en el servidor (una sola vez)

```bash
# 1. Generar y guardar el secret
python3 -c "import secrets; print(secrets.token_hex(32))"
echo 'PILLAI_DEPLOY_SECRET=<token>' >> /var/www/html/vilarkptl.com/pill-relay/.env

# 2. Asegurarse de que git pull funcione sin contraseña
cd /var/www/html/vilarkptl.com/pill-relay
git remote set-url origin https://github.com/vilarkptl-lang/pill.ai.git
# repo privado → usar token:
# git remote set-url origin https://<token>@github.com/vilarkptl-lang/pill.ai.git

systemctl restart pillai-relay
```

El deploy secret vive **solo en el `.env` del servidor** y en `PILLAI_DEPLOY_SECRET` en cada agente. Nunca se commitea al repo.

## Reglas de seguridad (NO violar)

- **Nunca** poner API keys de Anthropic/DeepSeek/Gemini en el repo
- **Nunca** commitear `.env`
- **Nunca** hardcodear la IP `201.149.87.114` en código
- Las API keys viven solo en el servidor (`/var/www/html/vilarkptl.com/pill-relay/.env`)
