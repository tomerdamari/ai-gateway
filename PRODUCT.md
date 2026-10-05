# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: IT / systems administrator** at a company that uses AI models. Works in the admin screen daily: creates users and API keys, sets team and personal budgets, watches security events, connects company documents.
- **Employees**: use the chat screen to ask questions of Claude, GPT or Gemini, optionally grounded in company documents. They want an answer fast and to know how much budget they have left.
- **Apps / bots**: call the gateway with an API key instead of the provider's key.
- The product is meant to be sold to other companies as well, so the people above work at customer companies, not only at the builder's.

## Product Purpose

One gateway that every AI request in a company passes through. It knows who is asking, what they may use, how much they and their team have spent this month, and records everything. Success: the administrator controls and explains AI spending and risk from one place, and employees get a safe chat without writing code.

## Positioning

Self-hosted on the customer's own server, no external dependencies (single Python process + SQLite). Combines in one tool: per-person and per-team monthly budgets with recommendations, three providers behind one key, company-document search with per-team access, sensitive-data masking (Israeli ID, credit cards, secrets) and security event logging. Hebrew-first (RTL).

## Operating Context

- Runs on the customer's server (Docker, or plain Python). Often reached only on the office network; HTTPS when a domain exists.
- Admin screen `/admin`: overview, users and keys, teams, knowledge sources, security, question log, change log.
- Chat screen `/`: employee picks a model and document sources, conversations are saved.
- Open-access mode (no chat login on the office network, people pick their name) is used during rollout.

## Capabilities and Constraints

- Providers and models: Claude (fast/smart), OpenAI (gpt-fast/gpt-smart), Gemini (gemini-fast/gemini-smart). Prices hardcoded, checked 2026-10-04.
- Monthly budgets reset on the 1st; warning at 80%, block at 100%; recommendation = max(month-end projection, last month) + 20%, rounded up to $5.
- Strict content-security policy: scripts only from the gateway's own files; no external fonts, scripts or CDNs.
- All prompts and answers are kept indefinitely (deliberate decision).
- Product name **"שער AI" is temporary**; the real name is undecided.
- Undecided: pricing and licensing for selling to other companies.

## Brand Commitments

- Hebrew UI, right-to-left. English only for model names, code and technical identifiers.
- The user asked for an AdminKit-style admin look (dark side menu, white top bar, flat white cards), bold menu text, dark readable body text, and full-width layout.

## Evidence on Hand

- Demo data only (`seed_demo.py`): 4 teams, 10 users, 45 days of synthetic usage, 3 sample document sources. No real customers, testimonials or metrics; none may be invented.

## Product Principles

1. Control without friction: every limit (budget, rate, access) is visible and adjustable from the admin screen in one or two clicks.
2. Explain the money: every number shown can be traced to who, which model and when.
3. Safe by default: sensitive data is masked and suspicious content is logged before anyone has to think about it.
4. Plain Hebrew: interfaces and messages are understandable by non-technical employees.

## Accessibility & Inclusion

Hebrew RTL throughout. Office staff of all technical levels use the chat; text must stay readable (the user explicitly asked for darker body text).
