# Learning guide

## 1. Start here

Coverage Companion demonstrates how a browser, Python API, explicit workflow, document retrieval, and optional language model fit together. It includes three fictional members plus locally imported GoMask synthetic service transactions. The member IDs choose demo records; they are not authentication. Uploaded policy text is separate evidence and cannot change a member record or prove live eligibility.

Start with [the project walkthrough](PROJECT_GUIDE.md) for the feature overview and
an exact explanation of LangSmith. `backend/gomask.py` validates imported transactions
and produces service-specific answers. `backend/operations.py` builds the review
worklist from recorded status, response, and authorization fields. `/members` and
`/operations` drive the selector and dashboard; these do not call an LLM.

Suggested study order:

1. `backend/data/members.json`: inspect the three small fictional records.
2. `backend/members.py`: understand deterministic lookup and supported facts.
3. `frontend/index.html`, then `frontend/app.js`: follow controls, fetch requests, and safe rendering.
4. `backend/main.py`: follow API validation, cookies, upload, and static serving.
5. `backend/documents.py`, `backend/storage.py`, then `backend/retrieval.py`.
6. `backend/workflow.py`: connect these components through LangGraph.
7. `backend/llm.py` and `backend/observability.py`: see the optional external integrations.
8. `tests/test_app.py`, `evals/dataset.json`, and `evals/run.py`.
9. `Dockerfile`, `requirements-lock.txt`, and `docs/DEPLOYMENT.md`.

## 2. File map

| File | Purpose |
| --- | --- |
| `backend/main.py` | FastAPI application, lifespan cleanup, body limit, security headers/origin checks, request model, API routes, frontend mount. Loads `.env`. |
| `backend/members.py` | Loads JSON, normalizes IDs, rejects unknown members, creates deterministic sample answers. |
| `backend/data/members.json` | Alex, Jordan, Taylor and their fictional plan facts. |
| `backend/documents.py` | Uses pypdf to extract page text and enforce file/page/text limits. |
| `backend/storage.py` | Lock-protected RAM store, random session tokens, capacity, absolute expiry, replacement, removal. |
| `backend/retrieval.py` | Tokenization, small alias map, page-local overlapping passages, conservative lexical matching. |
| `backend/workflow.py` | Typed state, three LangGraph nodes, explicit mode routing, answer assembly, provider fallback. |
| `backend/llm.py` | LangChain ChatOpenAI, structured quote schema, untrusted-content instructions, substring verification. |
| `backend/observability.py` | Optional LangSmith summary trace with four whitelisted fields. |
| `frontend/index.html` | Semantic controls for modes, members, upload, suggestions, chat, status, and limitations. |
| `frontend/app.js` | Fetch wrapper, timeouts, busy controls, text-only message/source rendering, session-status refresh. |
| `frontend/styles.css` | Responsive layout, chat bubbles, source disclosures, focus/disabled states. |
| `tests/test_app.py` | Offline API and component regression tests, with external providers mocked. |
| `evals/dataset.json` | Eight synthetic reference cases. |
| `evals/run.py` | Four evaluation checks, local runner, optional real LangSmith dataset/experiment creation. |
| `scripts/make_sample_pdf.py` | Reproducibly creates the two-page fictional PDF used by tests/evaluation/demo. |
| `scripts/live_smoke.py` | Explicit optional real OpenAI check using a single synthetic passage. |
| `scripts/lock_dependencies.py` | Resolves installed runtime dependencies into an exact lock; excludes unrelated dev packages. |
| `requirements.txt` | Direct runtime package pins. |
| `requirements-lock.txt` | Full runtime dependency closure resolved on Windows/Python 3.13. |
| `requirements-dev.txt` | Runtime requirements plus pytest, httpx, and reportlab. |
| `.env.example` | Empty credentials, model choice, tracing and hosting settings. |
| `.gitignore` | Excludes environments, credentials, local uploads, caches, logs. |
| `Dockerfile`, `.dockerignore` | Non-root container, health check, one worker, minimal build context. |
| `README.md` | Entry point, run/configuration commands, capability and limitation overview. |
| `docs/DEPLOYMENT.md` | Docker/Render instructions, temporary-storage and public-hosting limitations. |
| `docs/VERIFICATION.md` | Actual checks and unexercised paths. |
| `docs/synthetic-benefits.pdf` | Safe sample for an reviewer to upload. |
| `docs/browser-verification.jpg` | Browser verification capture from development. |

