# NEXUS Project Knowledge Base and Handover

> Living project record. Update after each meaningful decision, change, test, failure, benchmark, or handoff. Keep claims evidence-based; never store secrets.

## 1. Purpose and current state

NEXUS is a Track 1 hackathon prototype for investigating synthetic cybersecurity alerts through a FalkorDB graph. It traces multi-hop paths to critical data, computes deterministic risk and business impact, simulates containment on GRAPH.COPY sandboxes, applies a transparent Pareto policy, and can verify or roll back an approved action. The graph is the decision substrate, not decoration.

**Current verified state (2026-10-16):** B8–B21 core work is implemented in C:\Users\KIIT\Desktop\nexus_win. Gate A, Gate B, the 10-test pytest suite, mock HTTP flow, MCP stdio discovery/call, the 30-alert deterministic benchmark, and packaged Compose startup/ALT-1042 investigation have passed. The app runs at http://localhost:8080 when Compose is up. No API key was configured, so real LLM tool selection has not been run. Browser visual review, fresh-clone rehearsal, public repo, and demo recording remain outstanding.

### Documentation recovery note

During a documentation update on 2026-10-16, an accidental empty file patch truncated the previous 44 KB stuff.md. The local Git repository had no commits, so the previous file could not be restored from Git. This handover has been reconstructed from the supplied continuity-rule attachment, the three pasted planning/resource files, PROJECT.md, docs/capabilities.md, current source, and outputs captured during this session. It records verified current facts and important prior decisions; where earlier detail could not be recovered verbatim, it is summarized rather than presented as an exact transcript.

## 2. User intent, discussion, and event scope

- The user first asked for an opinion on the supplied 77-page NEXUS Build Specification (Track 1, Graph Hacks) PDF, then created a Desktop folder named nexus_win, requested stuff.md, asked about a GitHub repo, supplied event/resource excerpts, asked whether to use the FalkorDB repo, required using the provided resources, and finally directed: “start building this project and lets win this hackathon.”
- The user supplied a standing documentation/continuity rule requiring accurate status labels, source-of-truth reconciliation, exact evidence, chronological change history, unknowns, risks, and a takeover-ready next action. Original attachment: C:\Users\KIIT\.codex\attachments\a24ef763-76df-4eef-988d-de20873ae3d2\Pasted text.txt.
- The copied event page describes Graph Hacks: Context for AI Agents, powered by FalkorDB, online Oct 15–18, 2026, and three tracks. Chosen scope is Track 1: Agents That Act on Connected Data. Although the broad event overview mentions memory and coordination, the NEXUS Track 1 spec excludes persistent investigation memory, auth, multi-tenancy, and unrelated features.
- The event excerpt says submissions open Oct 17 at 1:03 AM GMT+5:30 and lists prizes, but event schedules/prizes are snapshots; recheck official event pages before submission.
- Prior official Rules-page check on 2026-10-16 confirmed a public source-code repository is required, plus README with setup and graph model, necessary Cypher/algorithms, demo video, live deployment or complete local setup, track declaration, and AI-tool disclosure/participant understanding. The rule says public repository, not specifically GitHub. No public repo or remote has been created yet.

## 3. Source precedence and project decisions

1. PROJECT.md is a page-separated text extraction of all 77 PDF pages. The original PDF remains authoritative for visual layout/tables. Part B explicitly takes precedence over Part A when they conflict.
2. Part B uses risk constant K=4.0; Part A says K=6. Implementation and README use 4.0. Do not tune after seeing results.
3. Part B risk code uses maximum privilege across nodes/paths to each target; Part A prose says last credential on best path. Follow Part B code.
4. Part B provides IP_FACTOR=0.6 and REVOKE_FACTOR=0.7; keep pinned.
5. Part B defines eight MCP tools including rollback, despite inconsistent Part A counting. Eight are implemented.
6. Part A prohibits animation; Part C proposes premium UI animation. Follow staged work: baseline B17 UI first; polish only after required gates.
7. The supplied seed implementation yields 157 nodes, while a checkpoint prose estimate says ~170–180. Keep specified data and report 157; do not add filler nodes.
8. Vulnerability AFFECTED_BY edges are seeded but Part B risk code does not modify exploit weights based on vulnerability. Do not claim vulnerability raises computed risk.
9. Use path coverage as the choke-point metric despite algo.betweenness being present: Part B's starter fallback uses path coverage, and output names the implemented metric explicitly.
10. The SDK starter expects mcp.server.fastmcp. MCP 2.3.0 breaks that import; pin mcp==1.30.0, which passed actual stdio discovery/call.
11. Docker host port conflicts: another local service uses 8000; the Gate A DB uses 3000 and 6379. Compose app uses host 8080 and reaches its own FalkorDB service on a private network, with no host DB ports published.

