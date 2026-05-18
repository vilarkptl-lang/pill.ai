# pill.ai — UltraCheap Computer AI

> **Multi-agent computer-use AI that costs 95–99% less than GPT-4o.**  
> Controls your desktop, browser, and terminal. Powered by DeepSeek V4 Pro + Gemini Flash.

[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-orange.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-green.svg)](https://github.com/langchain-ai/langgraph)

---

## Install in 30 seconds

**Linux / macOS:**
```bash
curl -sSL https://get.pill.ai | bash
```

**Windows:**
```
https://get.pill.ai/install.bat
```

**From source (developers):**
```bash
git clone https://github.com/vilarkptl-lang/pill.ai
cd pill.ai
pip install -e ".[dashboard]"
playwright install chromium
```

---

## Quick Start

```bash
# Interactive chat
pillai

# One-shot task
pillai "open Chrome, go to gmail.com, and read the first unread email"

# Activate your license
pillai activate PILLAI-XXXX-XXXX-XXXX-XXXX

# Check status
pillai status
```

**Python API:**
```python
from interpreter import Interpreter

ai = Interpreter(license_key="PILLAI-XXXX-XXXX-XXXX-XXXX")

# Chat
ai.chat("take a screenshot and describe what you see")

# Direct tool use
ai.computer.browser.goto("https://example.com")
ai.computer.mouse.click(100, 200)
ai.computer.terminal.run("ls -la ~/Documents")
```

---

## What it can do

| Capability | How |
|-----------|-----|
| **Click anything on screen** | pyautogui (left, right, double, drag & drop) |
| **Type and use hotkeys** | pyautogui keyboard control |
| **Browse the web** | Playwright full browser |
| **Run terminal commands** | subprocess + sudo support |
| **See the screen** | Gemini Flash vision (screenshot analysis) |
| **Write & run code** | Python exec with Streamlit dashboards |
| **Remember skills** | Auto-updated `skills.md` |
| **Schedule tasks** | Cron integration (Fase 2) |

---

## Cost comparison (May 2026)

| Task | GPT-4o | Claude 3.5 | **pill.ai** | Savings |
|------|--------|------------|-------------|---------|
| Analyze 50-page PDF | $0.45 | $0.38 | **$0.008** | **98%** |
| Browse web + extract data | $1.20 | $0.95 | **$0.015** | **99%** |
| Write + run Python script | $0.80 | $0.65 | **$0.012** | **98%** |
| Desktop task (5 clicks + forms) | $2.00 | $1.80 | **$0.025** | **99%** |

> Routing: 90% DeepSeek V4 Pro ($0.14/M tokens) + Gemini Flash ($0.10/M tokens) + GPT-4o-mini fallback only.

---

## Multi-agent architecture

```
User Input
    │
    ▼
Supervisor Agent (DeepSeek V4 Pro)
    │  Routes to the right specialist
    ├──► Vision Agent      — Gemini Flash — analyzes screenshots
    ├──► Browser Agent     — Playwright   — web navigation & scraping
    ├──► Desktop Agent     — pyautogui    — GUI clicks, drag-drop
    ├──► Shell Agent       — subprocess   — terminal + sudo
    └──► Coder Agent       — Python exec  — code + dashboards
              │
              ▼
         Final answer + skills.md update
```

Built with **LangGraph StateGraph** — explicit control flow, no black boxes.

---

## Pricing

| Tier | Price | Daily calls | Features |
|------|-------|-------------|----------|
| **Free** | $0 | 100 | All core features. Service level not guaranteed. |
| **Starter** | $9/mo | 1,000 | + API access + cron jobs |
| **Pro** | $29/mo | 10,000 | + multi-session + skills marketplace |
| **Enterprise** | $199/mo | Unlimited | + SLA + dedicated support + on-premise |

**Get a license key:** [pill.ai/pricing](https://pill.ai/pricing)

---

## License key management

```bash
# Activate
pillai activate PILLAI-ABCD-EFGH-IJKL-MNOP

# Check tier and remaining calls
pillai status

# Deactivate this seat (frees up the license for another machine)
pillai deactivate
```

License keys are validated against `license.pill.ai`. The system works offline for up to 7 days using a cached validation. The service owner can:
- Revoke or suspend individual keys
- Disable the free tier globally
- Set per-key call limits and feature flags

---

## Self-hosting the license server (enterprise)

```bash
# Install server deps
pip install "pill-ai[server]"

# Set admin secret
export PILLAI_ADMIN_SECRET="your-secret-here"
export PILLAI_DB="/data/license.db"

# Start
pillai server
# or: uvicorn licensing.server:app --host 0.0.0.0 --port 8080

# Point clients to your server
export PILLAI_LICENSE_SERVER="https://your-license-server.com"
```

**Admin API:**
```bash
# Create key
curl -X POST https://your-server/admin/keys \
  -H "X-Admin-Secret: your-secret" \
  -d '{"email":"user@example.com","tier":"pro","daily_call_limit":10000}'

# Suspend a key
curl -X PATCH https://your-server/admin/keys/PILLAI-XXXX \
  -H "X-Admin-Secret: your-secret" \
  -d '{"status":"suspended","message":"Payment failed"}'

# Disable free tier globally
curl -X PUT https://your-server/admin/settings/free_tier_enabled \
  -H "X-Admin-Secret: your-secret" \
  -d '{"value":"false"}'

# View all keys
curl https://your-server/admin/keys -H "X-Admin-Secret: your-secret"
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PILLAI_LICENSE_KEY` | — | License key (alternative to `pillai activate`) |
| `PILLAI_LICENSE_SERVER` | `https://license.pill.ai` | License validation endpoint |
| `PILLAI_GRACE_DAYS` | `7` | Days to work offline after last validation |
| `PILLAI_CACHE_DIR` | `~/.pill.ai` | Local cache and config directory |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `OPENAI_API_KEY` | — | OpenAI API key (fallback only) |

---

## skills.md — auto-generated skill registry

Every time you complete a new type of task, pill.ai appends to `skills.md`:

```markdown
## Send daily email report
_Added: 2026-05-18_
Agent: coder_agent
Schedule: 0 8 * * *  (daily at 8am)

Reads sales CSV, generates HTML report, sends via SMTP.
```

You can also manually run: `pillai "update skills.md with what you know"`

---

## Fork policy and commercial use

This project is licensed under **BSL-1.1** (Business Source License 1.1).

- ✅ **Free** for personal and non-commercial use
- ✅ **Free** for developers evaluating the software
- ❌ **Requires a commercial license** for SaaS, hosted services, or products with >5 employees
- 🔄 **Converts to Apache 2.0** on January 1, 2028

If you fork this repository, the license terms still apply to your fork.  
Commercial licenses: [pill.ai/pricing](https://pill.ai/pricing)

---

## Roadmap

See [roadmap.md](roadmap.md) for the full plan.

**TL;DR:**
- **Now (0–3mo):** MVP + license system + multi-agent + one-click install
- **Soon (3–9mo):** Docker sandboxing, cron jobs, billing portal, relay-master cloud
- **Later (9–18mo):** Ollama local mode, mobile app, VSCode extension

---

## Contributing

Bug reports and feature requests: [GitHub Issues](https://github.com/vilarkptl-lang/pill.ai/issues)

Commercial contributions and integrations: hello@pill.ai
