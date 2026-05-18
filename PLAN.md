# pill.ai — Plan de ejecución

> Documento de estado, arquitectura y roadmap interno del proyecto.  
> Branch activo: `claude/add-licensing-system-KsFAw`  
> Último commit: `1933338` — 18 mayo 2026

---

## Estado actual del repositorio

### Árbol de archivos

```
pill.ai/
├── .env.example                   ← variables de entorno (API keys, admin secret)
├── .gitignore                     ← excluye .env, license.db, .pill.ai/
├── LICENSE                        ← BSL-1.1 → Apache 2.0 el 2028-01-01
├── README.md                      ← instalación one-click, costos, tabla OI vs pill.ai
├── PLAN.md                        ← este documento
├── fly.toml                       ← deploy Fly.io (max_machines=1, volumen /data)
├── pyproject.toml                 ← paquete `pill-ai`, entry point `pillai`
├── roadmap.md                     ← 3 fases: 0-2mo / 2-6mo / 6+mo
│
├── .github/
│   └── workflows/
│       └── ci.yml                 ← ruff + pytest + docker build en push/PR
│
├── agents/
│   ├── __init__.py                ← exporta build_graph()
│   └── graph.py                   ← LangGraph StateGraph + nodo human_approval
│
├── interpreter/
│   ├── __init__.py
│   ├── interpreter.py             ← singleton `interpreter = Interpreter()`
│   ├── llm.py                     ← LiteLLM router (DeepSeek / Gemini / GPT-4o-mini)
│   ├── skills_compactor.py        ← deduplicación semántica de skills.md
│   ├── core/
│   │   ├── __init__.py
│   │   └── core.py                ← Interpreter: chat(), dispatch(), skills
│   └── tools/
│       ├── __init__.py
│       ├── browser.py             ← Playwright sync wrapper
│       ├── desktop.py             ← pyautogui: click, drag, hotkey, screenshot
│       └── shell.py               ← subprocess, sudo, patrones peligrosos
│
├── licensing/
│   ├── __init__.py                ← exporta LicenseClient, activate, deactivate
│   ├── activation.py              ← require_license() (no bloquea), require_relay()
│   ├── client.py                  ← machine_id persistente, caché offline 7 días
│   ├── models.py                  ← LicenseTier, LicenseStatus, LicenseInfo
│   ├── server.py                  ← FastAPI: /v1/validate, /v1/usage, /admin/*, /webhooks/stripe
│   ├── Dockerfile                 ← imagen para Fly.io
│   └── requirements.txt           ← fastapi, uvicorn, pydantic, httpx, stripe
│
├── pill_ai/
│   ├── __init__.py
│   └── cli.py                     ← pillai activate|deactivate|status|server|run
│
└── installers/
    ├── install.sh                 ← one-click Linux/macOS
    └── install.bat                ← one-click Windows
```

---

## Política de licenciamiento

```
Local use   →  SIEMPRE GRATIS, sin cuenta, sin rate limit, sin network call
Relay cloud →  requiere license key (Starter $9/mo+)
```

- `require_license()` — nunca bloquea. Sin key → devuelve `LicenseInfo(key="LOCAL", daily_call_limit=0)`.
- `require_relay()` — único hard gate. Solo lo llaman features de cloud. Hace `SystemExit` si no hay key válida.
- `daily_call_limit=0` significa ilimitado (local free mode).

---

## Árbol de agentes

```
Usuario
  └─► Interpreter.chat(message)
        └─► require_license()          ← nunca bloquea; devuelve FREE si no hay key
              └─► LangGraph graph
                    │
                    ▼
              [ supervisor_node ]       ← DeepSeek V4 Pro
                    │   analiza tarea, elige ruta, incrementa iteración
                    │
                    ├──► [ vision_agent ]      ← Gemini 2.0 Flash
                    │        screenshot_and_describe()
                    │        OCR visual, análisis de UI
                    │
                    ├──► [ browser_agent ]     ← DeepSeek V4 Pro
                    │        BrowserTool: goto, click, fill, extract_text
                    │        Playwright sync → headless Chromium
                    │
                    ├──► [ desktop_agent ]     ← DeepSeek V4 Pro
                    │        DesktopTool: click, drag, scroll, type, hotkey
                    │        pyautogui + screenshot_and_describe()
                    │        ⚠ >10 clicks → human_approval
                    │
                    ├──► [ shell_agent ]       ← DeepSeek V4 Pro
                    │        ShellTool: run(), run_python()
                    │        sudo caching, streaming output
                    │        ⚠ rm -rf / sudo / mkfs → human_approval
                    │              │
                    │         [ human_approval_node ]
                    │              │  muestra la acción al usuario
                    │              │  y/n → continúa o va a final
                    │
                    └──► [ coder_agent ]       ← DeepSeek V4 Pro
                              genera código Python/bash
                              exec() con captura de salida
                              siempre actualiza ~/.pill.ai/skills.md
                              (deduplicación semántica via skills_compactor.py)
                              │
                              ▼
                        [ final_node ]          ← DeepSeek V4 Pro
                              sintetiza output de todos los agentes
                              │
                              ▼
                        respuesta al usuario

Loop guard: max 8 iteraciones supervisor→specialist→supervisor
safe_mode="off": omite human_approval en todos los nodos
```

