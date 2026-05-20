# pill.ai — Roadmap

> **Principio rector:** Core 100% gratis y open-source forever. Relay cloud y tiers Pro son opcionales y financian el desarrollo.

**Stack:** Python 3.12 · LangGraph · LiteLLM · DeepSeek V4 Pro · Gemini Flash · Playwright · pyautogui · BSL-1.1 → Apache 2.0 (2028)

---

## Fase 1 — MVP open-source (0–2 meses)
**Objetivo:** Lanzar en GitHub con suficiente calidad para ser viral. Instalar en 30 segundos, correr sin cuenta.

| # | Tarea | Estado |
|---|-------|--------|
| 1.1 | Fork real de Open Interpreter: todos los 40+ params de `__init__`, `computer.*` (8 módulos), diff explícito en `OI_DIFF.md` | ✅ |
| 1.2 | LangGraph multi-agente: Supervisor → Vision / Browser / Desktop / Shell / Coder | ✅ |
| 1.3 | LiteLLM routing: DeepSeek V4 Pro (90%) + Gemini Flash (visión) + GPT-4o-mini (fallback) | ✅ |
| 1.4 | Modo LOCAL FREE: 100% funcional sin license key, sin cuenta, sin rate limit | ✅ |
| 1.5 | Human-in-the-loop: confirmación explícita antes de `sudo`, `rm -rf`, >10 clicks | ✅ |
| 1.6 | `skills.md` en `~/.pill.ai/skills.md` — gitignoreado, deduplicación semántica | ✅ |
| 1.7 | `machine_id` persistente en `~/.pill.ai/machine.id` (fingerprint robusto en Docker/VMs) | ✅ |
| 1.8 | One-click installers: `install.sh` (Linux/macOS) + `install.bat` (Windows) | ✅ |
| 1.9 | CLI: `pillai activate / deactivate / status / server / run` | ✅ |
| 1.10 | License server (FastAPI + SQLite) con Stripe webhook verificado | ✅ |
| 1.11 | `computer.*` namespace expandido: display, clipboard, files, vision (+ alias os, screen) | ✅ |
| 1.12 | Tests OI compat: `tests/test_oi_compatibility.py` — 30+ assertions, offline-safe | ✅ |
| 1.13 | **GitHub Actions CI** — ruff + pytest en push a main y PRs | ✅ |
| 1.14 | README completo con tabla de costos, "Local Free Forever", sección Contributing | ✅ |
| 1.15 | **Batch processing** — `BatchProcessor` + `pillai batch tasks.txt` | ✅ |
| 1.16 | **Context injection** — `ContextInjector`: skills relevantes + compactación de historial | ✅ |
| 1.17 | **`pillai run`** — demo interactivo guiado con 3 demos predefinidos + custom | ✅ |
| 1.18 | **`.github/PULL_REQUEST_TEMPLATE.md`** | ✅ |
| 1.19 | `safe_mode="off"` warnings en desktop y shell tools | ✅ |
| 1.20 | Deploy license server en Fly.io (1 máquina fija, SQLite persistente) | ⬜ |
| 1.21 | Tests adicionales: `test_licensing.py`, `test_graph.py`, `test_llm_router.py` | ⬜ |
| 1.22 | Página de precios `pill.ai/pricing` con Stripe Checkout | ⬜ |
| 1.23 | **Docker sandbox básico** para shell_agent (aislamiento del host) | ⬜ |
| 1.24 | **Memoria persistente entre sesiones** — historial de conversación + compactación semántica (tipo Claude Code) | ⬜ |
| 1.25 | **Context injection automático** — leer `CLAUDE.md` / `skills.md` al arrancar, inyectar contexto del proyecto sin que el usuario lo pida | ⬜ |
| 1.26 | **Plugin DAW / Ableton** — detectar proceso Ableton corriendo, leer archivos `.als` del proyecto activo, comandos específicos (tempo, pistas, plugins) | ⬜ |
| 1.27 | **Detección de ventana activa** — saber qué app tiene el foco antes de responder; enriquecer contexto automáticamente (Excel abierto → modo hoja de cálculo, Ableton → modo DAW) | ⬜ |

**Costo típico por tarea en Fase 1:**
```
$0.001 – $0.01 USD   (DeepSeek V4 Pro: $0.14/M tokens)
vs GPT-4o: $0.15 – $1.50   →  95-99% más barato
```

---

## Fase 2 — Plataforma robusta (2–6 meses)
**Objetivo:** Dashboard, auto-update, comunidad de skills, billing completo.

