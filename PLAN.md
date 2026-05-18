# pill.ai — Plan de ejecución

> Documento de estado, arquitectura y roadmap del proyecto.  
> Branch activo: `claude/add-licensing-system-KsFAw`  
> Último commit: `e564389` — 18 mayo 2026

---

## Estado actual del repositorio

### Árbol de archivos

```
pill.ai/
├── .env.example                  ← variables de entorno (keys, admin secret)
├── .gitignore
├── LICENSE                       ← BSL-1.1 → Apache 2.0 el 2028-01-01
├── README.md                     ← documentación pública + tabla de costos
├── PLAN.md                       ← este documento
├── pyproject.toml                ← paquete `pill-ai`, entry point `pillai`
├── roadmap.md                    ← fases 1–3 detalladas
├── skills.md                     ← auto-generado por coder_agent
│
├── agents/
│   ├── __init__.py               ← exporta build_graph()
│   └── graph.py                  ← LangGraph StateGraph completo
│
├── interpreter/
│   ├── __init__.py
│   ├── interpreter.py            ← singleton `interpreter = Interpreter()`
│   ├── llm.py                    ← LiteLLM router (DeepSeek / Gemini / GPT-4o-mini)
│   ├── core/
│   │   ├── __init__.py
│   │   └── core.py               ← clase Interpreter: chat(), dispatch(), skills
│   └── tools/
│       ├── __init__.py
│       ├── browser.py            ← Playwright sync wrapper
│       ├── desktop.py            ← pyautogui: click, drag, hotkey, screenshot
│       └── shell.py              ← subprocess persistente, sudo, patrones peligrosos
│
├── licensing/
│   ├── __init__.py               ← exporta LicenseClient, activate, deactivate
│   ├── activation.py             ← activate(), deactivate(), require_license()
│   ├── client.py                 ← hardware fingerprint, caché offline 7 días
│   ├── models.py                 ← LicenseTier, LicenseStatus, LicenseInfo
│   └── server.py                 ← FastAPI: /v1/validate, /v1/usage, /admin/*
│
├── pill_ai/
│   ├── __init__.py
│   └── cli.py                    ← pillai activate|deactivate|status|server|run
│
└── installers/
    ├── install.sh                ← one-click Linux/macOS
    └── install.bat               ← one-click Windows
```

---

## Árbol de agentes

```
Usuario
  └─► Interpreter.chat(message)
        └─► require_license()          ← bloquea si no hay licencia válida
              └─► LangGraph graph
                    │
                    ▼
              [ supervisor_node ]       ← DeepSeek V4 Pro
                    │   analiza tarea, elige ruta, razona
                    │
                    ├──► [ vision_agent ]      ← Gemini 2.0 Flash
                    │        screenshot_and_describe()
                    │        describe_image(), OCR visual
                    │
                    ├──► [ browser_agent ]     ← DeepSeek V4 Pro
                    │        BrowserTool: goto, click, fill, text
                    │        Playwright sync → headless Chromium
                    │
                    ├──► [ desktop_agent ]     ← Gemini 2.0 Flash (visión)
                    │        DesktopTool: click, drag, scroll, type, hotkey
                    │        pyautogui + screenshot_and_describe()
                    │
                    ├──► [ shell_agent ]       ← DeepSeek V4 Pro
                    │        ShellTool: run(), run_python()
                    │        subprocess persistente, sudo caching
                    │        detección de comandos peligrosos (rm -rf, etc.)
                    │
                    └──► [ coder_agent ]       ← DeepSeek V4 Pro
                              genera código Python/bash
                              exec() con captura de salida
                              → appends a skills.md si nueva habilidad
                              │
                              ▼
                        [ final_node ]
                              │
                              ▼
                        respuesta al usuario

Límite: max 8 iteraciones por tarea (loop guard)
```

