# Deployment guide

This is a project demo for synthetic data. No external resources have been created.

## Release defaults

A fresh checkout and Docker image include three demo members plus eight
project-owned fictional service records. Local `backend/data/gomask.json` imports
remain usable locally and are excluded from Git and the deployment image. The
hosted demo therefore has a working worklist without redistributing GoMask data.

The single process shares allowances of 60 chat requests per minute, 10 uploads
per minute, and 100 OpenAI request attempts per UTC day. Configure
`CHAT_REQUESTS_PER_MINUTE`, `UPLOADS_PER_MINUTE`, and `OPENAI_DAILY_CALL_LIMIT` to
change these limits. A zero limit disables that operation. Rejected chat/uploads
return 429 with `Retry-After`. When the OpenAI allowance is exhausted, document
answers use local extraction. This is a request-count limit, not a dollar budget;
failed provider attempts count too. Counters reset on restart, are shared by all
visitors, and are not a replacement for authentication or provider-side spending controls.

GitHub Actions runs offline tests, evaluation, dependency validation, JavaScript
syntax checks, and a Linux Docker build when the repository is pushed. This
workflow has been added but has not run on GitHub yet.

## Deploy with the included Render Blueprint

1. Publish this folder to your GitHub repository. Keep `.env` excluded; `.env.example` must contain no credentials.
2. In the Render dashboard, choose **New > Blueprint** and connect that repository. Render reads the included `render.yaml`.
3. Supply `OPENAI_API_KEY` as a secret in Render. For `APP_ORIGIN`, use the actual service's HTTPS URL without a trailing slash. If Render hasn't assigned the URL yet, update this variable in the service's Environment settings after creation and redeploy before using uploads or chat.
4. The Blueprint selects the free plan, Docker runtime, `/health` check, secure cookies, and manual deployments. Keep one instance; the Dockerfile already runs one worker. Free services can suspend when idle, which discards uploaded documents.
5. After deployment, open `/health` and confirm `{"status":"ok"}`. Open `/config` and confirm `llm_configured` is `true` (this checks configuration presence, not key validity). Then test a synthetic PDF upload, document question, and removal.

Local `.env` settings are not uploaded to Render. LangSmith is optional and disabled in the Blueprint. The OpenAI key is used only for document answers; member answers always use fictional records. Never put a key in frontend files or `render.yaml`.

Blueprint fields and secret prompts follow the [official Render Blueprint reference](https://render.com/docs/blueprint-spec).

## Docker locally

Docker Desktop must be running in Linux container mode.

```powershell
docker build -t coverage-companion .
docker run --rm -p 8000:8000 --name coverage-companion coverage-companion
```

Visit http://127.0.0.1:8000/. For optional credentials, add `--env-file .env` before the image name. Do not bake keys into the image. The Dockerfile uses Python 3.13, the runtime lock, a non-root user, one Uvicorn worker, no access logs, and a health check that respects `PORT`.

The runtime lock was resolved on Windows/Python 3.13 and excludes unrelated local packages and developer tools. Exact runtime package versions are pinned. Linux container installation/build still needs validation in a running Docker environment. To refresh deliberately after changing direct requirements: install them, run `python -m scripts.lock_dependencies`, review the lock, and run tests again. Do not upgrade packages during a deploy.

## Render: one web service

The service can use Render's Docker runtime with the supplied Dockerfile. After you publish this code to your own repository:

1. Create a Render Web Service, connect the repository, and choose Docker.
2. Keep a single service instance and a single worker. The Dockerfile reads Render's `PORT` and binds to `0.0.0.0`.
3. Set health check path to `/health`.
4. Set `COOKIE_SECURE=true` and `APP_ORIGIN=https://YOUR-SERVICE.onrender.com` (no trailing slash). This matters behind the HTTPS proxy for same-origin request checks.
5. Leave `OPENAI_API_KEY` empty for the local extraction demo. Optionally add it and `OPENAI_MODEL` as secret environment settings. Review account billing before enabling OpenAI on a public URL.
6. Optionally configure `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT`. Only sanitized summaries are sent by the application.
7. Deploy manually, then test `/health`, member switching, synthetic PDF upload, sources, unsupported questions, and removal. Verify the cookie has Secure and HttpOnly flags on HTTPS.

Alternatively, Render's native Python service can use Python 3.13, build command `pip install -r requirements-lock.txt`, and start command `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log`.

Official reference: [Render FastAPI deployment](https://render.com/docs/deploy-fastapi).

## Temporary storage and practical limits

Documents live only in the current process's RAM. No persistent disk is needed. Restart, redeploy, crash, or host suspension discards documents; browsers must upload again. Multiple workers or horizontally scaled instances would produce inconsistent sessions and are unsupported without replacing the store with a shared expiring data store. Cookie sessions are not identity authentication.

The store allows at most 100 concurrent documents, each with at most 250,000 extracted characters. Requests are capped before multipart parsing; uploads are also checked for their actual file byte size. A document expires at 30 minutes, with background cleanup within a minute. Extraction still runs inside the server process: compressed/malformed PDFs can consume CPU or transient memory before the text limit is checked. This demo is not hardened for arbitrary public uploads.

Before a broad public release, add authentication, durable per-user quotas, process-isolated PDF parsing, monitoring, a privacy policy, operational review, and shared storage if scaling. These remain deployment limitations. The current code intentionally uses no real personal data. No production-readiness or HIPAA claim is made.
