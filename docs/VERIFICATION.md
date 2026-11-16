# Verification record

## Deployment preparation, November 16, 2026

- Removed company-specific references from application copy and documentation.
- 55 offline tests passed, along with all eight evaluation cases, JavaScript syntax,
  and Python dependency checks. Tests covered request limits, daily provider
  allowance, extraction fallback, and bundled synthetic scenarios.
- The separate live OpenAI smoke test succeeded with `llm_evidence` and `found=true`.
  A sanitized LangSmith test summary was also verified remotely after configuration.
- The Docker image excludes local GoMask imports and uses bundled service examples.
  The new GitHub Actions workflow includes tests, a Linux image build, and container
  startup checks; it has not run yet.
- Docker could not be validated locally because the Docker engine is not running.
  No external deployment has been made. Earlier entries below describe earlier states.

## November 16, 2026 update

- 50 tests passed, including GoMask validation, service scope, worklist reasons,
  overlapping flag counts, repeated patient transactions, and API checks.
- Eight offline evaluation cases passed all four checks. JavaScript syntax and
  Python dependency checks passed.
- On the running local server, `/operations` returned 8 transactions, 8 patients,
  3 recorded exceptions, and 2 authorization flags. PAT0003, PAT0004, and PAT0002
  could be selected through their IDs and answered status questions successfully.
- The current HTML references versioned assets and the worklist. The bundled
  sample PDF download, upload, and unsupported dental-implant abstention worked.
- These updates were checked through HTTP and offline tests. The new worklist
  has not received browser visual QA; browser automation was unavailable in this
  session. Earlier browser evidence below applies to the earlier UI.
- OpenAI has a local key configured, but live provider success has not been
  verified. LangSmith tracing is disabled and no LangSmith key is configured.
  No remote traces, experiments, Docker build, or public deployment are claimed.

Verified on November 13, 2026 using Windows, Python 3.13.5, and the workspace virtual environment.

- `python -m pytest -q`: 36 tests passed. External provider operations are mocked. HTTP tests were run outside the workspace sandbox because Windows socketpair creation hung inside the sandbox, before any application request.
- `python -m evals.run`: 8/8 synthetic examples passed all four checks (expected answer, source pages, document support, found/abstain). These are deterministic regression examples, not general performance metrics.
- `python -m pip check`: no broken requirements.
- `node --check frontend/app.js`: passed.
- `python -m compileall -q backend evals scripts tests`: passed.
- Browser smoke on a temporary local Uvicorn server: initial page, member deductible, switching to Taylor's inactive mock record, document mode, sample PDF upload, prescription benefits with page 2 citation, expanded excerpt, unsupported dental implant question. A 390px viewport reported document width 375px (no horizontal overflow); the viewport was reset afterward. Screenshot: `browser-verification.jpg`.
- The sample PDF generator created the two-page synthetic benefits document successfully.

Not exercised live:

- OpenAI: no backend credential was configured. Schema/quote verification, success, abstention, provider failure, and fallback are covered using mocks. The separate `python -m scripts.live_smoke` command is available once credentials are configured.
- LangSmith: no credential was configured. Summary sanitization is tested with a mocked trace function. Real tracing and remote dataset/evaluation code are implemented, but no remote experiment or trace result is claimed. Run `python -m evals.run --langsmith` for synthetic remote evaluation after account setup.
- Docker: the CLI exists, but Docker Desktop's Linux engine was not running. The container image was not built or run. Linux dependency installation remains to be checked in Docker.
- External hosting: nothing was deployed, published, provisioned, committed, or pushed. Render instructions are prepared for the owner.

Study `LEARNING_GUIDE.md` first; see `DEPLOYMENT.md` before hosting. The application is a synthetic-data project demo, not a production insurance system.