### AgentState (LangGraph TypedDict)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `messages` | `list[dict]` | historial (add_messages reducer) |
| `task` | `str` | tarea original del usuario |
| `safe_mode` | `str` | `"ask"` / `"off"` / `"auto"` |
| `license_tier` | `str` | free / starter / pro / enterprise |
| `route` | `Optional[str]` | próximo nodo a invocar |
| `agent_output` | `str` | output del último agente |
| `output` | `str` | respuesta final al usuario |
| `new_skill` | `Optional[str]` | skill a registrar en skills.md |
| `iteration` | `int` | contador anti-loop (máx 8) |
| `pending_command` | `Optional[str]` | **HITL:** acción esperando aprobación |
| `pending_agent` | `Optional[str]` | **HITL:** agente que reanuda tras aprobación |

---

## Stack tecnológico

### Núcleo de IA

| Componente | Tecnología | Rol |
|------------|------------|-----|
| Orquestación | LangGraph `StateGraph` | grafo de agentes con estado compartido |
| LLM principal | DeepSeek V4 Pro via LiteLLM | razonamiento, código, supervisión |
| LLM visión | Gemini 2.0 Flash via LiteLLM | análisis de screenshots, OCR visual |
| LLM fallback | GPT-4o-mini via LiteLLM | resiliencia cuando DeepSeek falla |
| Router | `LLMRouter` (custom) | selector de modelo + tracking de costo/tarea |

### Herramientas de computer-use

| Herramienta | Librería | Capacidades |
|-------------|----------|-------------|
| Browser | Playwright (sync) | navegación, clicks, forms, extracción de texto |
| Desktop | pyautogui | mouse, teclado, hotkeys, screenshots |
| Shell | subprocess | bash/python, sudo, streaming, timeout |

### Licencias y monetización

| Componente | Tecnología | Estado |
|------------|------------|--------|
| License server | FastAPI + SQLite | ✅ listo |
| License client | httpx + JSON cache | ✅ listo |
| Hardware ID | `machine.id` UUID persistente | ✅ listo |
| Stripe webhook | `stripe.Webhook.construct_event()` | ✅ listo |
| Deploy | Fly.io `max_machines=1` | ⬜ pendiente `fly deploy` |
| DNS | `licenses.pill.ai` → CNAME fly.dev | ⬜ pendiente |
| Página precios | `pill.ai/pricing` + Stripe Checkout | ⬜ pendiente |

### Infraestructura

```
Python 3.12+
├── langgraph          ← StateGraph, conditional edges, HITL
├── litellm            ← abstracción multi-LLM
├── fastapi + uvicorn  ← license server
├── stripe             ← webhook verification
├── playwright         ← browser automation
├── pyautogui          ← desktop automation
├── httpx              ← HTTP client
├── pydantic           ← validación de datos
└── click              ← CLI entry point
```

### Costos de inferencia (mayo 2026)

| Modelo | Input | Output | Uso |
|--------|-------|--------|-----|
| DeepSeek V4 Pro | $0.14/M | $0.28/M | 90% de llamadas |
| Gemini 2.0 Flash | $0.10/M | $0.40/M | visión / desktop |
| GPT-4o-mini | $0.15/M | $0.60/M | fallback <10% |
| **Costo típico/tarea** | | | **$0.001–$0.01** |

---

## Árbol de documentos

```
Pública
├── README.md              ← instalación one-click, free-first, tabla OI vs pill.ai
├── roadmap.md             ← 3 fases, tabla de tareas, decisiones de arquitectura
├── PLAN.md                ← este documento (estado interno, árbol de agentes)
└── ~/.pill.ai/skills.md   ← auto-generado, gitignoreado, deduplicación semántica

CI/CD
└── .github/workflows/ci.yml  ← ruff + pytest + docker build

Configuración
├── .env.example           ← DEEPSEEK_API_KEY, GEMINI_API_KEY, PILLAI_ADMIN_SECRET, ...
├── pyproject.toml         ← metadatos, dependencias, entry points
└── .gitignore             ← excluye .env, license.db, .pill.ai/

Deploy
├── fly.toml               ← Fly.io: 1 máquina, volumen /data, 256MB RAM
└── licensing/Dockerfile   ← imagen FastAPI del license server

Licencia
└── LICENSE                ← BSL-1.1 → Apache 2.0 (2028-01-01)
```

