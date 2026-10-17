# Pantry Chef: a hybrid AI baking assistant

**An LLM understands you. A rule-based expert system decides.**

Tell Pantry Chef what is in your kitchen, in English, French or Algerian Arabic, and it recommends
what to bake, what to buy and how to substitute what you lack. Diets and allergies are enforced by
the expert system, so a forbidden ingredient can never be recommended, and every sentence the
language model writes is checked against the engine's facts before you see it.

> *"I have semolina, smen, dates and orange blossom water, I want traditional sweets for Eid"*
> → **Makrout**: buy cinnamon, oil and honey; use your fine semolina instead of medium semolina,
> and steam and blend your dates into paste. Here is the rule trace that led there.

## Why hybrid?

LLMs are great at language and bad at guarantees. On the same benchmark requests, a large model
choosing recipes by itself breaks diet and allergy constraints and invents shopping lists. Pantry Chef
keeps the LLM where it shines, understanding messy multilingual requests and writing friendly
answers, and gives every decision to a transparent rule engine:

| Concern | Who handles it | How it is made safe |
|---|---|---|
| Understanding the request (EN/FR/AR) | LLM (`gpt-oss-20b`) | Output validated against a controlled vocabulary; each ingredient re-grounded on the knowledge base; literal matches override LLM mis-mappings |
| Prompt injection | Llama Prompt Guard 2 | Flagged input bypasses the LLM entirely (deterministic parser + template answer) |
| Constraints, substitutions, ranking | Expert system | Forbidden ingredients can only be obtained through an allowed substitute, otherwise the recipe is excluded, *by construction*; property-tested with Hypothesis |
| Writing the answer | LLM (`gpt-oss-120b`) | Receives only engine facts; a verifier rejects any ingredient or recipe not in the result and falls back to a template |

## Benchmark

<!-- BENCHMARK:START -->
40 requests with known ground truth (English, French, Arabic), models: `openai/gpt-oss-20b` (parsing), `openai/gpt-oss-120b` (writing and the LLM-only baseline). Reproduce with `python -m eval.run_eval`; results are also shown on the app's *Benchmark* page.

| Metric | LLM only | Rules only | Hybrid (Pantry Chef) |
|---|---:|---:|---:|
| Diet / allergy violations | 28.1% | **0.0%** | **0.0%** |
| Invented recipes | **0.0%** | **0.0%** | **0.0%** |
| Honest shopping list | 28.1% | 75.0% | **92.5%** |
| Craving satisfied | **78.6%** | 68.6% | 60.0% |
| Pantry extraction F1 | n/a | 0.954 | **0.976** |
| Constraint recall | n/a | 96.9% | **100.0%** |
| Ungrounded LLM text caught | n/a | n/a | 2.5% |
| Errors | 20.0% | **0.0%** | **0.0%** |
| Latency p50 | 2.1 s | **23 ms** | 2.0 s |
| Latency p95 | 4.1 s | **82 ms** | 2.9 s |

- Cases are synthetic requests with known ground truth, rendered in English, French and Arabic (seeded, reproducible).
- LLM only receives the full catalog with ingredient lists and must respect diets itself; its declared substitutions are honored when judging.
- Rules only uses the deterministic keyword parser; hybrid uses the LLM for parsing and narration, the expert system for every decision.
- Shopping-list accuracy compares declared missing items with what the user truly lacks, so parsing mistakes are penalized.
- Latencies exclude the backoff imposed by Groq's free-tier rate limits (measured and stored separately as throttle_wait_ms).
- LLM only sends the whole catalog (about 3k tokens) per request, so on Groq's free tier part of its requests exhausted the rate limit even after retries; its metrics cover the requests that completed.
<!-- BENCHMARK:END -->

## Features

- **Natural-language assistant** in English, French and Arabic (right-to-left UI), or a structured ingredient picker.
- **Real expert system**: forward chaining with pattern variables and MYCIN certainty factors, goal-driven
  backward chaining (`can_make(recipe)` proof trees), hard constraints vs. soft preferences, quantity-aware
  pantry, serving scaling, and a full explanation trace.
- **Substitution knowledge** with ratios, confidence, conditions and how-to notes (butter → oil at 80%,
  1 egg → 7 g flax + 45 ml water, dates → date paste...).
- **What-if and best purchase**: which single ingredient unlocks the most recipes.
- **Baking planner**: several bakes under a budget (DZD), buying whole packs and reusing leftovers.
- **68 recipes**, including 14 Algerian classics (makrout, griwech, kalb el louz, baklawa, mchewek...),
  plus vegan, gluten-free and egg-free options; 60 ingredients with allergens, prices and pack sizes.