The directories are Python namespace packages, so module commands such as `python -m evals.run` work from the project root without `__init__.py` files. `.venv`, `__pycache__`, `.pytest_cache`, and `.sf` are local tooling/generated directories, not application source.

## 3. Install and run in Windows PowerShell

```powershell
Set-Location C:\Users\Syamalatha\Desktop\Coverag_Companion
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Using the explicit virtual-environment executable avoids PowerShell activation-policy problems. Python 3.13 is the tested interpreter. The existing `.venv` can be reused. Start the server before browsing http://127.0.0.1:8000/. API documentation is at `/docs`, health at `/health`. Ctrl+C stops the process. Use `--reload` during editing if desired; reloads discard uploaded documents.

For development checks, install `requirements-dev.txt` too. The exact runtime lock gives repeatable package versions; the smaller direct file is for understanding and deliberate dependency updates.

## 4. Follow one question

1. The browser reads the selected mode and member. `ask()` sends `POST /chat` with JSON `{mode, member_id, question}`. The browser automatically includes its same-origin document-session cookie.
2. `BodyLimit` caps incoming JSON to 8 KB before parsing. `ChatRequest` validates the mode, rejects blank/overlong questions and unknown fields, and strips surrounding spaces. No request selects a different user's session by a JSON parameter.
3. The route looks up a document from the cookie only in document mode, then calls `run_workflow()`.
4. The compiled graph receives a fresh state dictionary. It does not maintain conversation memory or store a checkpoint.
5. The entry conditional edge uses the explicit mode. Member mode runs `member_lookup` and finishes. Document mode runs `document_retrieval`, then `document_answer`, then finishes.
6. `run_workflow()` disables automatic graph tracing, invokes the graph, and optionally emits a sanitized summary.
7. FastAPI serializes the result. The browser displays its answer, answer-mode notice, source name, and expandable page excerpts using `textContent`.

```text
START -- mode=member --> member_lookup -----------------> END
      -- mode=document --> document_retrieval --> document_answer --> END
