# pill.ai — Autodiagnóstico del Sistema
> Generado automáticamente · 2026-05-21 · Rama: `claude/add-licensing-system-KsFAw`

---

## Tabla de contenidos
1. [Stack tecnológico](#1-stack-tecnológico)
2. [Árbol de agentes](#2-árbol-de-agentes)
3. [Árbol de documentos](#3-árbol-de-documentos)
4. [Fortalezas](#4-fortalezas)
5. [Problemas actuales](#5-problemas-actuales)
6. [Debilidades estructurales](#6-debilidades-estructurales)
7. [Áreas de oportunidad](#7-áreas-de-oportunidad)
8. [Propuestas de mejora](#8-propuestas-de-mejora)

---

## 1. Stack tecnológico

| Capa | Tecnología | Versión mín. | Propósito |
|------|-----------|-------------|----------|
| **Orquestación de agentes** | LangGraph | ≥ 0.2.0 | StateGraph multi-agente con nodos especializados |
| **Routing LLM** | LiteLLM | ≥ 1.40.0 | Abstracción multi-proveedor (DeepSeek, Gemini, GPT) |
| **Modelo principal** | DeepSeek V4 Pro | — | Razonamiento, código, routing (~$0.14/M tokens) |
| **Modelo de visión** | Gemini 2.0 Flash | — | Análisis de screenshots (~$0.10/M tokens) |
| **Modelo de fallback** | GPT-4o mini | — | Respaldo si fallan los otros |
| **Control de escritorio** | pyautogui + pygetwindow | ≥ 0.9.54 | Mouse, teclado, ventanas |
| **Navegador** | Playwright (sync) | ≥ 1.44.0 | Web scraping, formularios, automatización |
| **API del servidor** | FastAPI + Uvicorn | ≥ 0.111.0 | Servidor de licencias + relay LLM |
| **Base de datos** | SQLite (dev) / MySQL (prod) | SQLAlchemy ≥ 2.0 | Licencias, activaciones, uso |
| **UI de escritorio** | tkinter (overlay) + pystray | stdlib | Overlay flotante + ícono de bandeja |
| **Frontend avanzado** | Tauri + Svelte 5 + TypeScript | Rust | Orb (burbuja flotante nativa) |
| **Distribución** | PyInstaller | — | Binarios nativos: .exe, mac, linux |
| **CI/CD** | GitHub Actions | — | Tests + lint + build en 3 plataformas |
| **Licenciamiento** | Custom BSL-1.1 | — | → Apache 2.0 el 2028-01-01 |

### Modelos y costos vs. OpenInterpreter

| Métrica | OpenInterpreter | pill.ai | Ahorro |
|---------|----------------|---------|--------|
| Modelo default | GPT-4o | DeepSeek V4 Pro | **53× más barato** |
| Costo input | $5.00/M | $0.14/M | −97% |
| Costo output | $15.00/M | $0.28/M | −98% |
| Presupuesto por tarea | Sin límite | $0.50 (configurable) | Control de costos |

---

## 2. Árbol de agentes

```
Entrada del usuario
        │
        ▼
┌───────────────────────────────────┐
│   supervisor_node                 │
│   Modelo: DeepSeek V4 Pro         │
│   Decide qué especialista llamar  │
│   Itera máx. 8 veces              │
└──────┬────────────────────────────┘
       │
       ├──────────────────────────────────────────────────┐
       │                                                  │
       ▼                                                  ▼
┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ vision      │  │ browser     │  │ desktop      │  │ shell    │  │ coder    │
│ Gemini 2.0  │  │ Playwright  │  │ pyautogui    │  │ bash /   │  │ Python   │
│ Flash       │  │ (sync)      │  │ (click/type) │  │ PowerShell│ │ código   │
│             │  │             │  │              │  │          │  │          │
│ Analiza     │  │ Navega web  │  │ Control GUI  │  │ Comandos │  │ Scripts  │
│ screenshots │  │ scraping    │  │ drag-drop    │  │ archivos │  │ dashboards│
└──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └────┬─────┘  └────┬─────┘
       │                │                │               │              │
       │                │        ┌───────┘               │              │
       │                │        │   si acción peligrosa │              │
       │                │        ▼                       ▼              │
       │                │  ┌─────────────────────────────────┐          │
       │                │  │ human_approval_node (HITL)      │          │
       │                │  │ input() del usuario             │          │
       │                │  │ Approve → resume agente         │          │
       │                │  │ Deny → final                    │          │
       │                │  └─────────────────────────────────┘          │
       │                │                                               │
       └────────────────┴───────────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌────────────────┐
                              │ final_node     │
                              │ DeepSeek       │
                              │ Sintetiza      │
                              │ respuesta      │
                              └───────┬────────┘
                                      │
                                      ▼
                                     END
```

### Patrones peligrosos (activan HITL)

```
rm -rf · dd if=…of=/dev/ · mkfs · format · sudo passwd
chmod -R 777 · crontab -r · >/etc/ · shutdown · reboot · pkill -9
```

### Jerarquía de herramientas (computer.*)

```
computer
├── terminal / os      → ShellTool    (bash, PowerShell, Python)
├── browser            → BrowserTool  (Playwright sync)
├── desktop → mouse    → DesktopTool  (pyautogui)
├── desktop → keyboard → DesktopTool
├── display            → DisplayTool  (screenshot)
├── clipboard          → ClipboardTool
├── files              → FilesTool    (read/write/find)
└── vision             → VisionTool   (Gemini 2.0 Flash OCR/describe)
```

---

## 3. Árbol de documentos

```
pill.ai/
├── agents/
│   └── graph.py                ← LangGraph: nodos, routing, HITL
│
├── interpreter/
│   ├── core/core.py            ← Clase Interpreter (API OI-compatible)
│   ├── llm.py                  ← LLMRouter (LiteLLM + relay + budget)
│   ├── relay_router.py         ← Cliente relay (.exe → servidor)
│   ├── memory.py               ← Historial persistente (~/.pill.ai/sessions/)
│   ├── context_injector.py     ← Inyección de skills + compactación
│   ├── scheduler.py            ← Cron / triggers de eventos
│   ├── skills_compactor.py     ← Dedup semántico de skills.md
│   ├── batch.py                ← Ejecución multi-tarea paralela
│   ├── _hw_id.py               ← Fingerprint de hardware
│   ├── _entry.py               ← Punto de entrada del .exe
│   └── tools/
│       ├── shell.py            ← subprocess + HITL safety
│       ├── browser.py          ← Playwright wrapper
│       ├── desktop.py          ← pyautogui (mouse, teclado, screenshot)
│       ├── vision.py           ← Gemini 2.0 Flash (OCR, describe)
│       ├── files.py            ← I/O de archivos
│       ├── display.py          ← Screenshot de pantalla
│       └── clipboard.py        ← Copy/paste
│
├── licensing/
│   ├── models.py               ← LicenseInfo, LicenseTier, LicenseStatus
│   ├── server.py               ← FastAPI: /validate /relay /admin/* /webhooks/stripe
│   ├── client.py               ← Validación + caché AES offline
│   ├── activation.py           ← activate() / deactivate() / require_license()
│   ├── relay.py                ← relay_complete() (proxy LLM server-side)
│   └── requirements.txt        ← Deps del servidor
│
├── pill_ai/
│   ├── cli.py                  ← `pillai` CLI (activate/status/batch/server/orb)
│   ├── tray.py                 ← Ícono bandeja + hotkey Ctrl+Space
│   ├── overlay.py              ← Ventana flotante tkinter
│   ├── orb.py                  ← Backend FastAPI del Tauri Orb
│   ├── local_exec.py           ← Detección de intents locales (Ableton, etc.)
│   └── skills_recorder.py      ← "Recuerda esto como skill"
│
├── orb/                        ← Frontend Tauri + Svelte 5
│   ├── src/App.svelte
│   └── src-tauri/Cargo.toml
│
├── tests/
│   ├── test_graph.py           ← Tests de nodos LangGraph (router mockeado)
│   ├── test_llm_router.py      ← Tests de LLMRouter (litellm mockeado)
│   ├── test_licensing.py       ← Tests del servidor de licencias (SQLite in-memory)
│   └── test_oi_compatibility.py← Paridad de API con OpenInterpreter
│
├── installers/build_exe.py     ← Configuración PyInstaller
├── .github/workflows/
│   ├── ci.yml                  ← Lint + tests (Python 3.12, Ubuntu)
│   └── build.yml               ← Build .exe/.app/.bin (3 plataformas)
│
├── DIAGNOSTICO.md              ← Este documento
├── CLAUDE.md                   ← Notas del equipo + relay server
├── OI_DIFF.md                  ← Diferencias con Open Interpreter
├── PLAN.md                     ← Plan de implementación
└── roadmap.md                  ← Roadmap de features
```

---

## 4. Fortalezas

| # | Fortaleza | Impacto |
|---|-----------|---------|
| 1 | **Costos 53× más bajos que OpenInterpreter** (DeepSeek vs GPT-4o) | Alto |
| 2 | **API 100% compatible con OpenInterpreter** — cualquier código OI funciona sin cambios | Alto |
| 3 | **Arquitectura multi-agente clara** — LangGraph con nodos especializados y HITL explícito | Alto |
| 4 | **Distribución sin instalación** — .exe descargable, relay baked en binario | Alto |
| 5 | **Sistema de licencias completo** — tiers, grace period, caché offline, Stripe webhooks | Medio |
| 6 | **Memoria persistente** — skills.md con dedup semántico, historial por sesión | Medio |
| 7 | **CI/CD automatizado** — tests + lint + 3 binarios en cada push | Medio |
| 8 | **Seguridad HITL** — aprobación humana para comandos peligrosos, no inline | Medio |
| 9 | **Budget por tarea** — evita costos infinitos ($0.50 default, configurable) | Medio |
| 10 | **Tests offline** — todos los tests usan mocks, sin API keys en CI | Bajo |

---

## 5. Problemas actuales

### 5.1 🔴 CRÍTICO — Alucinación de resultados (resuelto parcialmente)

**Problema:** El agente describe búsquedas imaginarias en vez de ejecutar comandos reales.

**Ejemplo real:**
> Usuario: *"busca todas las carpetas que lleven el nombre Noela en toda la computadora"*
> pill.ai: *"No se encontraron carpetas coincidentes"* (falso negativo — el folder existe en `C:\Users\noela\OneDrive\Documentos\Noela\`)

**Causa raíz:**
- `_final_node` tenía prompt `"Summarize what was accomplished. Be concise."` — el LLM redactaba respuestas "educadas" ignorando el output real
- `_shell_node` usaba CMD (`dir /s`) en Windows en vez de PowerShell (`Get-ChildItem -Recurse`)
- El LLM envolvía comandos en bloques markdown (` ```powershell `) que el parser no strippeaba

**Fix aplicado (commit `eb4fcb5`):**
- `_final_node` ahora tiene 5 reglas explícitas anti-alucinación
- `_shell_node` detecta Windows vs Unix y usa `Get-ChildItem -Recurse -ErrorAction SilentlyContinue`
- Strip de markdown code fences en el comando generado

### 5.2 🔴 CRÍTICO — Binario Mac incompatible con Intel

**Problema:** `pillai-mac` compilado en Apple Silicon (M1) arroja `bad CPU type in executable` en Macs Intel.

**Causa raíz:** `macos-latest` en GitHub Actions = runner Apple Silicon desde 2024.

**Fix aplicado (commit `06e6f9f` + `50def11`):** Cambio a `macos-13` (Intel x86_64). Compatible en todas las Macs vía Rosetta.

### 5.3 🟡 IMPORTANTE — Servidor relay con código desactualizado

**Problema:** El servidor en `143.198.228.78:8181` retorna el error del código viejo (`"pillai.exe not yet uploaded to server"`). La nueva lógica (redirect a GitHub Releases) no está en producción.

**Causa:** El deploy via `/admin/deploy` no se puede verificar desde el agente (restricciones de red del ambiente cloud).

**Acción pendiente:** Verificar desde Mac con `curl http://143.198.228.78:8181/health` y hacer `systemctl restart pillai-relay` si no responde.

### 5.4 🟡 IMPORTANTE — Shell agent sin loop de refinamiento

**Problema:** Si el primer comando devuelve resultados vacíos o incorrectos, el agente va directo a `final` sin intentar un comando alternativo.

**Ejemplo:** Busca en `C:\Users\noela` pero no en `C:\Users\noela\OneDrive`, encuentra 0 resultados, termina.

**Causa:** El supervisor no analiza si el resultado fue "realmente vacío" vs "comando incorrecto".

### 5.5 🟡 IMPORTANTE — Cobertura de tests baja (~39%)

Módulos críticos con 0% de cobertura:
- `interpreter/scheduler.py` (0%)
- `licensing/relay.py` (0%)
- `interpreter/skills_compactor.py` (0%)
- `interpreter/batch.py` (no en cobertura CI)

---

## 6. Debilidades estructurales

| # | Debilidad | Severidad |
|---|-----------|-----------|
| 1 | **Sin logging estructurado** — solo `print()`, imposible depurar en producción | Alta |
| 2 | **Sin tests de integración** — solo unit tests; el grafo completo no se prueba end-to-end | Alta |
| 3 | **Relay URL baked en .exe** — cambiar servidor requiere recompilar y redistribuir | Media |
| 4 | **tkinter overlay limitado** — no soporta Markdown, imágenes, ni historial visual | Media |
| 5 | **Shell node genera un solo comando** — no itera si falla o devuelve vacío | Media |
| 6 | **Sin rate limiting en relay** — un cliente malicioso puede agotar la cuota del servidor | Media |
| 7 | **Sin observabilidad** — no hay tracing, métricas de latencia, ni alertas | Media |
| 8 | **Idioma inconsistente** — mezcla de español/inglés en mensajes de error | Baja |
| 9 | **Timeouts hardcodeados** — playwright 30s, relay 120s, subprocess 60s | Baja |
| 10 | **`dashboard/` vacío** — listado en pyproject.toml pero sin contenido | Baja |

---

## 7. Áreas de oportunidad

### Corto plazo (1-2 semanas)

1. **Loop de refinamiento en shell** — si el resultado está vacío o tiene error, el supervisor debería intentar un comando alternativo antes de ir a `final`
2. **Logging con `structlog`** — cada nodo del grafo loguea entrada/salida, facilita debugging remoto
3. **Tests e2e del grafo** — 3-5 escenarios reales con router mockeado pero grafo completo
4. **Deploy verificado** — confirmar que el servidor en producción corre el código nuevo

### Mediano plazo (1 mes)

5. **Overlay con historial** — mostrar la conversación completa, no solo la última respuesta
6. **Multi-comando en shell** — el agente puede ejecutar N comandos hasta resolver la tarea
7. **Configuración de relay URL en runtime** — sin recompilar el .exe
8. **Dashboard de uso** — el propietario ve llamadas/día por usuario desde el admin panel
9. **Code signing en Mac y Windows** — eliminar las advertencias de "app no verificada"

### Largo plazo (3 meses)

10. **Modelo de visión local** — Gemini tiene latencia; un modelo local (LLaVA) para screenshots sería más rápido
11. **Modo colaborativo** — múltiples agentes trabajando en paralelo en subtareas
12. **Plugin system** — permite añadir nuevas herramientas sin modificar el núcleo
13. **Versión iOS/Android** — relay mode ya funciona sin Python; solo falta la UI nativa

---

## 8. Propuestas de mejora

### 8.1 Shell con loop inteligente

```python
# En _supervisor_node: detectar "resultado vacío = reintento"
def _result_is_empty(output: str) -> bool:
    return not output.strip() or output.strip() in ("", "0", "exit code 0")

# En _route_from_supervisor:
if _result_is_empty(state.get("agent_output", "")) and state.get("iteration", 0) < 3:
    return "shell"  # reintentar con otro enfoque
```

### 8.2 Logging estructurado (3 líneas por nodo)

```python
import logging
log = logging.getLogger("pill.ai.graph")

def _shell_node(state, router):
    log.info("shell_node.start", extra={"task": state["task"][:100], "iteration": state["iteration"]})
    # ... lógica ...
    log.info("shell_node.done", extra={"command": command, "exit_code": result["returncode"]})
```

### 8.3 Overlay con historial scrollable

```python
# En overlay.py: reemplazar Text widget simple por ScrolledText con markdown básico
from tkinter.scrolledtext import ScrolledText

self._history = ScrolledText(self._frame, height=15, wrap="word", state="disabled")
# Renderizar respuestas con colores: [shell] en azul, [error] en rojo
```

### 8.4 Configuración de relay en runtime

```python
# En relay_router.py: leer de ~/.pill.ai/config.json si existe
def _load_baked_url():
    config = Path.home() / ".pill.ai" / "config.json"
    if config.exists():
        return json.loads(config.read_text()).get("relay_url")
    # fallback a URL baked en binario
    ...
```

### 8.5 Tests e2e del grafo completo

```python
# tests/test_graph_e2e.py
def test_file_search_windows(mock_router_with_shell):
    """Simula búsqueda de archivos — verifica que el shell node ejecuta un comando real."""
    mock_router_with_shell.complete.side_effect = [
        "shell",           # supervisor → shell
        "Get-ChildItem -Path C:\\ -Recurse -ErrorAction SilentlyContinue -Filter '*noela*'",
        "final",           # supervisor → final
        "Encontré 3 carpetas: ...",  # final
    ]
    result = graph.invoke({"task": "busca carpetas Noela", "safe_mode": "off", ...})
    assert "Get-ChildItem" in mock_router_with_shell.complete.call_args_list[1][0][0]
```

---

## Resumen ejecutivo

| Dimensión | Estado | Tendencia |
|-----------|--------|-----------|
| **Funcionalidad core** | ✅ Funcionando | ↑ Mejorando |
| **Calidad de respuestas** | ⚠️ Alucinaciones parcialmente resueltas | ↑ |
| **Distribución** | ✅ Binarios en 3 plataformas | ↑ |
| **Licenciamiento** | ✅ Completo (tiers, Stripe, caché) | → Estable |
| **Costos** | ✅ 53× más barato que OI | → Estable |
| **Observabilidad** | ❌ Sin logging ni tracing | ↓ Deuda técnica |
| **Test coverage** | ⚠️ ~39% (solo unit) | → |
| **Producción** | ⚠️ Servidor desactualizado | ↑ Pendiente deploy |

**Prioridad inmediata:** (1) Verificar deploy del servidor, (2) probar binario Mac Intel en la Mac de María, (3) implementar loop de refinamiento en shell agent.
