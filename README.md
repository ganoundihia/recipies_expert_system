# NeSyChef

**A neuro-symbolic expert system for constraint-safe recipe recommendation.**
An LLM understands you. A rule engine decides. A verifier checks every word.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_19-TypeScript-61DAFB?logo=react&logoColor=black)
![Tests](https://img.shields.io/badge/tests-pytest_+_Hypothesis_+_Vitest-6E4AFF)
![License](https://img.shields.io/badge/license-MIT-green)

Tell NeSyChef what is in your kitchen, in English, French or Algerian Arabic. It recommends what to
bake, what to buy and how to substitute what you lack, and it shows the rules behind every decision.
Diets and allergies are enforced by the expert system, so a forbidden ingredient cannot be
recommended, and the language model's answer is checked against the engine's facts before you see it.

![Results: grounded answer, ranked recipes, evidence and rule trace](docs/screenshots/results.png)

## Why neuro-symbolic?

LLMs are great at language and bad at guarantees. On the benchmark below, a large model choosing
recipes on its own broke a diet or allergy constraint in more than one request out of four.
NeSyChef keeps the neural part where it shines and gives every decision to a symbolic engine:

| Concern | Who handles it | How it is made safe |
|---|---|---|
| Understanding the request (EN/FR/AR) | LLM (`gpt-oss-20b`) | Output validated against a controlled vocabulary; ingredients re-grounded on the knowledge base; literal matches override LLM mis-mappings |
| Diets and allergies | LLM **and** deterministic parser | Safety net: constraints found by either parser are always enforced (the LLM missed Darija words for sesame and peanuts during evaluation) |
| Prompt injection | Llama Prompt Guard 2 | Flagged input bypasses the LLM entirely (deterministic parser + template answer) |
| Constraints, substitutions, ranking | Expert system | A forbidden ingredient can only be obtained through an allowed substitute, otherwise the recipe is excluded, *by construction*; property-tested with Hypothesis |
| Writing the answer | LLM (`gpt-oss-120b`) | Receives only engine facts; a verifier rejects any ingredient or recipe not in the result and falls back to a template |

## Benchmark

<!-- BENCHMARK:START -->
40 requests with known ground truth (English, French, Arabic), models: `openai/gpt-oss-20b` (parsing), `openai/gpt-oss-120b` (writing and the LLM-only baseline). Reproduce with `python -m eval.run_eval`; results are also shown on the app's *Benchmark* page.

| Metric | LLM only | Rules only | Hybrid (NeSyChef) |
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

## Screenshots

| Backward-chaining proof | Arabic, right-to-left |
|---|---|
| ![Recipe page with the can_make proof tree](docs/screenshots/recipe-proof.png) | ![Arabic interface, Algerian pastries for Eid](docs/screenshots/arabic-rtl.png) |
| **Knowledge console** | **Benchmark page** |
| ![Mined candidates with impact preview](docs/screenshots/knowledge-console.png) | ![Benchmark results inside the app](docs/screenshots/benchmark.png) |

## Features

- **Expert system**: forward chaining with pattern variables and MYCIN certainty factors, goal-driven
  backward chaining (`can_make(recipe)` proof trees), hard constraints vs. soft preferences,
  quantity-aware pantry, serving scaling and a full explanation trace.
- **Substitution knowledge** with ratios, confidence, conditions and how-to notes (butter → oil at 80%,
  1 egg → 7 g flax + 45 ml water, dates → date paste...).
- **What-if and best purchase**: which single ingredient unlocks the most recipes.
- **Baking planner**: several bakes under a budget (DZD), buying whole packs and reusing leftovers.
- **Knowledge base**: 68 recipes (14 Algerian classics such as makrout, griwech, kalb el louz and
  baklawa, plus vegan, gluten-free and egg-free options), 60 ingredients with allergens, prices and
  pack sizes, 51 substitutions, 31 rules. Everything is localized in English, French and Arabic.
- **Knowledge console**: validated edits of rules and substitutions, **knowledge mining** from recipe
  data (substitution candidates; flavor association rules with support, confidence and lift),
  **impact preview** on 60 benchmark requests, approval workflow and audit log.
- **Corpus import** from RecipeNLG (2M recipes) to scale knowledge mining.
- **Any OpenAI-compatible LLM**: Groq by default; a local llama.cpp or Ollama server works by changing
  `LLM_BASE_URL`. Without a key the app still works with the deterministic parser.

## Architecture

```mermaid
flowchart LR
    U[User text<br/>EN / FR / AR] --> G{Prompt Guard}
    G -- flagged --> K[Keyword parser]
    G -- clean --> P[LLM parser]
    P --> R[Grounding + safety net<br/>vocabulary, KB matcher,<br/>deterministic constraints]
    K --> E
    R --> E[Expert system<br/>forward chaining + CF<br/>backward chaining<br/>constraints]
    KB[(Knowledge base<br/>SQLite / PostgreSQL)] --> E
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
  app/api/         public API, knowledge-console API, rate limiting
  app/scripts/     seed / reset the database, RecipeNLG import
  eval/            benchmark: LLM only vs rules only vs hybrid
  tests/           unit, API and property-based tests
frontend/          React 19 + TypeScript + Vite (assistant, recipe, planner, benchmark, console)
```

## Run it locally

**Docker**: API and frontend in one container.

```bash
docker build -t nesychef .
docker run -p 8000:8000 -e LLM_API_KEY=your_groq_key nesychef
```

Open http://localhost:8000. `docker compose up --build` runs the same image with PostgreSQL.

**Development**

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

## Deploy on Render

1. On [render.com](https://render.com), choose **New → Blueprint** and select this repository.
   `render.yaml` creates a free Docker web service.
2. When asked, paste your Groq key into `LLM_API_KEY`. `ADMIN_TOKEN` is generated for you: read it in
   the service's **Environment** tab to use the knowledge console.
3. Open the service URL. The free plan sleeps when idle, so the first request takes about a minute.

The knowledge base is re-seeded on every start (SQLite in the container). To keep console edits
across deploys, attach a PostgreSQL database and set `DATABASE_URL`.

## Production safeguards

- **Rate limiting**: natural-language requests are limited per client (`RATE_LIMIT_PER_MINUTE`, with
  `429` and `Retry-After`).
- **Daily LLM budget** (`DAILY_LLM_BUDGET`): once spent, the assistant keeps answering
  deterministically instead of failing, so a public demo can never run up the LLM bill.
- **Knowledge console**: protected by `X-Admin-Token`, compared in constant time. With
  `ENVIRONMENT=production` it stays disabled until the default token is changed.
- **Secrets** are read from the environment only; `.env` is git-ignored.
- **Static files** are served from the build folder only (path-traversal tested).

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_KEY` | empty | Key for the OpenAI-compatible endpoint; empty = deterministic mode |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Groq, or a local `llama.cpp` / Ollama server |
| `PARSE_MODEL` | `openai/gpt-oss-20b` | Request parsing and step translation |
| `NARRATE_MODEL` | `openai/gpt-oss-120b` | Answer writing |
| `GUARD_MODEL` | `meta-llama/llama-prompt-guard-2-86m` | Prompt-injection screening |
| `DATABASE_URL` | SQLite file | e.g. `postgresql://user:pass@host/db` |
| `ADMIN_TOKEN` | `change-me-admin` | Token for the knowledge console |
| `ENVIRONMENT` | `development` | `production` disables the console while the default token is used |
| `RATE_LIMIT_PER_MINUTE` | `10` | Natural-language requests per client per minute |
| `DAILY_LLM_BUDGET` | `300` | LLM-backed requests per day before falling back to deterministic answers |

## API

| Endpoint | Description |
|---|---|
| `POST /api/ask` | Natural-language request through the full neuro-symbolic pipeline |
| `POST /api/recommend` | Structured request, engine only (no LLM) |
| `POST /api/prove` | Backward-chaining proof tree for one recipe |
| `POST /api/what-if` | Recipes unlocked by adding ingredients |
| `POST /api/plan` | Multi-bake plan under a budget with a consolidated shopping list |
| `GET /api/recipes/{id}?lang=&servings=` | Recipe scaled to servings, steps translated and cached |
| `GET /api/meta`, `/api/health`, `/api/eval` | Vocabulary, status, benchmark results |
| `/api/admin/*` | Knowledge console (header `X-Admin-Token`) |

Interactive documentation: `/docs` on a running server.

## Tests and quality

```bash
cd backend && ruff check . && pytest            # 40 tests
cd frontend && npm run lint && npm run typecheck && npm test
```

The key safety test generates random pantries, diets and allergies and asserts that no recommendation
ever uses a forbidden ingredient. CI (GitHub Actions) runs linting, type checking, both test suites
and a Docker build on every push.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic 2 · pytest + Hypothesis · Ruff ·
React 19 · TypeScript · Vite · Vitest · Groq (gpt-oss, Llama Prompt Guard 2) · PostgreSQL / SQLite ·
Docker · GitHub Actions · Render

## License

[MIT](LICENSE)