### Estado del AgentState (LangGraph TypedDict)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `messages` | `list[dict]` | historial de mensajes (add_messages reducer) |
| `task` | `str` | tarea original del usuario |
| `safe_mode` | `str` | `"auto"` / `"none"` / `"full"` |
| `license_tier` | `str` | tier activo: free / starter / pro / enterprise |
| `route` | `Optional[str]` | próximo agente a invocar |
| `agent_output` | `str` | output del último agente |
| `output` | `str` | respuesta final al usuario |
| `new_skill` | `Optional[str]` | skill a registrar en skills.md |
| `iteration` | `int` | contador anti-loop (máx 8) |

---

## Stack tecnológico

### Núcleo de IA

| Componente | Tecnología | Rol |
|------------|------------|-----|
| Orquestación | LangGraph `StateGraph` | grafo de agentes con estado compartido |
| LLM principal | DeepSeek V4 Pro via LiteLLM | razonamiento, código, supervisión |
| LLM visión | Gemini 2.0 Flash via LiteLLM | análisis de screenshots, OCR visual |
| LLM fallback | GPT-4o-mini via LiteLLM | resiliencia cuando DeepSeek falla |
| Routing | `LLMRouter` (custom) | selector de modelo por tarea + tracking de costo |

### Herramientas de computer-use

| Herramienta | Librería | Capacidades |
|-------------|----------|-------------|
| Browser | Playwright (sync) | navegación, clicks, forms, extracción de texto |
| Desktop | pyautogui | mouse, teclado, hotkeys, screenshots |
| Shell | subprocess | bash/python, sudo, streaming output |

### Licencias y monetización

| Componente | Tecnología | Rol |
|------------|------------|-----|
| License server | FastAPI + SQLite | validación, usage tracking, admin API |
| License client | httpx + diskcache | validación online/offline, fingerprint hardware |
| Hardware ID | SHA-256(MAC+CPU+hostname) | previene compartir keys |
| CLI | Click (via pyproject.toml) | `pillai` entry point |
| **Pendiente** | Stripe + Fly.io | billing y deploy producción |

### Infraestructura y dependencias

```
Python 3.12+
├── langgraph          ← orquestación de agentes
├── litellm            ← abstracción multi-LLM
├── fastapi + uvicorn  ← license server
├── playwright         ← browser automation
├── pyautogui          ← desktop automation
├── httpx              ← HTTP client async
├── pydantic           ← validación de datos
└── click              ← CLI
```

### Costos de inferencia (mayo 2026)

| Modelo | Input | Output | Uso en pill.ai |
|--------|-------|--------|----------------|
| DeepSeek V4 Pro | $0.14/M | $0.28/M | 90% de llamadas |
| Gemini 2.0 Flash | $0.10/M | $0.40/M | visión / desktop |
| GPT-4o-mini | $0.15/M | $0.60/M | fallback <10% |
| **Costo típico/tarea** | | | **$0.001–$0.01** |

---

## Árbol de documentos

```
Documentación pública
├── README.md              ← instalación, uso, costos, arquitectura
├── roadmap.md             ← fases 1–3, tabla de tareas, decisiones técnicas
├── PLAN.md                ← este documento (estado + arquitectura interna)
└── skills.md              ← habilidades auto-generadas por el agente

Configuración
├── .env.example           ← PILL_LICENSE_KEY, DEEPSEEK_API_KEY, GEMINI_API_KEY, ...
├── pyproject.toml         ← metadatos del paquete, dependencias, entry points
└── .gitignore             ← excluye .env, license.db, __pycache__, .pill.ai/

Licencia
└── LICENSE                ← BSL-1.1 con Change Date 2028-01-01 → Apache 2.0

Instaladores
├── installers/install.sh  ← Linux/macOS: git clone + venv + pip + playwright
└── installers/install.bat ← Windows: mismo flujo con cmd
```

---

## Fixes aplicados (2026-05-18)

