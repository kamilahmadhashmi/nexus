# Open-source tooling evaluation — 2026-10-16

This review evaluates the four repositories named in the project request against the current NEXUS stack: a Python 3.13 / FastAPI API, a single static HTML/Cytoscape.js UI, Docker Compose for the local app and FalkorDB, and a synthetic scripted demo. The Python app container installs only `requirements.txt`; browser/agent tooling remains outside the shipped runtime.

## Decision summary

| Repository | License and current project fit | Decision |
|---|---|---|
| [OpenHands Agent Canvas](https://github.com/OpenHands/OpenHands) | MIT. Self-hosted agent control center/orchestrator; latest release page showed v1.27.1. Local quickstart needs Node 24+ and `uv`; this host has Node 22.18.0. Unsandboxed mode grants the agent full host filesystem access. It needs a configured agent/model backend; no unlimited inference is included. | Evaluate only; do not install. NEXUS already has Codex for edits; Canvas adds another agent runtime, setup, and model-backend configuration without improving the shipped UI. |
| [Aider](https://github.com/Aider-AI/aider) | Apache-2.0. Repo-aware terminal coding with Git integration; current main supports Python 3.10–3.14, including this host's 3.13.12. Latest release page showed v0.86.0. Repo history showed commits through May 22, 2026, with later community PR activity. | Evaluate only; do not install. It could support incremental edits, but duplicates the current Codex/Git workflow. It is a client, not free inference: a hosted model API key and provider billing may apply, or the user must run a local model with suitable hardware. |
| [Microsoft Playwright](https://github.com/microsoft/playwright) | Apache-2.0, actively released (v1.64.1 upstream on Oct 14, 2026). Python bindings support Python 3.10+; this host runs Python 3.13.12. | Adopt as a development-only browser test. It exercises NEXUS's real rendered page and stateful demo workflow, detects JavaScript/runtime and responsive layout regressions, and captures reviewable screenshots. |
| [Syngrisi](https://github.com/syngrisi/syngrisi) | MIT (declared in its README), self-hosted visual comparison platform; latest release page showed v3.19.1. Native development expects Node 22.19+, Yarn and MongoDB 8.0+; its Docker server still adds another service. Optional AI triage can use a self-hosted/local model. | Do not integrate yet. Playwright screenshots and the current smoke workflow cover the immediate one-page UI. Reconsider if we adopt multiple approved visual baselines or CI cross-browser comparisons. |

## Playwright setup and costs

`requirements-dev.txt` pins `playwright==1.64.0` and includes the existing application/test requirements. The upstream GitHub release v1.64.1 was newer at review time, but the configured Python package index offered only through 1.64.0; use the pinned installable release instead of claiming an installation that could not be completed. The Chromium build downloaded by Playwright is about 200 MB. No Playwright cloud account, paid browser service, model key, or AI inference is needed. The tested page loads Cytoscape.js from cdnjs, so browser test execution requires network access to that CDN unless the UI dependency is later vendored.

From PowerShell, with Docker Compose serving the scripted app at `http://localhost:8080`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest tests/e2e -q
```

Override the app URL with `NEXUS_BASE_URL` if needed. Screenshots are written to `artifacts/screenshots/`; override the location using `NEXUS_SCREENSHOT_DIR`. The browser automation is test tooling only and is not copied into the Docker image as a Python dependency.

## Setup notes for the alternatives

- **OpenHands:** upstream quickstart is `npm install -g @openhands/agent-canvas` then `agent-canvas`; it requires Node 24+ and `uv`. Configure an agent/model backend (or a local model); a hosted provider may bill separately. Docker sandbox setup is available but mounts selected project directories for agent access.
- **Aider:** upstream installer is `python -m pip install aider-install` then `aider-install`; afterward choose/configure a supported hosted provider and API key, or supply a locally running model. Model inference is not bundled or unlimited. Python compatibility is suitable here, but the current workflow does not need another AI editor.
- **Syngrisi:** upstream self-host path downloads its app Dockerfile and Compose file, then runs `docker compose up`; native development expects Node 22.19+, Yarn 1.22+, and MongoDB 8.0+. Baseline screenshot comparison is self-hosted/MIT; optional AI triage requires an available model backend, potentially local Ollama. None of those services were added to NEXUS.

## What the browser workflow verifies

`tests/e2e/test_browser_workflow.py` checks the home page and its three alert choices, runs `ALT-1042` through the scripted agent, verifies graph nodes render, reruns CoSE physics, applies and rolls back containment, confirms and executes demo reset, checks the 390px viewport for page overflow and a horizontally scrollable matrix, and asserts the page emitted no uncaught JavaScript exceptions. It records desktop home, desktop investigation, and mobile investigation screenshots in the repository. The workflow ends with the synthetic graph reset to its baseline.

On its first pass, Playwright surfaced an uncaught Cytoscape error when the UI destroyed a graph while its animated CoSE layout was still running. `ui/index.html` now explicitly stops the active layout and Cytoscape animations before graph teardown. The same run found that the graph canvas retained its desktop size after a viewport change; the UI now resizes the Cytoscape instance with the window. At mobile widths, the containment matrix keeps readable columns in an internal horizontal scroller and shows a swipe hint rather than squeezing every column to a few pixels.

## Verification results

- Python 3.13.12 and Playwright Python 1.64.0 installed in the project `.venv`; Chromium build 1248 installed locally.
- Playwright browser workflow: **PASS** (1 test), including desktop and 390px mobile screenshots.
- Full project suite: PASS, 11 passed in 17.44s, including the Playwright flow. Backend tests used a temporary isolated FalkorDB on 127.0.0.1:16379; the test container was stopped and removed afterward. Compose demo stack remains available on port 8080.
- Current committed application dependencies and Compose service list are unchanged by the test-tool installation.

## Upstream references checked

- OpenHands [README / setup](https://github.com/OpenHands/OpenHands#readme), [MIT license](https://github.com/OpenHands/OpenHands/blob/main/LICENSE), [releases](https://github.com/OpenHands/OpenHands/releases).
- Aider [README / setup](https://github.com/Aider-AI/aider#readme), [Apache-2.0 license](https://github.com/Aider-AI/aider/blob/main/LICENSE.txt), [Python compatibility](https://github.com/Aider-AI/aider/blob/main/pyproject.toml), [releases](https://github.com/Aider-AI/aider/releases), [commit history](https://github.com/Aider-AI/aider/commits/main/).
- Playwright [README / getting started](https://github.com/microsoft/playwright#readme), [Apache-2.0 license](https://github.com/microsoft/playwright/blob/main/LICENSE), [Python binding requirements](https://github.com/microsoft/playwright-python/blob/main/pyproject.toml), [Python installation docs](https://playwright.dev/python/docs/intro), [releases](https://github.com/microsoft/playwright/releases).
- Syngrisi [README / setup](https://github.com/syngrisi/syngrisi#readme), [releases](https://github.com/syngrisi/syngrisi/releases).
