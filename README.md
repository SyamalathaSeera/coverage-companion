# Coverage Companion

An eligibility and benefits workspace built with FastAPI, vanilla HTML/CSS/JavaScript, LangGraph, and optional OpenAI and LangSmith integrations.

## Try it locally (Windows PowerShell)

```powershell
Set-Location C:\Users\Syamalatha\Desktop\Coverag_Companion
# Only create the virtual environment if it does not already exist:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Open http://127.0.0.1:8000/ (application), http://127.0.0.1:8000/docs (API), or http://127.0.0.1:8000/health (health check). Stop the server with Ctrl+C. Serve the frontend through FastAPI; opening index.html directly is unsupported. Use Python 3.13. No frontend build is needed.

1. Ask a member question, then switch between DEMO001, DEMO002, and DEMO003.
2. Choose **Uploaded benefits PDF** and upload `docs/synthetic-benefits.pdf`.
3. Ask “What is the deductible?” or “What is the prescription copay?” Expand a source to see its page and excerpt.
4. Ask about dental implants to see an unsupported-question response.
5. Remove the document when finished.

## Implemented and mocked

- Deterministic member answers use three fictional plan records plus twelve bundled synthetic service records. Examples include dental, prescriptions, vision, specialist consultations, urgent care, imaging, physical therapy, and laboratory testing. A local GoMask import adds records alongside the bundled service examples. Plan values and recorded status never use an LLM.
- Chat supports record summaries, cost breakdowns, provider/payer IDs, recorded dates, authorization requirements, term explanations, and grounded follow-up steps. Common variants such as "co-payment", "pre-approval", and "deductable" are recognized. After asking about a deductible, try "How much is left?" The browser sends only the preceding question as context, clears it on record/mode changes, and retains no server-side conversation. Answers show the specific response first, with expandable historical context. General definitions are labeled separately from record facts.
- PDF uploads accept text PDFs up to 5 MB and 20 pages, with errors for invalid, encrypted, empty, scanned, oversized, or excessive extracted text documents.
- Document mode retrieves page-preserving passages, quotes evidence, and abstains when there is no match. Lexical retrieval is intentionally conservative; it can miss paraphrases and split-page answers.
- A real compiled LangGraph routes member lookup versus document retrieval and answer generation.
- Without credentials, document answers are clearly labeled **extractive fallback**. They are matching passages, not synthesized interpretations.
- With OpenAI configured, `langchain-openai` selects verbatim answering quotes using structured output. The server rejects quotes not present in retrieved passages. This deliberately constrained LLM answer avoids free-form benefit claims. Quote validation guarantees textual provenance, not that a quote is complete or clinically/legally correct.
- Optional LangSmith summary traces omit questions, names, member IDs, filenames, excerpts, answers, and API keys. The graph and provider are never automatically traced, even if tracing environment variables are set.
- Sessions use a random HttpOnly, SameSite=Strict cookie. Each browser has one document in bounded server RAM. Documents expire 30 minutes after upload; access checks expiration immediately and a sweep removes expired records every minute. Removal, replacement, shutdown, and process restart discard them. No original PDF is retained after request processing. Tabs sharing cookies share a document; separate browsers do not.

Policy documents cannot establish current eligibility or guarantee payment. This demo has no authentication, real claims integration, OCR, database, conversation persistence, or production/HIPAA compliance claim. Use synthetic documents only. It is not medical, legal, or coverage advice.

## Optional configuration

GoMask synthetic service records are supported alongside the original demo members.
See [GoMask records and importing a full export](docs/GOMASK.md).

Copy `.env.example` to `.env` without overwriting existing configuration:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` on the backend, then restart the server:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Empty keeps fallback mode; a real key enables paid OpenAI requests for document questions with matches. |
| `OPENAI_MODEL` | Default `gpt-4.1-mini`; choose a model your account supports with structured output. |
| `LANGSMITH_TRACING` | `true` enables sanitized request summaries when a LangSmith key is present. |
| `LANGSMITH_API_KEY` | Optional LangSmith credential. |
| `LANGSMITH_PROJECT` | Summary trace project, default in example: `coverage-companion`. |
| `COOKIE_SECURE` | Set `true` on HTTPS hosting, `false` for local HTTP. |
| `APP_ORIGIN` | Hosted public origin, e.g. `https://your-service.onrender.com`, without a trailing slash. Empty uses the request origin locally. |

Keys stay on the backend and `.env` is Git-ignored. OpenAI receives only the question and retrieved passages, not the whole document. Provider calls have a 20-second timeout and no retries; failures or invalid quotes return a labeled local fallback. No keys are needed for the default demo. No paid provider check runs as part of tests.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evals.run
.\.venv\Scripts\python.exe -m pip check
node --check frontend/app.js
```

The tests mock provider calls and tracing. They cover member values, validation, PDF rejection, retrieval and citation pages, isolated sessions, expiry, removal, replacement, routing, body limits, provider failure, quote validation, and redacted telemetry. Offline evaluation checks eight synthetic examples against expected answer values, evidence support, page numbers, and found/abstain behavior. These are small regression checks, not a claim of general accuracy.

Optional, separate checks:

```powershell
# Makes a paid OpenAI call only if OPENAI_API_KEY is configured:
.\.venv\Scripts\python.exe -m scripts.live_smoke
# Creates a synthetic dataset and experiment in your LangSmith account:
.\.venv\Scripts\python.exe -m evals.run --langsmith
# Recreate the bundled synthetic PDF (requires dev dependencies):
.\.venv\Scripts\python.exe -m scripts.make_sample_pdf
```

`evals.run --langsmith` sends only the built-in synthetic dataset and evaluation outputs. It calls the actual LangSmith SDK's dataset and evaluation APIs. The target forces extractive mode and disables ordinary summary traces. OpenAI evaluation is not silently billed. Application traces remain redacted even for synthetic uploads.

See [docs/VERIFICATION.md](docs/VERIFICATION.md) for the actual checks performed and limitations.

## Structure and learning

See the [project walkthrough and LangSmith explanation](docs/PROJECT_GUIDE.md).
The eligibility worklist groups historical GoMask transactions into recorded exceptions,
authorization follow-up, and recorded active results. Rules include field-level reasons;
they do not predict claim denials or determine current eligibility.

Start with [docs/LEARNING_GUIDE.md](docs/LEARNING_GUIDE.md). It explains every source module, request flow, graph, retrieval, configuration, study order, and architecture questions.

Deployment instructions, Docker commands, Render settings, and single-worker constraints are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Nothing has been published, pushed, committed, or provisioned.