```

`State` is a TypedDict describing shared fields. Nodes return only updates, such as retrieved passages or the final result. LangGraph applies those updates before the next node. The graph is meaningful here because it makes the two source paths explicit and independently testable; no LLM decides which source to trust.

## 5. Member lookup

`find_member()` uppercases and trims an ID, then reads the corresponding dictionary. Unknown IDs produce HTTP 404. `create_answer()` uses keyword rules to select actual JSON values. Supported topics are plan name, annual deductible, primary care copay, and mock status. The annual deductible is not a remaining balance. Unsupported subjects such as specialist copays, claims, dental benefits, and remaining deductibles receive a limitation message. Keyword rules still have limited language understanding; they are intentionally not advertised as general reasoning.

A factual member answer never calls OpenAI. This preserves the exact source values and makes cost and behavior predictable. No insurer API is connected. A document upload neither modifies this JSON nor verifies its status.

## 6. Upload and session lifecycle

`POST /documents/upload` accepts a multipart file. The ASGI body wrapper limits the entire multipart envelope to 5 MB plus 64 KB overhead, even when the caller omits Content-Length. The endpoint separately reads at most 5 MB plus one byte of the file and rejects oversized content. File extension is checked, then pypdf parses the bytes rather than trusting MIME type.

`extract_pdf_text()` rejects empty input, encryption, more than 20 pages, parse/extraction errors, and documents with no extractable text. Each extracted page retains its original one-based `page_number`, including blank pages. More than 250,000 extracted characters is rejected. No OCR is implemented; scanned images need a text layer first. Extraction can still consume CPU/transient memory before these checks complete; process isolation is future work.

Only successful extraction replaces a previous document. The store rotates the session token on replacement. Filenames are display-only basenames; they never become filesystem paths. PDF bytes are not persisted. The extracted text stays in RAM under a random cookie token. Cookies are HttpOnly and SameSite=Strict; production HTTPS must set `COOKIE_SECURE=true`.

The deadline is absolute: asking questions does not renew the 30-minute upload lifetime. Every access checks expiration, and a task sweeps once a minute. `DELETE /documents` removes the record and cookie. Shutdown clears the store. Capacity is 100 documents. The frontend refreshes status once a minute and when the window regains focus. Tabs share cookies, so they also share a document; independent browser sessions are isolated. This is temporary session isolation, not authentication.

## 7. Retrieval and citations

The retriever splits page text into passages of at most 800 characters, starting every 600 characters. This overlaps neighboring passages by 200 characters without crossing page boundaries. It lowercases and tokenizes both question and passage, drops common words, and maps a few synonyms such as “drug” to “prescription”.

All meaningful question tokens must occur in a passage. Up to four matching passages are returned in document order. This favors abstention over broad keyword guesses; it can miss paraphrases, answers spread across pages, tables, or context outside a passage. There are no embeddings, vector database, or relevance model. A match is evidence to read, not a guarantee of semantic completeness.

Every returned source contains the original document name, page number, and verbatim excerpt. With no matches, the graph says the document does not contain a supported answer. It also blocks common live-event questions (claim status/current eligibility), because policy terms cannot establish those events. Users should inspect exclusions and surrounding policy context.

## 8. OpenAI versus fallback

Without `OPENAI_API_KEY`, `document_answer()` joins retrieved excerpts as an **extractive fallback**, clearly labeled “no LLM used.” It never pretends to generate a semantic summary.

With credentials, `ChatOpenAI` uses `OPENAI_MODEL` (default `gpt-4.1-mini`) and structured output matching `EvidenceAnswer`. The system message explicitly treats the question and passages as untrusted data. The model returns exact quotes plus passage indexes, or no quotes when unsupported. The backend checks index bounds, a minimum quote length, and exact substring membership. It generates the displayed answer from verified quotes only. Fabricated or invalid evidence triggers local fallback; provider exception details are not exposed.

This is intentionally **LLM-assisted extractive answering**, not unrestricted prose generation. It demonstrates a real provider call and schema validation while bounding factual output. Textual provenance does not prove semantic correctness: a quote can omit context or reflect a malicious document. Safe text rendering prevents document HTML from executing, but does not establish the truth of uploaded claims.

Provider calls have a 20-second timeout and zero retries, output is bounded to 1,000 tokens, questions to 500 characters, and selected evidence to four passages. The browser uses a 35-second timeout. Keys remain in backend environment variables. Only the question and retrieved excerpts go to OpenAI. If a key exists but is invalid or the service times out, the app stays usable with a clearly labeled fallback.

## 9. LangSmith and evaluation

Normal graph/LLM tracing is always disabled with `tracing_context(enabled=False)`. When `LANGSMITH_TRACING=true` and a key exists, the application uses the real `@traceable` integration to emit a separate root summary containing only `mode`, `answer_mode`, `found`, and fixed route node names. It omits filenames, questions, member IDs/names, document content, generated answers, provider errors, and secrets. Telemetry failure must not break chat.

For a synthetic demonstration, set the LangSmith environment variables in `.env`, restart, and ask a synthetic question. Look for `coverage_request_summary` in the configured project. The trace shows which branch ran and whether it answered, not the private content or a full node trace. Setting standard tracing variables does not override the application's explicit suppression.

The separate evaluation runner uses `evals/dataset.json`. Its eight reference examples check:

- Expected member values/document answer substrings.
- Exact cited page sets.
- Whether every cited excerpt is present on the claimed synthetic page, and a found document answer has sources.
- Whether the application appropriately answers or abstains.

Run locally with `python -m evals.run`. It forces OpenAI off, even when credentials are available. `python -m evals.run --langsmith` creates a real remote synthetic dataset and calls `Client.evaluate()` with the same target and checks, concurrency one. This explicitly uploads synthetic questions and results to LangSmith. It is separate from redacted application tracing. The small dataset is a regression suite, not a statistically valid performance benchmark.

## 10. Verification and debugging

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evals.run
.\.venv\Scripts\python.exe -m pip check
node --check frontend/app.js
```

