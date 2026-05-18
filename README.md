# pill.ai — Ultra-Cheap Computer AI

[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-orange.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![CI](https://github.com/vilarkptl-lang/pill.ai/actions/workflows/ci.yml/badge.svg)](https://github.com/vilarkptl-lang/pill.ai/actions)
[![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-green.svg)](https://github.com/langchain-ai/langgraph)

> **Multi-agent computer-use AI. 95–99% cheaper than GPT-4o.**  
> Controls your desktop, browser, and terminal.  
> **No account required. No license key. Just run.**

<!-- demo placeholder -->
<!-- ![pill.ai demo](https://pill.ai/demo.gif) -->

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

| Capability | Tool |
|-----------|------|
| Click anything on screen | pyautogui |
| Type and use hotkeys | pyautogui |
| Browse the web, fill forms, scrape | Playwright |
| Run terminal commands + sudo | subprocess |
| Analyze screenshots, OCR | Gemini 2.0 Flash |
| Write and execute Python code | Python exec |
| Remember skills across sessions | `~/.pill.ai/skills.md` |

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

## Pricing (optional relay cloud)

**Local use is free forever.** You only pay if you want relay cloud features (no own API keys, hosted execution, team sharing).

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
| Default model | GPT-4o | DeepSeek V4 Pro (95% cheaper) |
| Human-in-the-loop | Inline confirmation | Explicit HITL graph node |
| Skills memory | None | `~/.pill.ai/skills.md` with semantic dedup |
| License | MIT | BSL-1.1 → Apache 2.0 (2028) |

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

Issues and PRs welcome: [github.com/vilarkptl-lang/pill.ai/issues](https://github.com/vilarkptl-lang/pill.ai/issues)

Commercial integrations: hello@pill.ai

---

## Roadmap

See [roadmap.md](roadmap.md) — TL;DR:
- **0–2 mo:** Open-source MVP, Docker sandbox, tests
- **2–6 mo:** Dashboard, auto-update, relay cloud, skills marketplace
- **6+ mo:** Ollama local ($0/task), mobile app, enterprise on-premise, Apache 2.0
