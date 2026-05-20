# pill.ai — Ultra-Cheap Computer AI

[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-orange.svg)](LICENSE)
[![Local Free Forever](https://img.shields.io/badge/local%20use-free%20forever-brightgreen.svg)](#pricing-optional-relay-cloud)
[![OI Compatible](https://img.shields.io/badge/API-Open%20Interpreter%20compatible-blue.svg)](OI_DIFF.md)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![CI](https://github.com/vilarkptl-lang/pill.ai/actions/workflows/ci.yml/badge.svg)](https://github.com/vilarkptl-lang/pill.ai/actions)
[![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-green.svg)](https://github.com/langchain-ai/langgraph)

> **Multi-agent computer-use AI. 95–99% cheaper than GPT-4o.**  
> Controls your desktop, browser, and terminal.  
> **No account required. No license key. Just run.**

<!-- demo placeholder -->
<!-- ![pill.ai demo](https://pill.ai/demo.gif) -->

---

## Pill Orb — Interfaz flotante

El **Orb** es una burbuja translúcida siempre visible en tu escritorio (60 px, glassmorphism). Un clic la expande a un chat minimalista. No requiere abrir ninguna app.

```
┌─────────────────────────────────────────┐
│  pill.ai                              ✕ │   ← drag para mover
├─────────────────────────────────────────┤
│                                         │
│  ¿En qué puedo ayudarte?               │
│                                         │
│            [usuario]  busca mis docs ▶  │
│  ◀ Encontré 12 archivos en ~/Documents  │
│                                         │
├─────────────────────────────────────────┤
│  Escribe algo…                       ↑  │
└─────────────────────────────────────────┘
```

**Requisitos:** Rust + Node 18+ (para compilar). Python ya instalado.

**Modo desarrollo (dos terminales):**
```bash
# Terminal 1 — backend Python
export PILLAI_RELAY_URL=http://143.198.228.78:8181
python -m pill_ai.orb

# Terminal 2 — frontend Tauri
cd orb
npm install
npm run tauri dev
```

**Modo producción (un solo comando):**
```bash
# 1. Compilar el binario Tauri (una sola vez)
cd orb && npm install && npm run tauri build
cd ..

# 2. Correr
export PILLAI_RELAY_URL=http://143.198.228.78:8181
pillai orb
```

**Stack del Orb:**
- Frontend: Svelte 5 (runes) + Tauri 2
- Ventana: transparente, sin decoraciones, always-on-top
- Backend: `pill_ai/orb.py` (FastAPI en localhost:7842)
- Comunicación: `invoke('chat', {message})` → Rust → HTTP → Python → relay

---

## Install in 30 seconds

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/vilarkptl-lang/pill.ai/main/installers/install.sh | bash
```

**Windows:**
```
curl -O https://raw.githubusercontent.com/vilarkptl-lang/pill.ai/main/installers/install.bat && install.bat
```

**pip (developers):**
```bash
pip install pill-ai
playwright install chromium
```

**From source:**
```bash
git clone https://github.com/vilarkptl-lang/pill.ai
cd pill.ai && pip install -e . && playwright install chromium
```

---

## Quick start — no account needed

```bash
# Interactive mode
pillai

# One-shot task
pillai "take a screenshot and describe what you see"
pillai "open Chrome, go to news.ycombinator.com, summarize top 5 stories"
pillai "find all PDF files in ~/Downloads and list their sizes"
```

**Python API** (API-compatible with [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter)):
```python
from interpreter import Interpreter

ai = Interpreter()   # no license key required
ai.chat("open a browser, go to github.com, and tell me the trending repos")
ai.chat("write a Python script that downloads my emails as CSV")

# Direct tool access
ai.computer.browser.goto("https://example.com")
ai.computer.mouse.click(100, 200)
ai.computer.terminal.run("ls -la ~/Documents")
```

---

## What it can do

| Capability | `computer.*` module | Tool |
|-----------|-------------------|------|
| Click anything on screen | `computer.mouse` | pyautogui |
| Type and use hotkeys | `computer.keyboard` | pyautogui |
| Browse the web, fill forms, scrape | `computer.browser` | Playwright |
| Run terminal commands + sudo | `computer.terminal` | subprocess |
| Read screen size + capture display | `computer.display` | pyautogui |
| Copy/paste clipboard | `computer.clipboard` | pyperclip |
| Read/write/find files | `computer.files` | pathlib |
| Analyze screenshots, OCR | `computer.vision` | Gemini 2.0 Flash |
| Write and execute Python code | coder agent | Python exec |
| Remember skills across sessions | — | `~/.pill.ai/skills.md` |

**Human-in-the-loop safety:** pill.ai asks for confirmation before `sudo`, `rm -rf`, or any destructive action. You can set `safe_mode="off"` to disable.

---

## Cost comparison (May 2026)

| Task | GPT-4o | Claude 3.5 | **pill.ai** | Savings |
|------|--------|------------|-------------|---------|
| Analyze 50-page PDF | $0.45 | $0.38 | **$0.008** | **98%** |
| Browse web + extract data | $1.20 | $0.95 | **$0.015** | **99%** |
| Write + run Python script | $0.80 | $0.65 | **$0.012** | **98%** |
| Desktop task (5 clicks + forms) | $2.00 | $1.80 | **$0.025** | **99%** |

> **Routing:** 90% DeepSeek V4 Pro ($0.14/M) · 10% Gemini 2.0 Flash ($0.10/M) · fallback GPT-4o-mini  
> You bring your own API keys — no markup, no hidden fees.

---

## Architecture

```
User Input
    │
    ▼
Supervisor Agent  (DeepSeek V4 Pro — routes + reasons)
    │
    ├──► Vision Agent    — Gemini 2.0 Flash — screenshot analysis
    ├──► Browser Agent   — Playwright       — web navigation
    ├──► Desktop Agent   — pyautogui        — GUI clicks, drag-drop
    ├──► Shell Agent     — subprocess       — terminal + sudo
    │         │
    │    [Human approval? ──► yes/no]
    │
    └──► Coder Agent     — Python exec      — code + dashboards
              │
              ▼
         ~/.pill.ai/skills.md  (auto-updated, semantic dedup)
```

Built with **LangGraph StateGraph** — explicit routing, no black boxes, human-in-the-loop at every dangerous step.

---

## Environment variables

You need at least one LLM API key:

```bash
export DEEPSEEK_API_KEY="sk-..."     # main model — get at platform.deepseek.com
export GEMINI_API_KEY="AI..."        # vision — get at aistudio.google.com (free tier)
export OPENAI_API_KEY="sk-..."       # fallback only — optional
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (main model) |
| `GEMINI_API_KEY` | — | Google Gemini API key (vision) |
| `OPENAI_API_KEY` | — | OpenAI API key (fallback, optional) |
| `PILLAI_LICENSE_KEY` | — | Optional relay license key |
| `PILLAI_LICENSE_SERVER` | `https://license.pill.ai` | License server URL |
| `PILLAI_SAFE_MODE` | `ask` | `ask` / `off` / `auto` |

---

## skills.md — auto-generated skill registry

Every time you complete a new type of task, pill.ai appends to `~/.pill.ai/skills.md`.  
Duplicate or semantically similar skills are merged automatically.

```markdown
## Send daily email report
_Added: 2026-05-18_

Task: read sales CSV, generate HTML report, send via SMTP
python
import smtplib, csv, datetime
...
```

---

## Local Free Forever + Relay Cloud (optional)

**The core is 100% free, forever.** No account, no rate limit, no expiry.  
You only pay for **relay cloud** — hosted execution without your own API keys, team sharing, and cron jobs.

```
Local use (your API keys)   →  FREE forever. All agents. All features. No limit.
Relay cloud (our API keys)  →  Paid tiers. Optional. You bring nothing.
```

**FAQ:**
- _Do I need to sign up?_ No. Run `pillai` and go.
- _Will local mode ever be paywalled?_ No. It's in the license (BSL-1.1 → Apache 2.0 in 2028).
- _What's the catch?_ You supply API keys (DeepSeek at $0.14/M is essentially free).

## Pricing (optional relay cloud)

| Tier | Price | Relay calls/day | Extras |
|------|-------|-----------------|--------|
| **Free** | $0 | Unlimited local | All core features, your own API keys |
| **Starter** | $9/mo | 1,000 | Hosted relay + cron jobs + API |
| **Pro** | $29/mo | 10,000 | Multi-session + skills marketplace |
| **Enterprise** | $199/mo | Unlimited | SLA + dedicated support + on-premise |

[Get a relay license →](https://pill.ai/pricing)

---

## Inspired by Open Interpreter

pill.ai implements the same public API as [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) (`chat()`, `reset()`, `computer.*`, `safe_mode`) so existing OI users can migrate without changing code.

**What's different under the hood:**

| | Open Interpreter | pill.ai |
|--|-----------------|---------|
| Agent loop | Single ReAct loop | LangGraph multi-agent StateGraph |
| LLM layer | Custom classes | LiteLLM (multi-provider routing) |
| Default model | GPT-4o ($15/M) | DeepSeek V4 Pro ($0.28/M) — **53x cheaper** |
| Vision model | GPT-4V | Gemini 2.0 Flash — 5x cheaper |
| Human-in-the-loop | Inline confirmation | Explicit HITL graph node |
| `computer.*` modules | 15 | 8 implemented, 6 in Phase 2 |
| Skills memory | None | `~/.pill.ai/skills.md` with semantic dedup |
| Singleton import | Eager (network call) | Lazy proxy (no cost on `import`) |
| License | MIT | BSL-1.1 → Apache 2.0 (2028) |
| Full diff | — | [OI_DIFF.md](OI_DIFF.md) |

---

## License

**BSL-1.1** (Business Source License 1.1)

- ✅ Free for personal and non-commercial use
- ✅ Free for developers and evaluation
- ❌ Requires a commercial license for SaaS/hosted products with >5 employees
- 🔄 Converts to **Apache 2.0 on January 1, 2028**

See [LICENSE](LICENSE) for full terms.

---

## Contributing

Issues and PRs welcome.

**Good first contributions:**
- Add a new `computer.*` sub-module (mail, sms, calendar — see `OI_DIFF.md`)
- Write tests: `tests/test_licensing.py`, `tests/test_graph.py`, `tests/test_llm_router.py`
- Improve the Docker sandbox for `shell_agent`
- Port an OI language runner (Ruby, JS, R) to `interpreter/tools/`

**Setup:**
```bash
git clone https://github.com/vilarkptl-lang/pill.ai
cd pill.ai
pip install -e ".[dev]"
playwright install chromium
pytest tests/ -v          # run tests
ruff check . --select E,F,W --ignore E501   # lint
```

**PR guidelines:**
- One logical change per PR
- `safe_mode` warnings must stay in desktop/shell tools
- No secrets committed — use `.env` (gitignored)
- Tests for new features preferred

Issues: [github.com/vilarkptl-lang/pill.ai/issues](https://github.com/vilarkptl-lang/pill.ai/issues)  
Commercial integrations: hello@pill.ai

---

## Roadmap

See [roadmap.md](roadmap.md) — TL;DR:
- **0–2 mo:** Open-source MVP, Docker sandbox, tests
- **2–6 mo:** Dashboard, auto-update, relay cloud, skills marketplace
- **6+ mo:** Ollama local ($0/task), mobile app, enterprise on-premise, Apache 2.0
