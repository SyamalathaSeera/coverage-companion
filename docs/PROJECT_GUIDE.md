# Coverage Companion project guide

An eligibility and benefits workspace using synthetic records and source-backed document answers.

## Three-minute walkthrough

1. Start with the worklist. Explain the counts of loaded transactions, synthetic patients, recorded exceptions, and authorization flags.
   Counts overlap: the pending specialist transaction has both an exception and
   an authorization requirement. These numbers describe the loaded preview only.
2. Filter flagged records. Review a terminated pharmacy record: pharmacy coverage is recorded as
   terminated and the response is denied. Show the underlying fields and dates.
   Explain that follow-up is a human workflow prompt, not an automated insurance decision.
3. Review a pending specialist record: pending specialist transaction, authorization required. Show
   why the system requests payer follow-up rather than treating a copay as proof of coverage.
4. Review an active dental record and ask about the recorded dental copay and deductible total.
   Explain that these values are deterministic source lookups, with service scope preserved.
5. Switch to document mode. Download the bundled synthetic PDF, upload it, ask
   about prescription benefits, and open the page citation. Then ask about dental
   implants: no supporting passage should produce abstention.
6. Close with verification and deployment limits. Tests use mocked providers;
   offline evaluation checks eight synthetic cases. The live OpenAI smoke test has also passed; Docker
   validation and external deployment remain separate release checks.

## Project overview

Coverage Companion helps reviewers find recorded eligibility exceptions, inspect service transactions, and explain benefits with source evidence. Structured amounts come directly from records. The optional language model selects document quotes, which the server validates before display. All bundled patient and service records are synthetic.

## What each AI tool does

| Tool | Actual role |
| --- | --- |
| LangGraph | Explicit routing: member lookup, or document retrieval followed by answering. It does not let an LLM select the factual source. |
| LangChain / OpenAI | Structured quote selection from retrieved document passages. The backend validates quoted text and page associations; invalid output falls back to extraction. |
| LangSmith summaries | Optional remote telemetry with only `mode`, `answer_mode`, `found`, and `route`. Useful for seeing answer paths and fallback frequency. |
| LangSmith experiments | Optional synthetic dataset and evaluation results, using `python -m evals.run --langsmith`. Checks expected answers, citation pages, evidence support, and found/abstain behavior. |

LangSmith does not generate answers, train a model, or serve as the member database.
The regular app disables automatic graph and provider tracing. Its summary trace
does not include questions, names, IDs, document content, answers, or keys. It also
does not measure end-to-end LLM latency or token cost: only the summary function is traced.
The separate evaluation experiment intentionally uploads the built-in synthetic
examples and outputs, and forces extractive mode; it does not benchmark live OpenAI.

## Enable LangSmith when you have an account

Set these on the backend in `.env`, then restart:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-private-key
LANGSMITH_PROJECT=coverage-companion
```

Then use the app to produce sanitized summaries. To create a separate synthetic
experiment, run:

```powershell
.\.venv\Scripts\python.exe -m evals.run --langsmith
```

No LangSmith connection or remote run is claimed until this succeeds. Offline
evaluation needs no key: `.\.venv\Scripts\python.exe -m evals.run`.

## Be candid about scope

This prototype uses keyword-based structured answers and conservative lexical
document retrieval. It has no authentication, insurer integration, claim adjudication,
medical coding, OCR, persistent case assignments, or production compliance certification.
All historical transactions still need fresh payer verification for a real visit.
Adding more sample rows does not make the system clinically or operationally validated.

Deployment configuration is in `render.yaml`. Hosting still needs a connected
account, source repository, secrets, correct HTTPS origin, and a successful live
smoke test. Bundled synthetic records are used when no local GoMask import is present.