| # | Problema | Fix |
|---|----------|-----|
| 1 | SQLite se corrompe si Fly.io escala a >1 máquina | `fly.toml`: `max_machines = 1`, `min_machines_running = 1` |
| 2 | Stripe webhook sin verificación de firma | `POST /webhooks/stripe` valida `Stripe-Signature` con `stripe.Webhook.construct_event()` antes de cualquier escritura |
| 3 | `SkillsCompactor` con TTL/conteo no aplica a skills | Rediseñado: verifica similitud semántica por entrada nueva (sin TTL, sin umbral), merge in-place si duplicado |
| 4 | `skills.md` en root era rastreado por git | Movido a `.pill.ai/skills.md` — ya cubierto por `.gitignore` |
| 5 | Hardware fingerprint débil en Docker/VMs | `machine_id` persistente en `~/.pill.ai/machine.id` como identidad primaria; MAC+CPU+hostname solo como fallback si el FS es read-only |

---

## Plan de ejecución — próximos pasos

### Inmediato (esta semana)

#### 1. Deploy del license server en Fly.io

```
licensing/server.py → Fly.io shared-cpu-1x (gratis hasta 3M req/mes)
```

Archivos creados:
- `licensing/Dockerfile` ✅
- `licensing/requirements.txt` ✅
- `fly.toml` ✅
- `fly secrets set ADMIN_SECRET=...` ← pendiente ejecutar
- DNS: `licenses.pill.ai` → CNAME a `pill-ai-licensing.fly.dev` ← pendiente

#### 2. Integración relay-master (pendiente acceso al repo)

Módulos identificados para integrar:

| Módulo agentic-repo | Dónde integra en pill.ai | Estado |
|--------------------|--------------------------|--------|
| `context-compactor.js` → portado a `interpreter/skills_compactor.py` | `interpreter/core/core.py` → `_update_skills()` | ✅ integrado |
| `batch_processor` | `licensing/client.py` → `report_usage()` | ❌ no existe en agentic-repo — diseñar desde cero si se necesita |
| `cache_layer` (reemplazar disco) | `licensing/client.py` | ❌ no aplica — el caché de 7 días en disco es más robusto para validación offline |

**Lo que se portó:** `SkillsCompactor` (in-memory, TTL 90s, umbral 12 entradas) colapsa entradas semánticamente similares en `skills.md` antes de hacer append. Si hay <12 entradas, append directo sin llamada LLM.

#### 3. Stripe billing

```
pill.ai/pricing → Stripe Checkout
Tiers: Free ($0) | Starter ($9/mes) | Pro ($29/mes) | Enterprise ($199/mes)
Webhook stripe → PATCH /admin/keys/{key} actualiza tier automáticamente
```

#### 4. Tests y CI

```
tests/
├── test_licensing.py   ← validación offline, expiración, hardware ID
├── test_llm_router.py  ← routing por tipo de tarea, budget exceeded
└── test_graph.py       ← supervisor routing, loop guard (max 8)

.github/workflows/ci.yml ← pytest + ruff en push a main y PRs
```

### Mediano plazo (1–3 meses)

- Docker sandbox por tarea (aislamiento real del shell_agent)
- Dashboard web (Streamlit) con historial, costos, usage analytics
- `POST /v1/task` API pública documentada
- Semantic memory compaction en producción
- Auto-update en instaladores

### Largo plazo (ver roadmap.md)

Fase 3 cubre: Ollama local ($0/tarea), mobile app, marketplace de agentes, fine-tuning propio, enterprise on-premise, cambio a Apache 2.0 en enero 2028.

---

## Decisiones técnicas pendientes

| Decisión | Opciones | Estado |
|----------|----------|--------|
| Deploy license server | Fly.io vs Railway | → **Fly.io** (mejor SQLite persistente) |
| Billing | Stripe vs Paddle | → **Stripe** (más APIs, mejor DX) |
| Sandbox shell | Docker vs gVisor vs nsjail | → **Docker** primero, gVisor en Fase 2 |
| Memory compaction | relay-master vs LangMem vs custom | → **relay-master** si acceso disponible |
| Frontend pricing page | Next.js vs Astro vs HTML estático | → **Astro** (sin build complexity) |

---

*Generado: 2026-05-18 — branch `claude/add-licensing-system-KsFAw`*
