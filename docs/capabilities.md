# FalkorDB capability check — 2026-10-16

## Environment

- Docker Desktop: 4.95.0
- Docker Engine: 29.8.2
- Docker Compose: 5.6.0
- Image: `falkordb/falkordb:latest`
- Pulled image digest: `sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a`
- FalkorDB module from startup log: 4.22.1
- Redis server from startup log: 8.10.2
- Python: 3.13.12
- Python client: `falkordb` 1.8.0

## Checks performed

- `docker run --rm hello-world`: **PASS**, printed `Hello from Docker!`.
- Python connection using `FalkorDB(host='localhost', port=6379)` and `select_graph(...)`: **PASS**.
- `RETURN 1 AS ok`: **PASS**, result `[[1]]`.
- `Graph.copy(clone: str)`: **PASS**. Copied a two-node synthetic graph; copy returned count `[[2]]`.
- Variable-length edge pattern `[:LINK*1..3]`: **PASS**, one-hop path returned `[[1]]`.
- `CALL dbms.procedures()`: **PASS**, 26 procedures returned.

Available graph algorithms reported by `dbms.procedures()`:

`algo.AStar`, `algo.betweenness`, `algo.BFS`, `algo.HarmonicCentrality`, `algo.labelPropagation`, `algo.maxFlow`, `algo.MSF`, `algo.pageRank`, `algo.SPpaths`, `algo.SSpaths`, `algo.WCC`.

## Still to verify

- Full attack traversal with multiple relationship types and the node/edge status filters.
- The call signature and output shape for `algo.betweenness` before using it.
- Seed generation and scenario counts/risk/impact.

## Cleanup and host note

The two temporary capability graphs were deleted and `list_graphs()` returned `[]`; the temporary `nexus-falkordb-check` container was stopped. The image remains in the local cache.

Docker config selects credential helper `desktop`. The helper exists under `C:\Program Files\Docker\Docker\resources\bin`, but the current shell PATH did not include that directory. For Docker commands in this environment, prepend that directory to `$env:PATH`; do not read or expose Docker config credentials.

## Gate A follow-up

After the initial capability checks, the full NEXUS multi-relationship traversal and active node/relationship status filters were exercised in `engine/paths.py` against the seeded graph. The `scripts_demo.py` Gate A run passed with 3, 1, and 0 crown-jewel paths for Alex, the leaked-token account, and Priya respectively. The active development container is `nexus-falkordb-gate-a` (ephemeral `--rm` container); stop it only after the next engine phase or replace it with the eventual Compose service.

## Gate B — simulation and containment (2026-10-16)

Using the project `.venv` and deterministic 157-node seed:

- `python scripts_decide.py`: **PASS**. ALT-1042 recommends `isolate_device LAPTOP-042`; ALT-2071 recommends `disable_account SVC-ACCT-17`; ALT-3310 recommends `monitor_only`.
- ALT-1042 simulation: risk 80; monitor leaves 80; isolation reaches 0 with LOW impact; disabling SVC-ACCT-09 reaches 0 but has CRITICAL impact and is Pareto-dominated by isolation.
- ALT-2071 simulation: risk 68; disabling SVC-ACCT-17 reaches 0 with LOW impact; block-IP leaves 49.
- Safety workflow: high-impact `disable_account SVC-ACCT-09` rejected without approval (`APPROVAL_REQUIRED`), accepted with approval, and verified against simulated residual risk; rollback returned risk to 80.
- Policy-selected isolation auto-executed without approval as specified because its impact is LOW; verification passed, and rollback returned risk to 80.
- After both workflows, the live Alex risk was 80, graph node count was 157, and `client().list_graphs()` contained no `nexus_sim_` leftovers.

The project later added a pytest suite; see Gate E below. The investigation store contains only synthetic test records in ignored `data/`; no credentials were used.

## Agent, API, MCP, UI and packaging integration (2026-10-16)

- Scripted agent: **PASS** for `ALT-1042`, `ALT-2071`, and `ALT-3310`; five-step traces and expected recommendations were returned. This mode is labelled `scripted` and does not use an LLM.
- FastAPI TestClient: **PASS**. Three alerts returned; mock investigation returned `isolate_device`; graph endpoint returned 200; containment verified risk 80→0; refresh showed execution; rollback restored risk 80; unknown alert returned 404.
- MCP SDK: initial pin 2.3.0 was incompatible with the specification's `mcp.server.fastmcp` import. Changed direct pin to `mcp==1.30.0`; stdio MCP client then discovered all 8 tools and successfully called `calculate_risk` for `U-ALEX` (score 80, CRITICAL, K 4.0).
- Compose: built the Python 3.12 app image; isolated FalkorDB on the Compose network; mapped app port 8080 because another local app listens on port 8000. Avoided publishing DB ports because the Gate A development container already occupies 3000/6379. Compose health check reported FalkorDB healthy, app seeded 157 nodes, and `POST /api/investigate` at localhost:8080 returned scripted mode with expected `isolate_device LAPTOP-042` recommendation.
- After updating to `mcp==1.30.0`, rebuilt the app image; container reported `FastMCP import: PASS`. Packaged ALT-1042 investigation again returned `scripted` and `isolate_device LAPTOP-042`.
- Stopped `docker compose` and `nexus-falkordb-gate-a` after checks. Compose named data volume was preserved; no containers remain running for this task.
- UI baseline is implemented in `ui/index.html`, including decision, matrix, trace, graph and contain/rollback interactions. Browser visual inspection remains outstanding: computer-use safety halted before navigation because the current browser URL could not be determined confidently; no browser action was taken.

## Gate E — automated tests (2026-10-16)

Command: `.venv\Scripts\python.exe -m pytest -q`

Outcome after MCP SDK pin `mcp==1.30.0`: **PASS**, `10 passed in 6.14s`. Tests cover all 3 decisions, no-candidate monitoring, unsimulated-action rejection, approval, execute/verify/rollback, graph-copy cleanup, scripted traces, and mock API flow.

## Graph physics UI update (2026-10-16)

- `ui/index.html` uses Cytoscape.js's built-in CoSE force-directed layout; no new dependency was added.
- Browser JavaScript passed `node --check`; the rebuilt Compose app returned HTTP 200 and served the physics configuration and rerun control.
- Browser visual QA remains outstanding.

## Benchmark (2026-10-16)

Command: `python -m bench.run_benchmark` with `MOCK_LLM=1` and the default `BENCH_N=30`.

Outcome: **30 of 30** engine decisions executed with risk equal to the simulated residual risk. No real LLM was configured, so agent agreement was not measured. Full rows are saved in `bench/results.md`. The benchmark initially exposed the empty-candidate case for service entities; `engine/pareto.py` now falls back to monitor-only when no containment action applies, covered by a regression test.