## 4. Organizer resources and how NEXUS uses them

The user-provided resources excerpt is at C:\Users\KIIT\.codex\attachments\37035029-f757-4e08-bd8c-8f7972d9f9b7\Pasted text.txt. It says no mandatory starter/boilerplate repository is provided; create a fresh public submission repository when ready. FalkorDB core is not a NEXUS starter and does not need to be forked.

| Resource | Role in NEXUS |
|---|---|
| [FalkorDB core](https://github.com/FalkorDB/FalkorDB) | Runs as the official Docker image; NEXUS depends on the database, not a fork of its source. |
| [Python client docs](https://docs.falkordb.com/getting-started/clients) / falkordb package | Used by engine/db.py for Cypher, graph copies, and graph selection. |
| [GraphRAG-SDK](https://github.com/FalkorDB/GraphRAG-SDK) | Reviewed as an optional organizer resource; not added as a dependency because deterministic graph tools cover this task and no GraphRAG feature is needed. |
| [FalkorDB community projects](https://www.falkordb.com/community-projects/) | Inspiration/reference only; no copied application code. |
| [Official Track tutorial](https://www.wemakedevs.org/blogs/how-to-build-an-agent-that-reasons-over-a-graph) | Architecture guidance: fixed typed tools, Python-authored Cypher, graph path evidence, graph-copy simulation. |
| [Hackathon resources](https://www.wemakedevs.org/hackathons/falkordb/resources) | Links getting started, Docker operations, Browser (port 3000), Cypher/limitations, algorithms, and tutorials on Cypher and algorithms. |
| FalkorDB Browser | Available on host port 3000 through the Gate A container for graph inspection; not required by app runtime. |
| FalkorDB algorithms | CALL dbms.procedures() found 26 procedures including algo.betweenness; this version uses path-coverage fallback instead. |
| Docker / Compose | Local reproducible FalkorDB + app deployment, including app-side deterministic seeding. |
| MCP | Exposes the same eight deterministic functions to compatible clients; verified by a real stdio client. |

The user-provided resources excerpt includes links to FalkorDB docs, official videos, and GraphRAG-SDK. Maintain the distinction between used, evaluated, and not needed; do not claim every listed library is a dependency.

## 5. Architecture and data flow

Architecture: Alert → LLM or labelled scripted runner → fixed deterministic tools → FalkorDB typed graph → GRAPH.COPY action simulations → Pareto and risk-impact policy → human contain approval → live risk verification or rollback.

The LLM may resolve alert text and choose questions/tools, but never generates executable Cypher or computes official risk/impact values. Python owns parameterized Cypher, deterministic scoring, candidate actions, simulation, policy, exact-action guard, verification and rollback. run_scripted exercises the same tools in a fixed sequence; response mode is scripted and must never be presented as AI tool-selection evidence.

### Schema and traversal

Synthetic labels: Person, Device, Server, ServiceAccount, Service, DataStore, Vulnerability, IPAddress, Alert. Typed edges include OWNS, LOGS_INTO, HOSTS_CREDENTIAL, AUTHENTICATES_TO, READS, HAS_ACCESS_TO, AFFECTED_BY, DEPENDS_ON, USES, USED_BY, and ABOUT. IDs are indexed; nodes carry id, name, synthetic, and status.

Attack paths follow OWNS|LOGS_INTO|HAS_ACCESS_TO|HOSTS_CREDENTIAL|AUTHENTICATES_TO|READS, depth at most 7, capped at 200, target criticality at least 7, and require active nodes/edges. Cypher returns IDs/types/exploit weights/privilege evidence; Python filters repeated-node paths and sorts deterministically.

### Scoring and policy

- Path exploitability is the product of edge exploit weights.
- Per-target path success uses noisy-OR; Part B uses maximum privilege among path nodes, default 0.5; target term = criticality × privilege × reach probability.
- Risk = round(100 * (1 - exp(-sum(terms) / 4.0))) (Part B K=4.0). Implementation bands: <20 LOW, <45 MEDIUM, <70 HIGH, otherwise CRITICAL (Part A prose has different bands; use Part B implementation).
- Impact capacity is 60; tier weights {1:10, 2:5, 3:1} and affected-person weight 0.5. Labels <20 LOW, <45 MEDIUM, <70 HIGH, otherwise CRITICAL.
- Pareto domination requires another row to be no worse in residual risk and impact and strictly better in at least one.
- Policy: initial risk <25 => monitor; otherwise choose the lowest-impact frontier action at residual risk <=40, tie-break by lower risk. If none meets 40, choose lowest residual risk and require approval. HIGH/CRITICAL actions require approval.
- If there are no non-monitor candidates for a high-risk entity, select monitor-only with a clear explanation. This defensive fallback was required by infrastructure-entity benchmark cases and is regression tested.

## 6. Safety and operational boundaries

- Candidate actions: isolate_device, disable_account, revoke_credentials, block_ip, monitor_only.
- Simulate each mutating action on a named graph copy; always delete copies in finally.
- Apply status/blocked metadata and modeled relationship weight scaling; do not delete graph nodes/edges.
- Execute accepts only an action+target present in that investigation's matrix. It requires approval for HIGH/CRITICAL impact or when policy recommendation requires it. Agent calls always set approved=False; autonomous mode is constrained. The UI/API contain click is the human approval path.
- After execution, recompute risk and compare with simulated residual (tolerance 1); retain change log, support rollback, restore status and original relationship weights.
- No auth, user accounts, multi-tenancy, persistent incident memory, production data, or real-CVE data. Synthetic only.
- Never commit .env, API keys, Docker credentials, or token values. .env and data/ are ignored.

## 7. Environment, install, and commands

Observed host: Windows, Python 3.13.12; Git 2.53.0.windows.2; Docker Desktop 4.95.0; Docker Engine 29.8.2; Compose 5.6.0; FalkorDB module 4.22.1 / Redis 8.10.2; image falkordb/falkordb:latest, digest sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a. Docker CLI/credential helper directory is C:\Program Files\Docker\Docker\resources\bin; prepend it to $env:PATH for commands. Do not expose Docker config secrets.

Project Python uses .venv; direct pins are in requirements.txt: falkordb==1.8.0, fastapi==0.143.3, uvicorn==0.54.0, mcp==1.30.0, anthropic==1.15.0, pydantic==2.14.1, pytest==9.1.1, python-dotenv==1.2.4, requests==2.34.2. No full transitive lockfile has been generated.

Commands from project root:

    .\.venv\Scripts\python.exe -m seed.generate
    .\.venv\Scripts\python.exe scripts_demo.py
    .\.venv\Scripts\python.exe scripts_decide.py
    .\.venv\Scripts\python.exe -m pytest -q
    .\.venv\Scripts\python.exe -m bench.run_benchmark
    docker compose up --build

Compose uses app port 8080 on host; open http://localhost:8080. It creates a private FalkorDB service and seeds 157 nodes at app startup. Local dev Gate A service is nexus-falkordb-gate-a on ports 6379 and 3000; Compose intentionally does not publish DB ports, avoiding collisions. .env.example defaults to mock/scripted mode. For real mode set MOCK_LLM=0 and ANTHROPIC_API_KEY in ignored .env; real mode is currently untested.

To re-seed a modified demo graph, run python -m seed.generate against the intended FalkorDB host. Test fixture also rebuilds/clears the synthetic nexus graph; run only against demo DB.

## 8. File map

- PROJECT.md — full 77-page extracted build specification; PDF remains original source.
- stuff.md — this master knowledge base and handover.
- README.md — judge-facing overview/setup, measured engine benchmark, limitations.
- docs/capabilities.md — environment and command-level capability/test evidence.
- seed/generate.py — deterministic synthetic graph/scenarios.
- engine/db.py, paths.py, risk.py, impact.py — DB access, traversal, scoring.
- engine/simulate.py, pareto.py, store.py, execute.py, tools.py — simulation, policy, JSON investigations, execute/rollback, eight shared tools.
- agent/loop.py — real Anthropic tool loop and labelled deterministic scripted runner.
- api/main.py, api/start.py — FastAPI, app runner/seed.
- ui/index.html — one-file baseline UI with Cytoscape CDN graph.
- mcp_server/server.py — eight MCP wrappers around the same tools.
- bench/run_benchmark.py, bench/results.md — synthetic 30-alert benchmark harness/results.
- tests/test_engine.py — 10 engine/agent/API tests; fixture reseeds DB.
- docker-compose.yml, Dockerfile, .dockerignore, .gitignore, .env.example, requirements.txt — build/run/configuration.
- scripts_demo.py, scripts_decide.py, check_capabilities.py — gates and diagnostics.

## 9. Verification ledger

### Environment and Gate A

- docker run --rm hello-world: PASS (Hello from Docker!).
- FalkorDB Python connection and RETURN 1 AS ok: PASS ([[1]]).
- Graph.copy(clone) on a two-node graph: PASS; returned copy count [[2]].
- Variable-length traversal: PASS. CALL dbms.procedures() returned 26 procedures, including algo.betweenness, BFS, PageRank, SPpaths, SSpaths, WCC.
- python -m seed.generate: PASS, seeded nodes: 157.
- scripts_demo.py: Alex 3 paths/risk 80 CRITICAL; SVC-ACCT-17 1/risk 68 HIGH; Priya 0/risk 0 LOW. Disable SVC-ACCT-09 impact 83 CRITICAL, four dependent services/30 users; disable SVC-ACCT-17 impact 5 LOW, BILLING-SVC/4 users.
- Gate A full multitype traversal and active-status filters passed.

### Gate B

- scripts_decide.py: ALT-1042 => isolate LAPTOP-042; ALT-2071 => disable SVC-ACCT-17; ALT-3310 => monitor-only.
- ALT-1042 matrix: monitor 80; isolate 0 / LOW; disable SVC-ACCT-09 0 / CRITICAL (dominated); revoke Alex 72 / LOW; block IP 68 / LOW.
- ALT-2071: initial 68; disable target 0 / LOW; block IP 49.
- High-impact account action rejected without approval (APPROVAL_REQUIRED), approved execution verified, rollback restored risk 80. Low-impact recommended isolation auto-executed as policy allows, verified and rolled back to 80. No nexus_sim_ graphs remained; main graph had 157 nodes.

### Agent/API/UI/MCP/Compose

- Scripted runner returned all three expected recommendations and five-step traces; labels mode scripted.
- FastAPI TestClient: alerts 200/count 3; investigate; graph; contain verified 80→0; investigation refresh showed execution; rollback to 80; unknown alert 404.
- MCP 2.3.0 initial import failure: No module named mcp.server.fastmcp (package stated FastMCP renamed in v2). Pinned mcp==1.30.0; actual stdio client discovered all eight tools and called calculate_risk for U-ALEX (80 CRITICAL, K 4.0).
- Compose first attempt exposed stale/non-network-attached DB container and occupied host ports 3000/6379/8000. Resolved by recreating project-managed containers, private DB networking, host app port 8080. Compose reports FalkorDB healthy, logs seeded nodes: 157, app reachable, and scripted ALT-1042 returns expected isolation recommendation.
- UI code is present; browser-based visual QA not run.

### Tests and benchmark

- Latest command after MCP pin and Pareto fallback: .venv\Scripts\python.exe -m pytest -q => PASS, 10 passed in 6.14s.
- python -m bench.run_benchmark, default 30 alerts, MOCK_LLM=1: 30 of 30 deterministic executions matched simulated residual risk. No real LLM configured; no AI agreement result. Full rows in bench/results.md.
- Benchmark first exposed the empty-candidate case on service alerts; resolved with monitor-only fallback and test. Earlier transient GRAPH.COPY failed, could not fork occurred while FalkorDB background save was in progress; subsequent run passed once save completed.
- After the MCP 1.30.0 pin, Compose was rebuilt; container reported FastMCP import PASS and ALT-1042 returned scripted isolation recommendation. The Compose stack and Gate A dev container were stopped after checks; named Compose data volume was preserved.
- Browser visual review was attempted using the computer-use skill but its safety layer stopped before URL navigation because the open browser URL could not be identified confidently. No browser action was taken; visual QA remains outstanding.

## 10. Git/publication and external submissions

Local Git repo was initialized on branch main, but no remote/public repo or commit is currently recorded. A public repository is required by official rules; create/push only after reviewing README and choosing the account/organization/URL. Do not imply public availability until verified. Check git status, branch and local user.name/user.email before committing; do not invent author identity. A local commit is appropriate after the current final gates.

No hackathon submission, video upload, emails, team invites, public posting, or deployment has been performed. These require user-directed external publication; build reviewable assets first.

## 11. Milestones and prioritized remaining work

### Complete and verified

- [x] Desktop folder/project scaffold and specification extraction.
- [x] Docker/FalkorDB environment gate and Gate A.
- [x] B11–B13 simulation, Pareto decisions, store, exact action guard, approval, verification/rollback, eight deterministic tools, Gate B.
- [x] B14–B16 scripted + real-mode loop implementation and FastAPI routes.
- [x] B17 baseline UI implementation (not visually reviewed yet).
- [x] B19 10 automated tests, B20 30-alert deterministic benchmark harness/results, B21 eight-tool MCP server.
- [x] Compose packaging and one packaged ALT-1042 scripted HTTP investigation.

### Next steps

1. Rebuild and restart Compose after the mcp==1.30.0 pin; verify MCP server packaging or at minimum API plus startup on 8080.
2. Open http://localhost:8080 in a browser and inspect responsive UI and interaction. Fix defects; update both docs and tests.
3. Re-run pytest and benchmark against one clean intended DB; record result in docs/capabilities.md and bench/results.md.
4. Check git status, ensure .env, data, .venv are ignored, inspect secrets, set author only if already configured, and create a local gate commit.
5. Ask user to select public repository host/account only when code is ready to publish. Verify public README clone/run instructions on a fresh checkout.
6. Real-mode LLM tool-selection run requires the user to configure a valid key privately. Record model/mode and actual tool choices; never log or write the key.
7. Capture screenshots and 90-second video after UI and real mode are verified; then use official rules for final submission details.

## 12. Decisions and recovery lessons

- Resource repo question: do not fork FalkorDB core; use official image/client and create an original fresh public NEXUS repository when ready.
- Do not claim every resource means every SDK must be installed. Use relevant resources and say how; list GraphRAG-SDK/community projects as reviewed/reference unless a real feature requires them.
- On Windows, Docker CLI is installed outside PATH; prepend C:\Program Files\Docker\Docker\resources\bin.
- Avoid fixed container names that collide with local databases and avoid unnecessary host port publications. Compose uses service DNS privately and host 8080.
- MCP major versions can break the starter API; verify using a real MCP client, not just import/compile.
- Preserve stuff.md before editing; never use an empty Add File patch on an existing file. This incident is recorded above; verify file length/content and documentation consistency immediately after large edits.
- Benchmark only the mode actually run. Current result is deterministic engine verification, not agent agreement.
- Maintain no secrets in source, results, terminal captures, or handover.

## 13. Source links and further reading

- Official [Hackathon resources](https://www.wemakedevs.org/hackathons/falkordb/resources), [rules](https://www.wemakedevs.org/hackathons/falkordb/rules), and [Track tutorial](https://www.wemakedevs.org/blogs/how-to-build-an-agent-that-reasons-over-a-graph).
- [FalkorDB getting started](https://docs.falkordb.com/getting-started/), [Docker operations](https://docs.falkordb.com/operations/docker), [Browser](https://docs.falkordb.com/browser/), [Cypher reference](https://docs.falkordb.com/cypher/), [known limitations](https://docs.falkordb.com/cypher/known-limitations), and [algorithms](https://docs.falkordb.com/algorithms/).
- User-provided event excerpt: C:\Users\KIIT\.codex\attachments\200c5ac5-8ffb-4b41-83ee-485c1d1f361d\Pasted text.txt.
- User-provided official resource extraction/analysis: C:\Users\KIIT\.codex\attachments\37035029-f757-4e08-bd8c-8f7972d9f9b7\Pasted text.txt.
- Full build spec: original PDF C:\Users\KIIT\Downloads\NEXUS Build Specification (Track 1, Graph Hacks).pdf; text extraction PROJECT.md.