- **Knowledge console** (admin): edit rules and substitutions with validation, **mine new knowledge**
  from recipe data (substitution candidates, flavor association rules with support, confidence and lift),
  **preview the impact** of a change on 60 benchmark requests, approve or reject, full audit log.
- **Corpus import** from RecipeNLG (2M recipes) to scale knowledge mining.
- **Any OpenAI-compatible LLM**: Groq by default; a local llama.cpp or Ollama server works by changing
  `LLM_BASE_URL`. Without any key the app still works with the deterministic parser.

## Architecture

```mermaid
flowchart LR
    U[User text<br/>EN / FR / AR] --> G{Prompt Guard}
    G -- flagged --> K[Keyword parser]
    G -- clean --> P[LLM parser]
    P --> R[Grounding:<br/>vocabulary + KB matcher]
    K --> E
    R --> E[Expert system<br/>forward chaining + CF<br/>backward chaining<br/>constraints]
    KB[(Knowledge base<br/>PostgreSQL / SQLite)] --> E
    E --> N[LLM narrator]
    N --> V{Verifier}
    V -- grounded --> A[Answer + cards + rule trace]
    V -- ungrounded --> T[Template answer] --> A
    X[Knowledge console] -- edit / mine / approve --> KB
```

```
backend/
  app/kb/          knowledge base: models, JSON data, multilingual matcher, labels
  app/engine/      inference (forward chaining, CF), reasoner (constraints, substitutions,
                   backward chaining, scoring), planner, mining, benchmark requests
  app/llm/         OpenAI-compatible client, prompt guard, parser, narrator + verifier, translator
  app/api/         public API and admin (knowledge console) API
  app/scripts/     seed / reset the database, RecipeNLG import
  eval/            benchmark: LLM only vs rules only vs hybrid
  tests/           unit, API and property-based tests
frontend/          React 19 + TypeScript + Vite (assistant, recipe, planner, benchmark, console)
```

## Run it

**Docker (recommended)**: API, frontend and PostgreSQL.

```bash
LLM_API_KEY=your_groq_key docker compose up --build
```

Open http://localhost:8000.

**Local development**

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env                              # then add your LLM_API_KEY
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev                                       # http://localhost:5173, proxies /api to :8000
```

The database is seeded from `backend/app/kb/data/*.json` on first start. After editing those files,
run `python -m app.scripts.seed --reset` (this also discards edits made in the console).

**Deploy**: `render.yaml` deploys the Docker image and a PostgreSQL database on Render
(New → Blueprint), then set `LLM_API_KEY`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_KEY` | empty | Key for the OpenAI-compatible endpoint; empty = no LLM, deterministic mode |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Groq, or a local `llama.cpp` / Ollama server |
| `PARSE_MODEL` | `openai/gpt-oss-20b` | Request parsing and step translation |
| `NARRATE_MODEL` | `openai/gpt-oss-120b` | Answer writing |
| `GUARD_MODEL` | `meta-llama/llama-prompt-guard-2-86m` | Prompt-injection screening |
| `DATABASE_URL` | SQLite file in `backend/` | e.g. `postgresql+psycopg://user:pass@host/db` |
| `ADMIN_TOKEN` | `change-me-admin` | Token for the knowledge console |

## API

| Endpoint | Description |
|---|---|
| `POST /api/ask` | Natural-language request through the full hybrid pipeline |
| `POST /api/recommend` | Structured request, engine only (no LLM) |
| `POST /api/prove` | Backward-chaining proof tree for one recipe |
| `POST /api/what-if` | Recipes unlocked by adding ingredients |
| `POST /api/plan` | Multi-bake plan under a budget with a consolidated shopping list |
| `GET /api/recipes/{id}?lang=&servings=` | Recipe scaled to servings, steps translated and cached |
| `GET /api/meta`, `/api/health`, `/api/eval` | Vocabulary, status, benchmark results |
| `/api/admin/*` | Knowledge console (header `X-Admin-Token`) |

Interactive documentation: http://localhost:8000/docs.

## Tests

```bash
cd backend && pytest            # inference, reasoner, safety property, parsing, narration verifier, API
cd frontend && npm test         # UI flows (ask, RTL), explanation widgets
```

The key safety test generates hundreds of random pantries, diets and allergies and asserts that no
recommendation ever uses a forbidden ingredient.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic 2 · pytest + Hypothesis · Ruff ·
React 19 · TypeScript · Vite · Vitest · Groq (gpt-oss, Llama Prompt Guard 2) · PostgreSQL · Docker · GitHub Actions