Tests use FastAPI TestClient and generate synthetic PDFs in memory with reportlab. External provider calls and tracing are mocked; no API charges occur. They cover upload errors, text limits, boundary pages, session isolation/expiry/replacement, source pages, routing, body limits, security headers, deterministic member values, and provider errors/quote validation. The live OpenAI smoke check is explicit: `python -m scripts.live_smoke`. Without credentials it exits without a request.

If the browser cannot connect, check that the server is running and use its HTTP URL instead of opening the HTML file. HTTP 409 in document mode means the document is missing or expired; upload again. HTTP 422 means an input is invalid. HTTP 413 means the file/request/extracted text exceeded a limit. HTTP 503 means the RAM store is full. Upload errors preserve the prior document. An unknown member is HTTP 404. On a hosted service, an origin error usually means `APP_ORIGIN` does not match the public HTTPS URL.

## 11. Deployment and limitations

Read [DEPLOYMENT.md](DEPLOYMENT.md) for the Dockerfile, Render settings, health checks, and secret configuration. Use one worker and one instance. RAM storage cannot support horizontally scaled deployments and is lost on restart. Docker Desktop must run before building. Neither publishing nor paid provisioning is part of this handoff.

Implemented: member lookup, PDF text extraction, per-browser temporary storage, lexical retrieval, citations, compiled graph routing, optional real OpenAI quote selection, optional LangSmith summaries/evaluations, UI, tests, and deployment files.

Mocked: all member plan data and eligibility status. Requires accounts/credentials: live OpenAI and LangSmith operations. Not implemented: OCR, real eligibility/claims, personal-data workflows, user authentication, durable storage, cost rate limits, full semantic retrieval, or production compliance.

## 12. Architecture questions grounded in the code

**Why use LangGraph here?** It gives explicit conditional routing and separate nodes for member lookup, document retrieval, and document answering. The graph is compiled once and invoked with fresh request state. A simple API could route without it, but this structure demonstrates inspectable workflow boundaries.

**How do you prevent hallucinated benefit values?** Member values are deterministic JSON lookups. Document fallback quotes source text. OpenAI can select exact quotes only, and the backend verifies substring membership. The design bounds invented text but still requires human review for relevance, omissions, and exclusions.

**Is this a real eligibility integration?** No. The three status strings are fictional public demo records. Policy documents also cannot confirm live member events.

**Why no vector database?** Twenty-page documents fit a small lexical retriever. Avoiding embeddings reduces services, cost, and setup. The tradeoff is lower recall for paraphrases and complex questions.

**How is an upload isolated?** A random HttpOnly cookie selects a bounded server-side RAM record. The client cannot choose another record through a member ID. The store uses a lock and absolute expiry. This is not a logged-in identity system.

**What happens on two workers?** Each worker would have a different RAM store. Document requests could hit a worker without that session, so the supported deployment uses one worker/instance.

**What is traced?** Only four sanitized status fields. Neither full graph state nor prompts/documents are sent by normal tracing. The separate evaluation command deliberately uploads only built-in synthetic examples.

**How is prompt injection handled?** Document text is data in a lower-priority message, provider instructions reject embedded commands, outputs have a schema, and exact-quote verification bounds the answer. Browser rendering uses textContent. This mitigates execution and invented prose; it does not make untrusted policy text authoritative.

**How do you test without API charges?** TestClient exercises API paths, PDFs are generated in memory, and provider functions are replaced with deterministic fakes. Evaluation forces OpenAI off. A separate explicit smoke script handles a real provider call.

**What would you change for production?** Add authentication, rate/cost controls, isolated PDF parsing, operational monitoring, a shared TTL store if scaling, stronger retrieval/evaluation, and a privacy/security review. Those are future changes, not features claimed by this demo.

## Official references consulted

- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangChain ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI quickstart and backend credentials](https://developers.openai.com/api/docs/quickstart)
- [LangSmith evaluation SDK](https://docs.langchain.com/langsmith/evaluate-llm-application)
- [LangSmith tracing controls](https://kb.langchain.com/articles/2491399069-how-do-i-disable-or-toggle-langsmith-tracing-during-execution)
- [Render FastAPI deployment](https://render.com/docs/deploy-fastapi)