---

## Relación con Open Interpreter

pill.ai **no es un fork de código** de Open Interpreter — es una reimplementación con la misma API pública. Esto permite que usuarios de OI migren sin cambiar una línea de código de su lado.

| | Open Interpreter | pill.ai |
|--|-----------------|---------|
| `interpreter.chat()` | ✅ | ✅ |
| `interpreter.reset()` | ✅ | ✅ |
| `interpreter.computer.*` | ✅ | ✅ |
| `auto_run`, `safe_mode` | ✅ | ✅ |
| Agent loop | ReAct single loop | LangGraph multi-agent StateGraph |
| LLM layer | Custom classes | LiteLLM (multi-provider) |
| Default model | GPT-4o | DeepSeek V4 Pro (95% más barato) |
| Human-in-the-loop | Inline input() | Nodo explícito en el grafo |
| Skills memory | No | `~/.pill.ai/skills.md` + dedup semántico |
| Modo local gratis | Sí | Sí, ilimitado, sin cuenta |
| Licencia | MIT | BSL-1.1 → Apache 2.0 (2028) |

---

## Integración agentic-repo

| Módulo | Estado | Notas |
|--------|--------|-------|
| `context-compactor.js` → `interpreter/skills_compactor.py` | ✅ portado | Dedup semántico por entrada nueva (sin TTL, sin umbral de conteo) |
| `batch_processor` | ❌ no existe en agentic-repo | Diseñar desde cero en Fase 2 si se necesita |
| `cache_layer` | ❌ no aplica | El caché de 7 días en disco de `licensing/client.py` es más robusto para validación offline |

---

## Fixes de seguridad y fiabilidad aplicados

| # | Problema | Fix | Commit |
|---|----------|-----|--------|
| 1 | SQLite corrupción si Fly.io escala a >1 máquina | `fly.toml`: `max_machines=1`, `min_machines_running=1` | `3d26c7b` |
| 2 | Stripe webhook sin verificación de firma | `POST /webhooks/stripe` valida `Stripe-Signature` antes de cualquier escritura | `3d26c7b` |
| 3 | SkillsCompactor por TTL/conteo no aplica a skills | Rediseñado: similitud semántica por entrada, merge in-place si duplicado | `3d26c7b` |
| 4 | `skills.md` en root rastreado por git | Movido a `~/.pill.ai/skills.md` (gitignoreado) | `3d26c7b` |
| 5 | Fingerprint débil en Docker/VMs | `machine_id` UUID persistente en `~/.pill.ai/machine.id` | `3d26c7b` |
| 6 | `require_license()` bloqueaba uso local | Nunca bloquea; `require_relay()` es el único hard gate | `1933338` |
| 7 | shell_agent ejecutaba comandos peligrosos sin confirmación | Nodo `human_approval` en el grafo para `rm -rf`, `sudo`, >10 clicks | `1933338` |

---

## Próximos pasos

### Inmediato

| Tarea | Comando |
|-------|---------|
| Deploy license server | `fly volumes create licensing_data --size 1 && fly secrets set ADMIN_SECRET=xxx && fly deploy` |
| DNS | `licenses.pill.ai` → CNAME `pill-ai-licensing.fly.dev` |
| Tests | Crear `tests/test_licensing.py`, `test_graph.py`, `test_llm_router.py` |
| Pricing page | Astro + Stripe Checkout en `pill.ai/pricing` |

### Mediano plazo (ver roadmap.md Fase 2)

Dashboard Streamlit · relay cloud · auto-update · skills marketplace · Docker sandbox avanzado

### Largo plazo (ver roadmap.md Fase 3)

Ollama local · mobile app · enterprise on-premise · Apache 2.0 (2028)

---

## Decisiones técnicas

| Decisión | Elegida | Razón |
|----------|---------|-------|
| Deploy license server | Fly.io | SQLite persistente con volumen, gratis hasta 3M req/mes |
| Base de datos | SQLite | Suficiente para 1 writer; migrar a Turso si crece |
| Billing | Stripe | Mejor DX, webhook robusto, Checkout hosted |
| Sandbox shell | Docker (Fase 1), gVisor (Fase 2) | Docker es simple; gVisor añade syscall filtering |
| Memory compaction | `skills_compactor.py` custom | relay-master solo tiene context-compactor para conversación, no skills |
| Frontend precios | Astro | Sin build complexity, HTML estático, deploys en Netlify/CF Pages |
| API-compat target | Open Interpreter | Mayor base de usuarios, migración sin fricción |

---

*Actualizado: 2026-05-18 — commit `1933338` — branch `claude/add-licensing-system-KsFAw`*
