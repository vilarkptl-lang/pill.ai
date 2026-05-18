# pill.ai — Roadmap

> **Stack base:** Python 3.12 · LangGraph · Open Interpreter fork · LiteLLM · DeepSeek V4 Pro · Gemini Flash · Playwright · pyautogui · BSL-1.1 license

---

## Fase 1 — Corto plazo (0–3 meses)

### Objetivo: MVP estable con sistema de licencias operativo

| # | Tarea | Estado |
|---|-------|--------|
| 1.1 | Fork de Open Interpreter (`core.py`, `llm.py`, `browser.py`, `desktop.py`, `shell.py`) | ✅ |
| 1.2 | Sistema de licencias: client, server, activación, revocación | ✅ |
| 1.3 | LangGraph multi-agente: Supervisor → Vision → Browser → Desktop → Shell → Coder | ✅ |
| 1.4 | LiteLLM routing: DeepSeek V4 Pro (90%) + Gemini Flash (visión) + GPT-4o-mini (fallback) | ✅ |
| 1.5 | Instaladores one-click: `install.sh` (Linux/macOS) + `install.bat` (Windows) | ✅ |
| 1.6 | `skills.md` auto-generado por el coder agent | ✅ |
| 1.7 | CLI: `pillai activate`, `pillai status`, `pillai deactivate`, `pillai server` | ✅ |
| 1.8 | License Server (FastAPI + SQLite) con panel admin REST | ✅ |
| 1.9 | Despliegue del license server en producción (Fly.io / Railway) | ⬜ |
| 1.10 | Página de precios: `pill.ai/pricing` con Stripe | ⬜ |
| 1.11 | Integración relay-master: batch processing + semantic memory + caching | ⬜ pendiente archivos |
| 1.12 | Tests unitarios básicos (pytest) | ⬜ |
| 1.13 | GitHub Actions CI | ⬜ |

**Stack activo en Fase 1:**
```
Python 3.12+ ─► LiteLLM ─► DeepSeek V4 Pro ($0.14/M tokens)
                        ─► Gemini 2.0 Flash  ($0.10/M tokens)
                        └► GPT-4o-mini       ($0.15/M tokens, fallback)

LangGraph StateGraph ─► Supervisor ─► Vision Agent (Gemini)
                                  ─► Browser Agent (Playwright)
                                  ─► Desktop Agent (pyautogui)
                                  ─► Shell Agent (subprocess)
                                  └► Coder Agent (Python exec)
```

**Costo estimado por tarea típica:** $0.001 – $0.01 USD  
**Comparado con GPT-4o full:** $0.15 – $1.50 USD → **95% más barato**

---

## Fase 2 — Mediano plazo (3–9 meses)

### Objetivo: Plataforma robusta y monetización real

| # | Tarea | Prioridad |
|---|-------|-----------|
| 2.1 | **Sandboxing avanzado**: Docker containers per-task, sin acceso al host salvo permisos explícitos | Alta |
| 2.2 | **relay-master cloud**: integración opcional vía webhook para batch jobs en cloud | Alta |
| 2.3 | **Marketplace de skills**: repositorio público de `skills.md` compartibles | Alta |
| 2.4 | **Dashboard web** (Streamlit) con historial de tareas, costos por sesión, usage analytics | Media |
| 2.5 | **Modo servidor** (API REST): `POST /v1/task` para integraciones externas | Media |
| 2.6 | **Semantic memory compaction** (relay-master): compresión automática del contexto largo | Media |
| 2.7 | **Cron jobs nativos**: `pillai schedule "tarea X" --cron "0 9 * * *"` | Media |
| 2.8 | **Soporte multi-sesión**: múltiples agentes corriendo en paralelo | Baja |
| 2.9 | **Auto-update**: el instalador verifica y actualiza automáticamente | Media |
| 2.10 | **Billing dashboard**: portal en `pill.ai/billing` para ver uso, facturas, actualizar tier | Alta |
| 2.11 | **Webhooks de licencia**: notificación automática cuando una cuenta se suspende/renueva | Alta |
| 2.12 | **SDK Python**: `pip install pill-ai` con API pública documentada | Media |

**Modelo de negocio en Fase 2:**

| Tier | Precio | Llamadas/día | Características |
|------|--------|--------------|-----------------|
| Free | $0 | 100 | Todas las funciones básicas. Puede desactivarse. |
| Starter | $9/mes | 1,000 | + API access + cron jobs |
| Pro | $29/mes | 10,000 | + Multi-sesión + Skills marketplace |
| Enterprise | $199/mes | Ilimitado | + SLA + soporte dedicado + on-premise |

---

## Fase 3 — Largo plazo (9–18 meses)

### Objetivo: Autonomía total y expansión de plataforma

| # | Tarea |
|---|-------|
| 3.1 | **Soporte local completo con Ollama**: DeepSeek local, Gemini local → $0/tarea |
| 3.2 | **Versión móvil**: app React Native que controla el escritorio remotamente vía WebRTC |
| 3.3 | **Computer-use nativo en macOS**: integración con Accessibility API (sin pyautogui) |
| 3.4 | **Computer-use nativo en Windows**: integración con UI Automation |
| 3.5 | **Multi-PC orquestación**: un supervisor controla N máquinas en paralelo |
| 3.6 | **Marketplace de agentes**: terceros publican agentes especializados (legal, finanzas, etc.) |
| 3.7 | **Fine-tuning propio**: entrenar un modelo compacto con las interacciones anonimizadas |
| 3.8 | **Integración VSCode / JetBrains**: pill.ai como extension IDE |
| 3.9 | **Versión enterprise on-premise**: despliegue en VPC sin llamadas externas |
| 3.10 | **Cambio de licencia a Apache 2.0** en enero 2028 (per BSL Change Date) |

---

## Comparativa de costos (actualizada mayo 2026)

| Tarea | GPT-4o | Claude 3.5 | **pill.ai** | Ahorro |
|-------|--------|------------|-------------|--------|
| Analizar PDF 50 pág | $0.45 | $0.38 | **$0.008** | 98% |
| Navegar web + extraer datos | $1.20 | $0.95 | **$0.015** | 99% |
| Escribir + ejecutar script Python | $0.80 | $0.65 | **$0.012** | 98% |
| Tarea de desktop (5 clics + forms) | $2.00 | $1.80 | **$0.025** | 99% |

> Costos basados en precios públicos de mayo 2026. DeepSeek V4 Pro: $0.14/M input, $0.28/M output.

---

## Decisiones de arquitectura

### ¿Por qué BSL-1.1 y no MIT?
- MIT permitiría que cualquiera forke y venda el mismo producto sin pagar.
- BSL-1.1 permite uso personal/dev gratuito, pero requiere licencia comercial para SaaS/productos.
- Cambia automáticamente a Apache 2.0 en 2028, manteniendo la buena fe con la comunidad.
- Permite control total de cuentas, precios y servicio gratuito.

### ¿Por qué no alojar los pesos del modelo?
- Usamos APIs (LiteLLM) → sin infra de GPU propia → costos variables, no fijos.
- Cuando Ollama madure lo suficiente, Fase 3 añade modo local.

### ¿Por qué LangGraph y no AutoGen/CrewAI?
- LangGraph tiene control explícito del flujo → predecible, debuggeable.
- StateGraph permite loops con condiciones → esencial para computer-use.
- Mantenido por LangChain, comunidad enorme, updates frecuentes.