| # | Tarea | Prioridad |
|---|-------|----------|
| 2.1 | **Dashboard Streamlit** — historial de tareas, costos por sesión, gráfico de uso | Alta |
| 2.2 | **Auto-update** — `pillai update` comprueba y actualiza el paquete | Alta |
| 2.3 | **Marketplace de skills** — repositorio público de `skills.md` compartibles entre usuarios | Alta |
| 2.4 | **Modo servidor REST** — `POST /v1/task` para integraciones externas | Media |
| 2.5 | **Cron jobs nativos** — `pillai schedule "tarea" --cron "0 9 * * *"` | Media |
| 2.6 | **Soporte multi-sesión** — múltiples agentes en paralelo | Media |
| 2.7 | **Billing portal** — `pill.ai/billing` para ver facturas, actualizar tier | Alta |
| 2.8 | **Webhooks de licencia** — notificación automática al suspender/renovar | Alta |
| 2.9 | **SDK Python** — `pip install pill-ai` con API pública documentada y estable | Media |
| 2.10 | **Relay cloud** — batch processing de tareas largas en cloud | Alta |
| 2.11 | **Semantic memory compaction** — context-compactor integrado en historial largo | Media |
| 2.12 | **Docker sandbox avanzado** — gVisor + syscall filtering para shell_agent | Alta |
| 2.13 | **VSCode extension** (básica) — panel lateral con `pillai` integrado | Baja |

**Modelo de negocio en Fase 2:**

| Tier | Precio | Calls/día | Características |
|------|--------|-----------|----------------|
| **Free** | $0 | Ilimitado local | Todo el core. Sin relay cloud. |
| **Starter** | $9/mes | 1,000 relay | + API access + cron + relay cloud |
| **Pro** | $29/mes | 10,000 relay | + Multi-sesión + Skills marketplace |
| **Enterprise** | $199/mes | Ilimitado | + SLA + soporte + on-premise |

---

## Fase 3 — Autonomía total (6+ meses)
**Objetivo:** Cero dependencia de cloud si el usuario no quiere. Marketplace. Enterprise. Apache 2.0.

| # | Tarea |
|---|-------|
| 3.1 | **Ollama full local** — DeepSeek local, Llama 3 local → $0/tarea |
| 3.2 | **App móvil** (React Native) — controla el escritorio remotamente vía WebRTC |
| 3.3 | **Computer-use nativo macOS** — Accessibility API (sin pyautogui) |
| 3.4 | **Computer-use nativo Windows** — UI Automation API |
| 3.5 | **Multi-PC orquestación** — un supervisor controla N máquinas en paralelo |
| 3.6 | **Marketplace de agentes** — terceros publican agentes especializados (legal, finanzas, DevOps) |
| 3.7 | **Fine-tuning propio** — modelo compacto entrenado con interacciones anonimizadas |
| 3.8 | **JetBrains plugin** — pill.ai como herramienta IDE |
| 3.9 | **Enterprise on-premise** — despliegue en VPC sin llamadas externas |
| 3.10 | **→ Apache 2.0** — cambio automático de licencia el 1 de enero de 2028 |

---

## Comparativa de costos (mayo 2026)

| Tarea | GPT-4o | Claude 3.5 | **pill.ai** | Ahorro |
|-------|--------|------------|-------------|-------|
| Analizar PDF 50 págs | $0.45 | $0.38 | **$0.008** | 98% |
| Navegar web + extraer datos | $1.20 | $0.95 | **$0.015** | 99% |
| Escribir + ejecutar script Python | $0.80 | $0.65 | **$0.012** | 98% |
| Tarea de desktop (5 clics + forms) | $2.00 | $1.80 | **$0.025** | 99% |

> Basado en precios públicos mayo 2026. DeepSeek V4 Pro: $0.14/M input, $0.28/M output.

---

## Decisiones de arquitectura

### ¿Por qué API-compatible con Open Interpreter?
Permite que los usuarios que vengan de OI migren sin cambiar código. `interpreter.chat()`, `interpreter.computer.*`, `auto_run`, `safe_mode` — misma API, distintos internos (LangGraph + LiteLLM en vez del loop ReAct original).

### ¿Por qué LangGraph y no AutoGen/CrewAI?
Control explícito del flujo → predecible y debuggeable. StateGraph + conditional edges permite HITL nativo y loops con condición de salida. Menos magic, más control.

### ¿Por qué modo local gratis sin límite?
Viralidad. El usuario prueba gratis, confía en el producto, luego compra relay cloud cuando necesita escalar o no tiene API keys propias. El rate limit solo aplica a llamadas que pasan por nuestro relay.

### ¿Por qué BSL-1.1 y no MIT?
MIT permitiría que alguien forke y venda el mismo servicio sin contribuir. BSL-1.1 protege el negocio durante los primeros 2 años. La conversión automática a Apache 2.0 en 2028 mantiene la buena fe con la comunidad open-source a largo plazo.

### ¿Por qué SQLite + Fly.io con 1 máquina?
SQLite es suficiente para cientos de validaciones por segundo con 1 writer. Más simple que PostgreSQL. Si el volumen supera eso, migrar a Turso (SQLite distribuido) — el código del servidor no cambia.
