# NEXUS Build Specification (page-separated text extraction)

Source: `C:\Users\KIIT\Downloads\NEXUS Build Specification (Track 1, Graph Hacks).pdf`. This is a text extraction preserving page boundaries; PDF visual layout and some table/code formatting may differ. Refer to the original PDF for layout-sensitive details.

## PDF page 1

NEXUS Build Specification (Track 1, Graph Hacks)
NEXUS: Build Specification for Graph Hacks
Track 1
By kamil. Written so any capable LLM or developer can build the project end to end by
following it in order.
1. Mission
Build NEXUS, an autonomous cyber attack-path agent that uses FalkorDB as its decision
substrate. When a security alert arrives, the agent traces attack paths in a graph,
computes risk, simulates several containment actions on graph copies, selects the safest
one, executes it by mutating the graph, and verifies the result. The target is the Track 1
prize (Agents That Act on Connected Data) at the WeMakeDevs x FalkorDB hackathon,
deadline Oct 18, 2026, 11:59 PM IST.
Judging lens (design for these four)
1. The graph drives the agent. Remove FalkorDB and the agent cannot choose an action.
2. It really works and a judge can run it in one command.
3. Every answer is explainable with graph evidence.
4. It is presented clearly, decision first.
Non-negotiable success criteria
Every number shown (risk, impact, centrality) is computed from the graph. Nothing is
hardcoded to fit a story.
Three scenarios yield three different decisions: isolate device, disable service account,
monitor only.
Candidate actions are simulated on GRAPH.COPY sandboxes, never by lookup table.
The execute tool refuses any action not simulated in the current investigation.
docker compose up starts everything and seeds the data.
A benchmark compares the agent against brute force over many random alerts and
reports honest results.
Page 1 of 77

## PDF page 2

NEXUS Build Specification (Track 1, Graph Hacks)
2. Rules for the building LLM
Follow the build order in section 15 and pass each gate before moving on.
Verify FalkorDB features on the installed version before relying on them (section 4).
Never assume an algorithm exists.
Do not add features outside this spec. Forbidden: investigation memory, auth, multi-
tenancy, animations, extra scenarios.
Keep the engine deterministic and in plain Python. The LLM never computes scores.
Label all data as synthetic. Never claim latency numbers that you did not measure.
Never use the phrase Pareto optimal unless the Pareto code from section 8 exists. Call
the feature Next-Move Risk Analysis, never attacker prediction.
Write tests for the engine (section 14). Commit often.
3. Tech stack and repo layout
Database: FalkorDB (Docker image falkordb/falkordb:latest , port 6379, browser on
3000).
Language: Python 3.11+. Packages: falkordb , fastapi , uvicorn , mcp (official Python
MCP SDK), anthropic (or any LLM SDK with tool calling), pydantic , pytest .
Frontend: a single-page app. Use plain HTML + JS served by FastAPI (or Vite + React if
you prefer). Graph view with Cytoscape.js or D3 from a CDN.
LLM: any model with tool calling. Read the key from an environment variable. Provide a
MOCK_LLM=1 mode that replays a recorded trace so the demo never fails.
nexus/
docker-compose.yml
README.md
.env.example
seed/
generate.py # builds the synthetic graph + scenarios
scenarios.py # scenario definitions and alert payloads
engine/
db.py # FalkorDB connection helpers
paths.py # attack path discovery
risk.py # risk formula
impact.py # business impact
chokepoints.py # choke point metric
simulate.py # GRAPH.COPY sandboxes, action application
Page 2 of 77

## PDF page 3

NEXUS Build Specification (Track 1, Graph Hacks)
pareto.py # frontier and policy selection
execute.py # guarded execution, rollback, verification
mcp_server/
server.py # exposes the 6 tools over MCP
agent/
loop.py # LLM agent loop and system prompt
trace.py # structured trace recorder
api/
main.py # FastAPI: /alerts, /investigate, /approve,
/rollback, /graph
ui/
index.html, app.js, style.css
bench/
run_benchmark.py # random alerts vs brute force
tests/
test_engine.py
4. Step 0: verify the environment (do this first)
1. docker run -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest .
2. In Python, connect with FalkorDB(host='localhost', port=6379) and run a trivial
query.
3. Verify and record the result of each in a file docs/capabilities.md :
GRAPH.COPY works (Python client graph.copy('name') or raw GRAPH.COPY src
dst ).
Variable-length paths work: MATCH p=(a)-[*1..6]->(b) RETURN p .
Which of these procedures exist: run CALL dbms.procedures() and look for
algo.BFS , algo.SPpaths , algo.SSpaths , algo.pageRank , algo.betweenness ,
algo.WCC .
4. Decide the choke point method now: if algo.betweenness exists use it and call it
betweenness centrality. If not, use path coverage (section 7.4) and call it that
everywhere.
5. Graph schema
Use these labels and properties. Every node has id (unique string), name ,
synthetic=true , and status (default ACTIVE ).
Page 3 of 77

## PDF page 4

NEXUS Build Specification (Track 1, Graph Hacks)
Label Key properties
Person role, department, home_region
Device os, owner_id, patched (bool)
Server env (dev/prod), criticality (1-10), tier
ServiceAccount privilege (0-1), token_age_days, rotated (bool)
Service tier (1,2,3), revenue_weight, criticality
DataStore criticality (1-10), record_count, data_class (PII,
internal)
Vulnerability synth_id (for example SYNTH-VULN-2026-01),
cvss, exploitability (0-1)
IPAddress region, reputation
Alert type, severity_hint, raised_at, raw_text
Edge types, each with an exploit weight between 0 and 1 (probability an attacker can
traverse it) and an optional status (default ACTIVE):
(Person)-[:OWNS]->(Device)
(Device)-[:LOGS_INTO]->(Server)
(Server)-[:HOSTS_CREDENTIAL]->(ServiceAccount)
(ServiceAccount)-[:AUTHENTICATES_TO]->(Service)
(Service)-[:READS]->(DataStore)
(Person)-[:HAS_ACCESS_TO]->(Server)
(Server)-[:AFFECTED_BY]->(Vulnerability)
(Service)-[:DEPENDS_ON]->(Service) (used for business impact)
(Person)-[:USES]->(Service) (used for user impact)
(IPAddress)-[:USED_BY]->(Person)
(Alert)-[:ABOUT]->(Person|Device|ServiceAccount)
Attack traversal follows these edge types: OWNS, LOGS_INTO, HAS_ACCESS_TO,
HOSTS_CREDENTIAL, AUTHENTICATES_TO, READS. A node or edge whose status is
BLOCKED or ISOLATED is skipped.
Page 4 of 77

## PDF page 5

NEXUS Build Specification (Track 1, Graph Hacks)
Create indexes on id for each label.
6. Seed data and the three scenarios
seed/generate.py builds about 150 to 250 nodes: roughly 40 people, 50 devices, 25
servers, 12 service accounts, 20 services, 10 data stores, 8 vulnerabilities, plus IPs. Use a
fixed random seed so results are reproducible. Fill background nodes randomly with
sparse, mostly harmless connections, then plant the three scenario structures below.
Set exploit weights by edge type (for example OWNS 0.9, LOGS_INTO 0.7,
HOSTS_CREDENTIAL 0.6, AUTHENTICATES_TO 0.8, READS 0.9) and raise them when the
target server is AFFECTED_BY a vulnerability.
Scenario 1: Impossible travel (expected: isolate device)
Alert ALT-1042: Alex appears in Seattle and Sao Paulo within 14 minutes.
Planted chain: Alex -> LAPTOP-042 -> DEV-SERVER-03 -> SVC-ACCT-09 -> PROD-API -
> CUSTOMER-DB (1.25M PII records, criticality 10). DEV-SERVER-03 is AFFECTED_BY
SYNTH-VULN-2026-01 (CVSS 10.0, synthetic).
Add two more routes to CUSTOMER-DB that also pass through LAPTOP-042, so three
attack paths exist and all share that device.
PROD-API is tier 1 with many dependents, so disabling SVC-ACCT-09 has a large
business impact.
Result must emerge from computation: isolating the laptop breaks all paths with low
impact; disabling the service account breaks all paths with critical impact.
Scenario 2: Leaked service-account token (expected: disable service account)
Alert ALT-2071: SVC-ACCT-17 token used from an unknown external IP.
No device or person sits in front of it. Chain: SVC-ACCT-17 -> BILLING-SVC -> BILLING-
DB (PII, criticality 8).
BILLING-SVC is tier 3 with few dependents, so disabling the account has low to
medium impact.
Blocking the IP or isolating a device barely reduces risk because the attacker is already
inside the credential. Disabling the account must win.
Scenario 3: Benign anomaly (expected: monitor only)
Alert ALT-3310: Priya logs in from a new city.
Page 5 of 77

## PDF page 6

NEXUS Build Specification (Track 1, Graph Hacks)
Her devices and accounts reach only low-criticality internal assets (criticality 1 to 2).
Initial risk must land below the monitor threshold (default 25).
Expected decision: monitor only, no containment.
Each scenario in scenarios.py contains the alert id, a messy raw alert text (the LLM
must parse it), and the ground-truth entity ids used only by tests. Do not give the agent
the ground truth.
7. Engine specification (deterministic Python, no LLM)
7.1 Attack paths ( paths.py )
Function find_attack_paths(graph, start_ids, max_depth=7) returns every simple
path from the start entities to each crown-jewel node (DataStore with criticality >= 7),
skipping non-ACTIVE nodes and edges. Cypher pattern:
MATCH p=(s {id:$start})-
[:OWNS|LOGS_INTO|HAS_ACCESS_TO|HOSTS_CREDENTIAL|AUTHENTICATES_TO|READS*1..7]-
>(d:DataStore)
WHERE d.criticality >= 7
AND all(n IN nodes(p) WHERE n.status = 'ACTIVE')
AND all(r IN relationships(p) WHERE coalesce(r.status,'ACTIVE') = 'ACTIVE')
RETURN p
For each path return node ids, edge types, hop count, and exploitability = product of
edge exploit weights . Cap at 200 paths for safety.
7.2 Risk ( risk.py )
Print this formula in the README and show the term-by-term breakdown in the UI.
For each reachable crown jewel j:
p_j = 1 - product over paths i to j of (1 - exploitability_i) #
noisy-OR
priv_j = privilege of the last credential on the best path (default 0.5)
term_j = criticality_j * priv_j * p_j
raw = sum of term_j
risk = round(100 * (1 - exp(-raw / K))) # K = 6, saturating, document
it
label: <25 LOW, <50 MEDIUM, <75 HIGH, else CRITICAL
Page 6 of 77

## PDF page 7

NEXUS Build Specification (Track 1, Graph Hacks)
Tune K and edge weights once, before the demo, so the three scenarios land in sensible
bands. Document that tuning in the README. Do not tune afterward to flatter results.
7.3 Business impact ( impact.py )
For an action that disables a set of nodes N, find affected services S = services directly
reached via AUTHENTICATES_TO from N, plus services that DEPEND_ON them (up to 2
hops). Then:
service_weight = 10 for tier 1, 5 for tier 2, 1 for tier 3
raw = sum(service_weight) + 0.5 * count(distinct Person USES any service in
S)
impact = min(100, round(raw * 100 / IMPACT_CAP)) # IMPACT_CAP = 60
label: <20 LOW, <45 MEDIUM, <70 HIGH, else CRITICAL
Blocking an IP or revoking a user credential has its own small, computed impact: the user's
own productivity weight (one person) so impact is low but nonzero. Isolating a device
affects only that owner.
7.4 Choke points ( chokepoints.py )
If algo.betweenness is available, use it. Otherwise compute path coverage: for each
node, covered_paths / total_paths across the attack paths from 7.1. Return the top 5
with the node's metrics (token_age_days, historical alert count if you store it, number of
critical paths through it). Name the metric exactly as implemented.
7.5 Candidate actions and simulation ( simulate.py )
Actions: block_ip(ip_id) , isolate_device(device_id) ,
disable_account(account_id) , revoke_credentials(person_id) , and
monitor_only() (no change). Generate the candidates relevant to the alert entities.
For each candidate:
1. GRAPH.COPY nexus nexus_sim_<investigation>_<action> .
2. Apply the action to the copy by setting status (isolate_device: device status
ISOLATED and its LOGS_INTO edges BLOCKED; disable_account: account BLOCKED;
revoke_credentials: person's HAS_ACCESS_TO and OWNS edges BLOCKED; block_ip:
the IP BLOCKED and edges from it).
3. Re-run find_attack_paths and calculate_risk on the copy.
Page 7 of 77

## PDF page 8

NEXUS Build Specification (Track 1, Graph Hacks)
4. Record residual_risk , paths_broken (original minus remaining), and impact from
7.3.
5. Delete the sandbox graph.
Store the result list in an in-memory investigation record keyed by investigation id. This
record is what the execute tool checks.
8. Decision logic ( pareto.py )
1. Pareto frontier: an action is dominated if another action has residual_risk and impact
both less than or equal, with at least one strictly less. Keep the non-dominated set and
mark dominated actions with the action that dominates them. This is what lets the UI
say dominated, honestly.
2. Policy selection among the frontier:
If initial risk < MONITOR_THRESHOLD (25): choose monitor_only .
Else feasible = actions with residual_risk <= TARGET (40). Choose the feasible
action with the lowest impact, tie-broken by lower residual risk.
If none is feasible: choose the lowest residual risk and set requires_approval =
true .
3. Approval gate: if the chosen action's impact label is HIGH or CRITICAL, or
requires_approval is true, the action needs human approval via /approve . Otherwise
it auto-executes when the user presses CONTAIN (or immediately in autonomous
mode).
The LLM may propose a different action, but the policy result is shown alongside it and
execution is gated by the rules in section 9.
9. Execution, verification, rollback ( execute.py )
execute_containment(investigation_id, action) rejects unless that exact action
exists in the investigation's simulation record. Return a clear error the agent can read.
Apply the action to the live graph by writing status , blocked_by (the alert id), and
blocked_at (timestamp). Never delete nodes or edges.
Verification: re-run paths and risk on the live graph and return before and after values.
It must match the simulated residual risk within a small tolerance. If not, report a
mismatch.
Page 8 of 77

## PDF page 9

NEXUS Build Specification (Track 1, Graph Hacks)
Rollback: rollback(investigation_id) restores status to ACTIVE and removes the
blocked_* properties for everything that investigation changed. Keep a change log per
investigation.
Write an Investigation node linked to the Alert recording the decision, scores, and
timestamps (audit trail).
10. MCP server ( mcp_server/server.py )
Expose exactly these tools using the Python MCP SDK. Each returns structured JSON
including the Cypher actually run (so the UI can show it).
Tool Inputs Returns
resolve_entities raw_text or entity names matched node ids and types, plus
unmatched strings
find_attack_paths start_ids, max_depth list of paths with hops and
exploitability, plus the Cypher
blast_radius start_ids counts and lists of reachable nodes
by label
calculate_risk start_ids score, label, per-jewel breakdown,
formula inputs
find_choke_points start_ids, top_n ranked nodes with metric name and
values
simulate_containment start_ids, alert_id matrix of actions with residual risk,
paths broken, impact, Pareto flags,
policy recommendation
execute_containment investigation_id, action, before and after risk, change log
approved (guarded as in section 9)
The seventh tool, resolve_entities , replaces the LLM parsing job so the model can
ground entities against the graph rather than guess.
Page 9 of 77

## PDF page 10

NEXUS Build Specification (Track 1, Graph Hacks)
11. Agent loop ( agent/loop.py )
The LLM receives the raw alert text and calls the MCP tools. Implement the loop yourself:
send messages with tool definitions, run tool calls, append results, repeat until the model
returns a final answer or 12 steps pass.
System prompt requirements
Role: SOC investigation agent. You must ground every claim in tool output.
Procedure: resolve entities, find attack paths, calculate risk, find choke points,
simulate containment, pick an action, execute, then verify with a final risk calculation.
If no paths are found, widen the search (higher depth, or add related entities such as
the owner or devices) before concluding.
If an asset has missing data (for example no vulnerability record), say so explicitly
under a Missing evidence heading.
Never execute an action that was not returned by simulate_containment. Respect
requires_approval and stop to ask when it is true.
Final answer format: Decision, Evidence (cite node and edge ids from tool results),
Alternatives considered with their numbers, Missing evidence, Verification.
Do not reveal hidden reasoning. Present observations, evidence, decision, action, and
verification only.
Trace recorder ( trace.py )
Record every step as an object with step number, tool name, arguments, the Cypher run, a
short result summary, and duration in ms. Emit these to the UI over a server-sent events
stream.
Mock mode
With MOCK_LLM=1 , replay a saved trace per scenario (recorded from a real run) while still
running the real engine against the real graph. This is the safety net for demos and the
judges' machines.
Page 10 of 77

## PDF page 11

NEXUS Build Specification (Track 1, Graph Hacks)
12. API and UI
API ( api/main.py )
GET /alerts lists the three scenario alerts.
POST /investigate {alert_id} starts the agent and streams trace events (SSE).
POST /approve {investigation_id, action} and POST /rollback
{investigation_id} .
GET /graph?investigation_id= returns nodes and edges for the subgraph of the
attack paths, with status flags.
UI layout (decision first)
1. Decision card (hero): alert id and title, risk score and label, number of attack paths,
crown jewel exposed (for example 1.25M PII records), recommended action, and a
CONTAIN button. Show a Needs approval badge when applicable.
2. Containment matrix: one row per action with residual risk, paths broken, impact label,
a Pareto badge, and the dominated-by note. Highlight the selected row.
3. Agent trace: the live list of tool calls with arguments and results. Each has a Show
Cypher toggle.
4. Risk breakdown: a popover that prints the formula with the real numbers behind the
score.
5. Graph view: the attack subgraph with the attack paths highlighted. After containment,
blocked nodes turn red or grey and the paths disappear, with a before and after risk
readout.
6. Controls: scenario picker for the three alerts, a Rollback button, and a visible
SYNTHETIC DATA label.
Keep styling plain and readable. Dark or light theme is fine. Do not spend time on
animation.
13. Benchmark ( bench/run_benchmark.py )
1. Generate 30 alerts by picking random Person, Device, or ServiceAccount entities from
the graph (include the 3 scenarios plus random ones).
2. For each, brute-force every candidate action with the engine (section 7.5), apply the
same policy from section 8, and record the optimal action.
Page 11 of 77

## PDF page 12

NEXUS Build Specification (Track 1, Graph Hacks)
3. Run the agent (real LLM) on each alert and record its executed action.
4. Report agreement rate, the confusion list, and the cases where the agent differed,
with a one-line reason for each miss.
5. Write the results to bench/results.md and put the headline number and an honest
miss analysis in the README. Publish misses; do not hide them.
If time is short, run the benchmark with fewer alerts and say so.
14. Tests ( tests/test_engine.py )
Scenario 1 initial risk is in the CRITICAL band, three paths exist, and the selected action
is isolate_device.
Scenario 2 selected action is disable_account.
Scenario 3 selected action is monitor_only.
Executing an action that was not simulated is rejected.
Rollback restores the original risk exactly.
Verification risk after execution equals simulated residual risk.
Sandbox graphs are deleted after simulation.
The build is not done until all of these pass.
15. Build order with gates
Phase A: foundation (Oct 15)
1. Environment check and docs/capabilities.md (section 4).
2. Schema, indexes, seed generator, the three planted scenarios.
3. Engine: paths, risk, impact, choke points. Gate: a script prints the three scenarios with
initial risk and choke points, and numbers look sensible.
Phase B: decisions (Oct 16) 4. Simulation on GRAPH.COPY , Pareto, policy, execution,
rollback. Gate: the three scenarios give three different decisions and tests in section 14
pass. 5. MCP server with all tools. Gate: each tool can be called from an MCP client. 6.
Agent loop and trace. Gate: scenario 1 runs end to end from raw alert text to verified
containment.
Phase C: product (Oct 17) 7. FastAPI and UI (decision card, matrix, trace, graph). Run all
three scenarios through the UI. 8. Mock mode, docker compose up (services: falkordb,
app; the app seeds on startup). 9. Benchmark. README with architecture diagram,
Page 12 of 77

## PDF page 13

NEXUS Build Specification (Track 1, Graph Hacks)
formula, limitations. Draft the blog post.
Phase D: ship (Oct 18) 10. Record the 90-second video (script in section 16), fix bugs, test
a fresh clone on a clean machine, submit by early afternoon.
Fallback order if behind: shrink the benchmark, then skip rollback UI polish, then drop
scenario 3 UI (keep it in tests). Never drop live simulation or scenario 2.
16. Deliverables
README: one-paragraph pitch, architecture diagram (LLM orchestrates, FalkorDB
grounds, deterministic engine constrains), formulas, how to run, benchmark table,
limitations, synthetic data notice.
Video, 90 seconds: 0 to 10s decision card appears; 10 to 35s agent trace with real tool
calls and a real path; 35 to 60s containment matrix and Pareto note (it chose the safest
action, not the lowest theoretical risk); 60 to 80s contain, graph mutates, before and
after verified, quick cut to scenario 2 with a different decision; 80 to 90s benchmark
number and the thesis line.
Blog post: the design story, why the graph is the decision substrate, how GRAPH.COPY
powers counterfactuals, the benchmark and its misses, what you would do next. This
targets the AirPods side prize.
Submission: public repo, video, README, and any hosted demo link. Read the Rules
and FAQ tabs on the hackathon page for exact requirements before submitting.
The one-line thesis for the pitch: the LLM orchestrates the investigation, FalkorDB
provides the ground truth, and deterministic graph analysis constrains the action.
17. Common pitfalls
Variable-length path queries can explode. Always cap depth and path count.
Forgetting to filter on status makes containment appear to do nothing.
Leaving sandbox graphs behind. Always delete them in a finally block.
Tuning weights after seeing results to make a scenario look good. Tune once, document
it, then freeze.
Letting the LLM state numbers. It must quote tool outputs.
Overbuilding the UI. A plain decision card and a real trace beat polish.
Page 13 of 77

## PDF page 14

NEXUS Build Specification (Track 1, Graph Hacks)
Part B: The Complete A-to-Z Guide (Start
Here If You Are New)
Part A above is the specification: what to build and why. Part B is the walkthrough: every
install, every command and every file, in the order you do them, written for someone who
has never used a graph database, Docker, or an AI agent. Follow it top to bottom and do
not skip the checkpoints.
Where Part A and Part B differ, Part B wins, because Part B is the code and the decisions
worked out end to end. The differences:
The risk constant is K = 4 in the starter code (Part A said 6). K only controls how fast
the score saturates toward 100.
Attack paths are measured from one start entity (the alert's subject), not a list.
Blocking an IP and revoking credentials are modelled as reductions in exploit
probability (constants IP_FACTOR and REVOKE_FACTOR), because an attacker may
already hold a live session. Write this down in your README as a modelling
assumption.
The agent calls the tool functions directly. The same functions are also exposed
through an MCP server so any external MCP client can use them. There are 8 tools
(the 7 in Part A plus rollback).
The numbers will not match the pitch examples (96, 31, 18). They come out of the
computation. If a scenario returns a different number, the computation is right and the
pitch text should change to match it.
B1. What you are building, in plain English
Imagine a security guard at a company. An alarm rings: an employee seems to have logged
in from two countries within minutes. A weak guard sees one odd login. A great guard
pulls out a map of the company and asks: if this person's laptop is taken over, what else
can the attacker reach, step by step, and could that end at the customer database?
NEXUS is that great guard, as software:
1. The company map is stored in a graph database (FalkorDB). People, laptops, servers,
accounts and databases are dots (nodes); the ways one can reach another are lines
(edges).
Page 14 of 77

## PDF page 15

NEXUS Build Specification (Track 1, Graph Hacks)
2. An AI model reads the alert, decides which questions to ask the map, and writes the
explanation.
3. Plain Python code (not the AI) does the maths: finds attack routes, computes a risk
score, and tests what happens if we cut each route in a copy of the map.
4. The agent picks the action with the best trade-off between safety and business
disruption, applies it to the real map, and re-checks.
The key idea judges will reward: the graph is not decoration. Without it, the agent has no
way to know which action is safe.
B2. Glossary (read once, refer back)
Word Meaning in this project
Graph database A database that stores things (nodes) and the
connections between them (edges) directly, so
following connections is fast and simple
Node One thing: a person, laptop, server, service
account, database
Edge / relationship A typed link between two nodes, for example a
laptop LOGS_INTO a server
Property A named value on a node or edge, for example
criticality = 10
Label The type of a node, for example Person or Server
FalkorDB The open-source graph database used in this
hackathon. It speaks the Cypher language
Cypher The query language for graphs. MATCH finds
patterns, RETURN gives results, CREATE and SET
change data
Multi-hop Following several edges in a row, for example Alex
to laptop to server to account to service to
database
GRAPH.COPY A FalkorDB command that duplicates a whole
graph under a new name. We use copies as safe
sandboxes for what-if tests
Page 15 of 77

## PDF page 16

NEXUS Build Specification (Track 1, Graph Hacks)
Word Meaning in this project
Docker A tool that runs software in a ready-made box
called a container, so you do not install the
database by hand
docker compose A way to start several containers (database and
app) with one command
Python virtual environment A private folder of Python packages for one project
so versions do not clash
API A set of web addresses a program can call. Our
backend offers /api/investigate and others
FastAPI The Python library that builds that backend
LLM Large language model, the AI that reads text and
decides what to do next
Tool call The LLM asking our code to run a named function,
such as find_attack_paths, and receiving the result
Agent An LLM in a loop: think, call a tool, read the result,
repeat until it can answer
MCP Model Context Protocol, a standard way to publish
tools so any AI client can discover and call them
Attack path A chain of edges an attacker could follow from a
compromised entity to a valuable asset
Crown jewel A highly valuable asset, here a DataStore with
criticality 7 or more
Blast radius Everything reachable from the compromised entity
Choke point A node that many attack paths pass through, so
cutting it breaks many paths
Containment An action that stops the attack, such as isolating a
laptop or disabling an account
Counterfactual simulation Asking what would happen if we did action X, by
trying X on a copy of the graph
Page 16 of 77

## PDF page 17

NEXUS Build Specification (Track 1, Graph Hacks)
Word Meaning in this project
Pareto frontier The set of options where no other option is better
on both measures at once (here: residual risk and
business impact)
Synthetic data Made-up data. All data in this project is fake and
must be labelled so
B3. Your time plan (about 3.5 days)
Block What you do Done when
Today, hours 1 Sections B4 to B6: install tools, Every version command in B4
to 2 create project prints a number
Today, hours 3 B7: start FalkorDB, run the You can see the graph browser and
to 4 capability check the check prints GRAPH.COPY ok
Today, hours 5 B8 to B10: database helper, seed The demo script prints three
to 8 data, paths, risk, impact scenarios with sensible risk bands
Day 2 morning B11 to B13: simulation, Pareto, Tests for the three decisions pass
execute, tools
Day 2 afternoon B14 to B16: agent, API A curl call returns a full
investigation
Day 3 morning B17 to B18: UI, docker compose docker compose up works from a
clean folder
Day 3 afternoon B19 to B21: tests, benchmark, MCP Benchmark file exists
server
Day 4 (deadline B22 to B24: README, video, blog, Submitted by early afternoon IST
day) submit
If you are stuck for more than 30 minutes on one thing, copy the exact error message to
an AI assistant or ask in the FalkorDB Discord linked on the hackathon page. Do not
silently lose hours.
Page 17 of 77

## PDF page 18

NEXUS Build Specification (Track 1, Graph Hacks)
B4. Install the tools
You need five things: Git, Python 3.11 or newer, Docker Desktop, a code editor (VS Code),
and optionally an API key for an AI model.
Windows
1. Install Git from git-scm.com (accept the defaults).
2. Install Python from python.org. On the first screen tick Add python.exe to PATH.
3. Install Docker Desktop from docker.com and restart when asked. Open it once and
wait until it says Docker is running.
4. Install VS Code from code.visualstudio.com, then add the Python extension.
Mac
1. Install Homebrew from brew.sh, then run: brew install git python@3.11
2. Install Docker Desktop for Mac from docker.com and open it once.
3. Install VS Code and the Python extension.
Linux (Ubuntu)
1. sudo apt update && sudo apt install -y git python3 python3-venv python3-pip
2. Install Docker Engine following docs.docker.com, then add yourself to the docker
group and log in again.
3. Install VS Code.
Check everything. Open a terminal (PowerShell on Windows, Terminal on Mac and Linux)
and run:
git --version
python --version
docker --version
docker run hello-world
On Mac and Linux use python3 if python is not found. You should see version numbers
and a message starting Hello from Docker. If docker run fails, open Docker Desktop and
wait for it to finish starting.
AI key (optional but recommended). The project has a mock mode that needs no key, so
you can build and test everything without one. For the real agent, create an account with
an AI provider that supports tool calling (the examples use the Anthropic API,
Page 18 of 77

## PDF page 19

NEXUS Build Specification (Track 1, Graph Hacks)
console.anthropic.com), create an API key, and keep it secret. Never paste it into code or
commit it to Git.
B5. Create the project
In the terminal:
mkdir nexus
cd nexus
git init
python -m venv .venv
Activate the virtual environment (you must do this every time you open a new terminal):
# Windows PowerShell
.venv/Scripts/Activate.ps1
# Mac and Linux
source .venv/bin/activate
Your prompt should now start with (.venv). Open the folder in VS Code (code . in the
terminal) and create these folders and empty files using the VS Code explorer (right-click,
New Folder or New File). The empty init.py files are required so Python treats folders as
packages.
nexus/
seed/__init__.py
engine/__init__.py
agent/__init__.py
api/__init__.py
mcp_server/__init__.py
bench/__init__.py
tests/__init__.py
ui/ (index.html will go here)
data/ (investigation records are written here)
Create requirements.txt in the project root:
Page 19 of 77

## PDF page 20

NEXUS Build Specification (Track 1, Graph Hacks)
falkordb
fastapi
uvicorn
mcp
anthropic
pydantic
pytest
python-dotenv
requests
Install them:
pip install -r requirements.txt
Create .env.example (copy it to .env and fill in real values; add .env to a .gitignore file so it
is never committed):
FALKOR_HOST=localhost
FALKOR_PORT=6379
ANTHROPIC_API_KEY=
NEXUS_MODEL=claude-sonnet-5-5
MOCK_LLM=1
Set MOCK_LLM=1 until your real key works. Create .gitignore containing these lines:
.venv, .env, data/, pycache.
B6. Cypher in five minutes
Cypher draws pictures with text. Round brackets are nodes, square brackets are edges,
arrows show direction.
Page 20 of 77

## PDF page 21

NEXUS Build Specification (Track 1, Graph Hacks)
// create two nodes and one edge
CREATE (:Person {id:'U1', name:'Ann'})-[:OWNS]->(:Device {id:'D1', name:'Ann
laptop'})
// find everything Ann owns
MATCH (p:Person {id:'U1'})-[:OWNS]->(d) RETURN d.name
// follow up to 3 hops of any type
MATCH (a {id:'U1'})-[*1..3]->(b) RETURN b.id
// change a property
MATCH (d:Device {id:'D1'}) SET d.status = 'ISOLATED'
// count nodes by label
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS c
Six words cover most of the project: MATCH (find), WHERE (filter), RETURN (output),
CREATE or MERGE (add; MERGE avoids duplicates), SET (change a value), and the
pattern [*1..7] (follow 1 to 7 hops).
B7. Start FalkorDB and verify it
Run the database (leave this terminal open, or add -d to run in the background):
docker run -p 6379:6379 -p 3000:3000 --name falkordb falkordb/falkordb:latest
Open http://localhost:3000 in your browser. This is the FalkorDB Browser where you can
type Cypher and see the graph drawn. Port 6379 is what your Python code connects to.
Next, create check_capabilities.py in the project root and run it with python
check_capabilities.py. It proves the features this project depends on exist in your
installed version.
Page 21 of 77

## PDF page 22

NEXUS Build Specification (Track 1, Graph Hacks)
from falkordb import FalkorDB
c = FalkorDB(host='localhost', port=6379)
g = c.select_graph('cap_test')
g.query('CREATE (:A {id:1})-[:R]->(:B {id:2})')
print('query ok')
try:
cp = g.copy('cap_test_copy')
print('GRAPH.COPY ok')
cp.delete()
except Exception as e:
print('GRAPH.COPY FAILED:', e)
rows = g.query('CALL dbms.procedures() YIELD name RETURN name').result_set
for name in sorted(r[0] for r in rows):
print(name)
g.delete()
Checkpoint: you see query ok, GRAPH.COPY ok, then a list of procedure names. Save the
list into docs/capabilities.md. If you see algo.betweenness in the list you may use it for
choke points; the starter code uses path coverage, which always works.
If GRAPH.COPY fails, upgrade the image (docker pull falkordb/falkordb:latest, then
recreate the container). If it still fails, use the fallback in section B25 (pitfalls).
B8. The database helper (engine/db.py)
One small file that every other file uses to talk to FalkorDB. It retries the connection so
docker compose start-up order does not matter.
import os
import time
from falkordb import FalkorDB
HOST = os.getenv('FALKOR_HOST', 'localhost')
PORT = int(os.getenv('FALKOR_PORT', '6379'))
MAIN = 'nexus'
_client = None
def client():
Page 22 of 77

## PDF page 23

NEXUS Build Specification (Track 1, Graph Hacks)
global _client
if _client is None:
last = None
for _ in range(30):
try:
c = FalkorDB(host=HOST, port=PORT)
c.list_graphs()
_client = c
break
except Exception as e:
last = e
time.sleep(1)
if _client is None:
raise RuntimeError('Cannot reach FalkorDB: %s' % last)
return _client
def graph(name=MAIN):
return client().select_graph(name)
B9. The synthetic company and the three scenarios
(seed/generate.py)
This file builds a fake company of roughly 175 nodes. First it creates a harmless
background estate (people, laptops, servers, accounts, services, low-value databases),
then it plants the three scenarios. The background has no crown jewels, so it never
creates accidental attack paths. All data is marked synthetic.
What each scenario is designed to prove:
Scenario Alert Planted structure Expected decision
subject
1 U-ALEX Alex owns LAPTOP-042, which Isolate LAPTOP-042 (disabling
logs into three servers that all the account also works but
host the credential of SVC- causes huge outage)
ACCT-09, which feeds PROD-API
(tier 1, many dependents), which
reads CUSTOMER-DB (1.25M PII
records)
Page 23 of 77

## PDF page 24

NEXUS Build Specification (Track 1, Graph Hacks)
Scenario Alert Planted structure Expected decision
subject
2 SVC- A leaked token for a lone Disable SVC-ACCT-17 (no
ACCT-17 account that feeds a small tier 3 device to isolate, low outage)
billing service reading BILLING-
DB
3 U-PRIYA Priya reaches only low-value Monitor only
internal data
import random
from engine.db import client, MAIN
random.seed(42)
ROLES = ['engineer', 'analyst', 'sales', 'support', 'finance', 'hr']
LABELS = ['Person', 'Device', 'Server', 'ServiceAccount', 'Service',
'DataStore', 'Vulnerability', 'IPAddress', 'Alert']
def node(g, label, nid, **p):
p['id'] = nid
p['synthetic'] = True
p.setdefault('name', nid)
p.setdefault('status', 'ACTIVE')
g.query('MERGE (n:%s {id:$id}) SET n += $p' % label, {'id': nid, 'p': p})
def edge(g, a, b, rel, w):
q = ('MATCH (a {id:$a}), (b {id:$b}) '
'MERGE (a)-[r:%s]->(b) SET r.exploit=$w, r.status=$s' % rel)
g.query(q, {'a': a, 'b': b, 'w': w, 's': 'ACTIVE'})
def alert(g, aid, atype, about, text):
node(g, 'Alert', aid, type=atype, raw_text=text)
g.query('MATCH (a {id:$a}), (e {id:$e}) MERGE (a)-[:ABOUT]->(e)',
{'a': aid, 'e': about})
def background(g):
for i in range(10):
node(g, 'DataStore', 'DS-BG-%02d' % i, criticality=random.randint(1,
4),
record_count=random.randint(100, 5000), data_class='internal')
for i in range(12):
Page 24 of 77

## PDF page 25

NEXUS Build Specification (Track 1, Graph Hacks)
node(g, 'Service', 'SVC-BG-%02d' % i, tier=random.choice([2, 3]),
criticality=random.randint(1, 4))
edge(g, 'SVC-BG-%02d' % i, 'DS-BG-%02d' % random.randint(0, 9),
'READS', 0.8)
for i in range(12):
node(g, 'ServiceAccount', 'ACC-BG-%02d' % i,
privilege=round(random.uniform(0.2, 0.5), 2),
token_age_days=random.randint(5, 200), rotated=True)
edge(g, 'ACC-BG-%02d' % i, 'SVC-BG-%02d' % i, 'AUTHENTICATES_TO',
0.7)
for i in range(20):
node(g, 'Server', 'SRV-BG-%02d' % i, env=random.choice(['dev',
'prod']),
criticality=random.randint(1, 4))
edge(g, 'SRV-BG-%02d' % i, 'ACC-BG-%02d' % random.randint(0, 11),
'HOSTS_CREDENTIAL', 0.5)
for i in range(40):
node(g, 'Person', 'U-BG-%02d' % i, role=random.choice(ROLES))
node(g, 'Device', 'DEV-BG-%02d' % i, os=random.choice(['win', 'mac',
'linux']),
patched=random.random() > 0.3)
edge(g, 'U-BG-%02d' % i, 'DEV-BG-%02d' % i, 'OWNS', 0.9)
edge(g, 'DEV-BG-%02d' % i, 'SRV-BG-%02d' % random.randint(0, 19),
'LOGS_INTO', 0.6)
edge(g, 'U-BG-%02d' % i, 'SVC-BG-%02d' % random.randint(0, 11),
'USES', 0.0)
def scenario1(g):
node(g, 'Person', 'U-ALEX', name='alex.m', role='engineer',
home_region='Seattle')
node(g, 'Device', 'LAPTOP-042', owner_id='U-ALEX', os='win',
patched=False)
for sid in ['DEV-SERVER-03', 'DEV-SERVER-07', 'JUMPBOX-01']:
node(g, 'Server', sid, env='dev', criticality=5)
node(g, 'Vulnerability', 'SYNTH-VULN-2026-01', cvss=10.0,
exploitability=0.9,
note='synthetic vulnerability for the demo')
node(g, 'ServiceAccount', 'SVC-ACCT-09', privilege=0.9,
token_age_days=184, rotated=False)
node(g, 'Service', 'PROD-API', tier=1, criticality=9)
node(g, 'Service', 'WEB-FRONTEND', tier=1, criticality=8)
node(g, 'Service', 'PAYMENTS-SVC', tier=1, criticality=9)
node(g, 'Service', 'MOBILE-APP', tier=2, criticality=6)
Page 25 of 77

## PDF page 26

NEXUS Build Specification (Track 1, Graph Hacks)
node(g, 'DataStore', 'CUSTOMER-DB', criticality=10, record_count=1250000,
data_class='PII')
node(g, 'IPAddress', 'IP-203-0-113-77', region='BR',
reputation='suspicious')
edge(g, 'U-ALEX', 'LAPTOP-042', 'OWNS', 0.9)
for sid, w in [('DEV-SERVER-03', 0.8), ('DEV-SERVER-07', 0.6), ('JUMPBOX-
01', 0.6)]:
edge(g, 'LAPTOP-042', sid, 'LOGS_INTO', w)
edge(g, sid, 'SVC-ACCT-09', 'HOSTS_CREDENTIAL', 0.8)
edge(g, 'DEV-SERVER-03', 'SYNTH-VULN-2026-01', 'AFFECTED_BY', 1.0)
edge(g, 'SVC-ACCT-09', 'PROD-API', 'AUTHENTICATES_TO', 0.8)
edge(g, 'PROD-API', 'CUSTOMER-DB', 'READS', 0.9)
for d in ['WEB-FRONTEND', 'PAYMENTS-SVC', 'MOBILE-APP']:
edge(g, d, 'PROD-API', 'DEPENDS_ON', 0.0)
for i in range(30):
edge(g, 'U-BG-%02d' % i,
random.choice(['WEB-FRONTEND', 'PAYMENTS-SVC', 'MOBILE-APP',
'PROD-API']),
'USES', 0.0)
edge(g, 'IP-203-0-113-77', 'U-ALEX', 'USED_BY', 0.0)
alert(g, 'ALT-1042', 'IMPOSSIBLE_TRAVEL', 'U-ALEX',
'ALT-1042 | IMPOSSIBLE_TRAVEL | user alex.m logged in from Seattle
US then '
'Sao Paulo BR 14 min apart | device LAPTOP-042 | src_ip
203.0.113.77')
def scenario2(g):
node(g, 'ServiceAccount', 'SVC-ACCT-17', privilege=0.7,
token_age_days=412, rotated=False)
node(g, 'Service', 'BILLING-SVC', tier=3, criticality=5)
node(g, 'DataStore', 'BILLING-DB', criticality=8, record_count=300000,
data_class='PII')
node(g, 'IPAddress', 'IP-198-51-100-23', region='unknown',
reputation='malicious')
edge(g, 'SVC-ACCT-17', 'BILLING-SVC', 'AUTHENTICATES_TO', 0.9)
edge(g, 'BILLING-SVC', 'BILLING-DB', 'READS', 0.9)
edge(g, 'IP-198-51-100-23', 'SVC-ACCT-17', 'USED_BY', 0.0)
for i in range(30, 34):
edge(g, 'U-BG-%02d' % i, 'BILLING-SVC', 'USES', 0.0)
alert(g, 'ALT-2071', 'LEAKED_TOKEN', 'SVC-ACCT-17',
'ALT-2071 | LEAKED_TOKEN | service account SVC-ACCT-17 token used
from unknown '
'external ip 198.51.100.23 outside normal hours')
Page 26 of 77

## PDF page 27

NEXUS Build Specification (Track 1, Graph Hacks)
def scenario3(g):
node(g, 'Person', 'U-PRIYA', name='priya.k', role='analyst',
home_region='Pune')
node(g, 'Device', 'LAPTOP-PRIYA', owner_id='U-PRIYA', os='mac',
patched=True)
node(g, 'IPAddress', 'IP-192-0-2-8', region='IN', reputation='clean')
edge(g, 'U-PRIYA', 'LAPTOP-PRIYA', 'OWNS', 0.9)
edge(g, 'LAPTOP-PRIYA', 'SRV-BG-03', 'LOGS_INTO', 0.6)
edge(g, 'IP-192-0-2-8', 'U-PRIYA', 'USED_BY', 0.0)
alert(g, 'ALT-3310', 'NEW_LOCATION_LOGIN', 'U-PRIYA',
'ALT-3310 | NEW_LOCATION_LOGIN | user priya.k signed in from a new
city (Jaipur IN) '
'| device LAPTOP-PRIYA | src_ip 192.0.2.8')
def build():
c = client()
try:
c.select_graph(MAIN).delete()
except Exception:
pass
g = c.select_graph(MAIN)
for label in LABELS:
g.query('CREATE INDEX FOR (n:%s) ON (n.id)' % label)
background(g)
scenario1(g)
scenario2(g)
scenario3(g)
n = g.query('MATCH (n) RETURN count(n)').result_set[0][0]
print('seeded nodes:', n)
if __name__ == '__main__':
build()
Run it from the project root (the folder that contains seed and engine):
python -m seed.generate
Checkpoint: it prints seeded nodes with a number around 170 to 180. Open the Browser at
localhost:3000, choose the graph named nexus and run MATCH (a:Alert)-[:ABOUT]->(e)
RETURN a, e to see your three alerts.
Page 27 of 77

## PDF page 28

NEXUS Build Specification (Track 1, Graph Hacks)
If SET n += $p gives a syntax error on your version, replace it with one SET per property in
a loop. Everything else stays the same.
B10. The engine, part 1: paths, risk, impact
engine/paths.py
Finds every route from the start entity to a crown jewel, ignoring anything whose status is
not ACTIVE. That status filter is how containment actions take effect later.
Q = '''
MATCH p=(s {id:$start})-
[:OWNS|LOGS_INTO|HAS_ACCESS_TO|HOSTS_CREDENTIAL|AUTHENTICATES_TO|READS*1..7]-
>(d:DataStore)
WHERE d.criticality >= $minc
AND all(n IN nodes(p) WHERE coalesce(n.status,'ACTIVE') = 'ACTIVE')
AND all(r IN relationships(p) WHERE coalesce(r.status,'ACTIVE') = 'ACTIVE')
RETURN [n IN nodes(p) | n.id] AS ids,
[r IN relationships(p) | type(r)] AS types,
[r IN relationships(p) | r.exploit] AS ex,
[n IN nodes(p) | coalesce(n.privilege, -1.0)] AS priv,
d.id AS target, d.criticality AS crit
LIMIT $limit
'''
def find_attack_paths(g, start_id, max_depth=7, min_crit=7, limit=200):
q = Q.replace('*1..7', '*1..%d' % max_depth)
rows = g.query(q, {'start': start_id, 'minc': min_crit, 'limit':
limit}).result_set
out = []
for ids, types, ex, priv, target, crit in rows:
if len(set(ids)) != len(ids):
continue
e = 1.0
for x in ex:
e *= (x if x is not None else 0.5)
out.append({'ids': ids, 'types': types, 'exploit': round(e, 4),
'priv': priv, 'target': target, 'crit': crit, 'hops':
len(types)})
return {'paths': out, 'cypher': q.strip()}
Page 28 of 77

## PDF page 29

NEXUS Build Specification (Track 1, Graph Hacks)
engine/risk.py
The formula from Part A, in code. Every term is returned so the UI can show how the score
was built.
import math
K = 4.0
def band(score):
if score < 25:
return 'LOW'
if score < 50:
return 'MEDIUM'
if score < 75:
return 'HIGH'
return 'CRITICAL'
def calculate_risk(paths):
by_target = {}
for p in paths:
by_target.setdefault(p['target'], []).append(p)
terms = []
raw = 0.0
for target, ps in by_target.items():
miss = 1.0
for p in ps:
miss *= (1.0 - p['exploit'])
prob = 1.0 - miss
priv = max([max(p['priv']) for p in ps] + [0.0])
if priv <= 0:
priv = 0.5
crit = ps[0]['crit']
term = crit * priv * prob
raw += term
terms.append({'target': target, 'criticality': crit, 'privilege':
priv,
'reach_probability': round(prob, 3), 'paths': len(ps),
'term': round(term, 3)})
score = round(100 * (1 - math.exp(-raw / K)))
return {'score': score, 'label': band(score), 'raw': round(raw, 3), 'K':
K, 'terms': terms}
Page 29 of 77

## PDF page 30

NEXUS Build Specification (Track 1, Graph Hacks)
engine/impact.py
Business impact is measured by what would stop working: the services behind an
account, plus anything that depends on them, plus the people who use them.
CAP = 60.0
WEIGHT = {1: 10, 2: 5, 3: 1}
PERSON_WEIGHT = 0.5
def label(x):
if x < 20:
return 'LOW'
if x < 45:
return 'MEDIUM'
if x < 70:
return 'HIGH'
return 'CRITICAL'
def affected_services(g, account_id):
q = 'MATCH (a {id:$id})-[:AUTHENTICATES_TO]->(s:Service) RETURN s.id'
direct = [r[0] for r in g.query(q, {'id': account_id}).result_set]
if not direct:
return []
q2 = ('MATCH (d:Service)-[:DEPENDS_ON*1..2]->(s:Service) '
'WHERE s.id IN $ids RETURN DISTINCT d.id')
deps = [r[0] for r in g.query(q2, {'ids': direct}).result_set]
return sorted(set(direct + deps))
def action_impact(g, action, target):
if action == 'monitor_only':
return {'impact': 0, 'label': 'LOW', 'services': [], 'users': 0}
if action != 'disable_account':
raw = PERSON_WEIGHT
score = min(100, round(raw * 100 / CAP))
return {'impact': score, 'label': label(score), 'services': [],
'users': 1}
svcs = affected_services(g, target)
tiers = g.query('MATCH (s:Service) WHERE s.id IN $ids RETURN s.tier',
{'ids': svcs}).result_set
raw = sum(WEIGHT.get(r[0], 1) for r in tiers)
users = g.query('MATCH (u:Person)-[:USES]->(s:Service) WHERE s.id IN $ids
'
'RETURN count(DISTINCT u)', {'ids': svcs}).result_set[0]
Page 30 of 77

## PDF page 31

NEXUS Build Specification (Track 1, Graph Hacks)
[0]
raw += PERSON_WEIGHT * users
score = min(100, round(raw * 100 / CAP))
return {'impact': score, 'label': label(score), 'services': svcs,
'users': users}
scripts_demo.py (checkpoint script, project root)
from engine.db import graph
from engine import paths, risk, impact
g = graph()
for start in ['U-ALEX', 'SVC-ACCT-17', 'U-PRIYA']:
res = paths.find_attack_paths(g, start)
r = risk.calculate_risk(res['paths'])
print(start, 'paths:', len(res['paths']), 'risk:', r['score'],
r['label'])
for p in res['paths']:
print(' ', ' > '.join(p['ids']), 'exploit', p['exploit'])
print('impact if SVC-ACCT-09 disabled:', impact.action_impact(g,
'disable_account', 'SVC-ACCT-09'))
print('impact if SVC-ACCT-17 disabled:', impact.action_impact(g,
'disable_account', 'SVC-ACCT-17'))
Run python scripts_demo.py.
Checkpoint (this is gate A): you should see roughly this, give or take a few points:
Start Expected
U-ALEX 3 paths, risk about 80, CRITICAL
SVC-ACCT-17 1 path, risk about 68, HIGH
U-PRIYA 0 paths, risk 0, LOW
SVC-ACCT-09 disabled impact CRITICAL (around 80)
SVC-ACCT-17 disabled impact LOW (around 5)
If the numbers are far off, check the edge weights in seed/generate.py first, then K in
risk.py. Tune once, write down what you changed in the README, then freeze. Do not tune
later to flatter a result.
Page 31 of 77

## PDF page 32

NEXUS Build Specification (Track 1, Graph Hacks)
B11. The engine, part 2: actions and simulation (engine/simulate.py)
This is the heart of the project. For every candidate action it copies the whole graph,
applies the action to the copy only, re-runs the path search and risk calculation, records
the result and deletes the copy. The live graph is never touched during simulation.
How each action changes a graph (the same code is used on copies and on the live graph):
Action Effect
isolate_device The device gets status ISOLATED. Path search
skips non-active nodes, so every route through it
disappears
disable_account The service account gets status BLOCKED, same
effect
revoke_credentials The person's HAS_ACCESS_TO edges become
BLOCKED, and the person's OWNS edges lose 30
percent of their exploit weight (a stolen session is
cut but the device may still be compromised)
block_ip The IP gets status BLOCKED and the subject's
outgoing edges lose 40 percent of their exploit
weight (the easy remote route is closed but the
attacker may use another)
monitor_only Nothing changes
The two percentages are modelling assumptions (IP_FACTOR and REVOKE_FACTOR).
Say so in your README.
import time
import uuid
from engine.db import client, MAIN
from engine import paths, risk, impact
IP_FACTOR = 0.6
REVOKE_FACTOR = 0.7
def apply_action(g, action, target, subject, by):
ts = int(time.time())
p = {'t': target, 'by': by, 'ts': ts}
Page 32 of 77

## PDF page 33

NEXUS Build Specification (Track 1, Graph Hacks)
if action == 'isolate_device':
g.query("MATCH (n:Device {id:$t}) SET n.status='ISOLATED',
n.blocked_by=$by, n.blocked_at=$ts", p)
elif action == 'disable_account':
g.query("MATCH (n:ServiceAccount {id:$t}) SET n.status='BLOCKED',
n.blocked_by=$by, n.blocked_at=$ts", p)
elif action == 'revoke_credentials':
g.query("MATCH (u {id:$t})-[r:HAS_ACCESS_TO]->() SET
r.status='BLOCKED', r.blocked_by=$by, r.blocked_at=$ts", p)
scale(g, target, REVOKE_FACTOR, by, 'OWNS')
elif action == 'block_ip':
g.query("MATCH (n:IPAddress {id:$t}) SET n.status='BLOCKED',
n.blocked_by=$by, n.blocked_at=$ts", p)
scale(g, subject, IP_FACTOR, by, None)
# monitor_only changes nothing
def scale(g, entity, factor, by, rel):
pattern = '[r:%s]' % rel if rel else '[r]'
q = ('MATCH (e {id:$e})-%s->() WHERE r.exploit_orig IS NULL '
'SET r.exploit_orig = r.exploit, r.exploit = r.exploit * $f,
r.scaled_by = $by' % pattern)
g.query(q, {'e': entity, 'f': factor, 'by': by})
def restore(g, by):
g.query("MATCH (n) WHERE n.blocked_by = $by SET n.status='ACTIVE' REMOVE
n.blocked_by, n.blocked_at", {'by': by})
g.query("MATCH ()-[r]->() WHERE r.blocked_by = $by SET r.status='ACTIVE'
REMOVE r.blocked_by, r.blocked_at", {'by': by})
g.query('MATCH ()-[r]->() WHERE r.scaled_by = $by '
'SET r.exploit = r.exploit_orig REMOVE r.exploit_orig,
r.scaled_by', {'by': by})
def candidates(g, subject, base_paths):
ids = sorted({i for p in base_paths for i in p['ids']} | {subject})
out = [('monitor_only', None)]
q = 'MATCH (n:%s) WHERE n.id IN $ids RETURN n.id'
for (d,) in g.query(q % 'Device', {'ids': ids}).result_set:
out.append(('isolate_device', d))
for (a,) in g.query(q % 'ServiceAccount', {'ids': ids}).result_set:
out.append(('disable_account', a))
if g.query('MATCH (n:Person {id:$id}) RETURN n.id', {'id':
subject}).result_set:
out.append(('revoke_credentials', subject))
Page 33 of 77

## PDF page 34

NEXUS Build Specification (Track 1, Graph Hacks)
for (ip,) in g.query('MATCH (i:IPAddress)-[:USED_BY]->(s {id:$id}) RETURN
i.id', {'id': subject}).result_set:
out.append(('block_ip', ip))
return out
def simulate(subject, alert_id):
live = client().select_graph(MAIN)
base = paths.find_attack_paths(live, subject)
base_risk = risk.calculate_risk(base['paths'])
rows = []
for action, target in candidates(live, subject, base['paths']):
if action == 'monitor_only':
after_paths, r = base['paths'], base_risk
else:
sim = live.copy('nexus_sim_' + uuid.uuid4().hex[:8])
try:
apply_action(sim, action, target, subject, alert_id)
after = paths.find_attack_paths(sim, subject)
after_paths, r = after['paths'],
risk.calculate_risk(after['paths'])
finally:
sim.delete()
imp = impact.action_impact(live, action, target)
rows.append({'action': action, 'target': target,
'residual_risk': r['score'], 'residual_label':
r['label'],
'paths_before': len(base['paths']), 'paths_after':
len(after_paths),
'paths_broken': len(base['paths']) - len(after_paths),
'impact': imp['impact'], 'impact_label': imp['label'],
'impact_detail': imp,
'needs_approval': imp['label'] in ('HIGH', 'CRITICAL')})
return {'subject': subject, 'alert_id': alert_id, 'initial': base_risk,
'base_paths': [{'ids': p['ids'], 'types': p['types']} for p in
base['paths']],
'matrix': rows, 'cypher': base['cypher']}
Note that this file uses double quotes around some Cypher strings because the Cypher
itself contains single quotes. That is fine in Python.
Page 34 of 77

## PDF page 35

NEXUS Build Specification (Track 1, Graph Hacks)
B12. The decision logic (engine/pareto.py)
Two steps. First mark every action that another action beats on both measures (lower or
equal residual risk and lower or equal impact, strictly better on at least one). Those are
dominated. The rest form the Pareto frontier. Second, apply a written policy to the
frontier.
The policy, in order:
1. If the starting risk is below 25, choose monitor_only.
2. Otherwise, among frontier actions whose residual risk is at most 40, choose the one
with the lowest business impact (ties broken by lower residual risk).
3. If no action reaches 40, choose the lowest residual risk and flag that human approval is
required.
4. If the chosen action's impact label is HIGH or CRITICAL, human approval is required.
MONITOR_BELOW = 25
TARGET = 40
def mark_pareto(rows):
for a in rows:
a['dominated_by'] = None
for b in rows:
if b is a:
continue
no_worse = b['residual_risk'] <= a['residual_risk'] and
b['impact'] <= a['impact']
better = b['residual_risk'] < a['residual_risk'] or b['impact'] <
a['impact']
if no_worse and better:
a['dominated_by'] = '%s %s' % (b['action'], b['target'] or
'')
break
return rows
def recommend(initial_score, rows):
rows = mark_pareto(rows)
mon = next(r for r in rows if r['action'] == 'monitor_only')
if initial_score < MONITOR_BELOW:
return {'row': mon, 'requires_approval': False, 'why': 'initial risk
below monitor threshold'}
front = [r for r in rows if r['dominated_by'] is None and r['action'] !=
Page 35 of 77

## PDF page 36

NEXUS Build Specification (Track 1, Graph Hacks)
'monitor_only']
ok = [r for r in front if r['residual_risk'] <= TARGET]
if ok:
pick = sorted(ok, key=lambda r: (r['impact'], r['residual_risk']))[0]
return {'row': pick, 'requires_approval': pick['needs_approval'],
'why': 'lowest business impact among frontier actions
reaching risk <= %d' % TARGET}
cand = front or [r for r in rows if r['action'] != 'monitor_only']
pick = sorted(cand, key=lambda r: (r['residual_risk'], r['impact']))[0]
return {'row': pick, 'requires_approval': True,
'why': 'no action reaches the target; lowest residual risk
chosen, human approval required'}
Why this is honest to call Pareto: the dominated flags above are the standard non-
dominated filter over two measures. Because the code exists, you may use the word in
your pitch.
B13. Storing, executing and rolling back (engine/store.py,
execute.py, tools.py)
engine/store.py
Investigation records (what was simulated, what was executed) are saved to a small JSON
file so the API process and the MCP process can both see them.
import json
import os
import uuid
PATH = os.getenv('NEXUS_STORE', 'data/investigations.json')
def _load():
if not os.path.exists(PATH):
return {}
with open(PATH) as f:
return json.load(f)
def save(inv_id, record):
data = _load()
data[inv_id] = record
os.makedirs(os.path.dirname(PATH), exist_ok=True)
Page 36 of 77

## PDF page 37

NEXUS Build Specification (Track 1, Graph Hacks)
with open(PATH, 'w') as f:
json.dump(data, f, indent=2)
def get(inv_id):
return _load().get(inv_id)
def new_id():
return 'INV-' + uuid.uuid4().hex[:6].upper()
engine/execute.py
This file enforces the safety rule: an action can only be executed if it was simulated in
this same investigation. It also verifies the outcome by recomputing risk on the live graph
and comparing it with the simulated number.
from engine.db import graph
from engine import paths, risk, simulate, store
def live_risk(subject):
res = paths.find_attack_paths(graph(), subject)
return risk.calculate_risk(res['paths'])
def execute(inv_id, action, target=None, approved=False):
rec = store.get(inv_id)
if rec is None:
return {'ok': False, 'error': 'UNKNOWN_INVESTIGATION'}
if action == 'monitor_only':
target = None
row = next((r for r in rec['matrix'] if r['action'] == action and
r['target'] == target), None)
if row is None:
return {'ok': False, 'error': 'REJECTED: this action was not
simulated in this investigation'}
if (row['needs_approval'] or rec['recommendation']['requires_approval'])
and not approved \
and action != 'monitor_only':
return {'ok': False, 'error': 'APPROVAL_REQUIRED', 'impact':
row['impact_label']}
before = live_risk(rec['subject'])
if action != 'monitor_only':
simulate.apply_action(graph(), action, target, rec['subject'],
rec['alert_id'])
Page 37 of 77

## PDF page 38

NEXUS Build Specification (Track 1, Graph Hacks)
after = live_risk(rec['subject'])
verified = abs(after['score'] - row['residual_risk']) <= 1
rec['executed'] = {'action': action, 'target': target, 'before':
before['score'],
'after': after['score'], 'verified': verified}
store.save(inv_id, rec)
return {'ok': True, 'before': before['score'], 'after': after['score'],
'before_label': before['label'], 'after_label': after['label'],
'verified': verified, 'simulated_residual': row['residual_risk']}
def rollback(inv_id):
rec = store.get(inv_id)
if rec is None:
return {'ok': False, 'error': 'UNKNOWN_INVESTIGATION'}
simulate.restore(graph(), rec['alert_id'])
rec['executed'] = None
store.save(inv_id, rec)
return {'ok': True, 'risk_now': live_risk(rec['subject'])['score']}
engine/tools.py
The single place where the 8 tools live. Both the agent and the MCP server call these.
Every tool returns plain data plus the Cypher it ran, so the UI can show it.
from engine.db import graph
from engine import paths, risk, simulate, pareto, execute, store
def resolve_entities(queries):
g = graph()
found, missing = [], []
for q in queries:
rows = g.query('MATCH (n) WHERE n.id = $q OR toLower(n.name) CONTAINS
toLower($q) '
'RETURN n.id, labels(n)[0], n.name LIMIT 5', {'q':
q}).result_set
if rows:
found += [{'id': r[0], 'label': r[1], 'name': r[2]} for r in
rows]
else:
missing.append(q)
return {'entities': found, 'unmatched': missing,
'cypher': 'MATCH (n) WHERE n.id = $q OR toLower(n.name) CONTAINS
Page 38 of 77

## PDF page 39

NEXUS Build Specification (Track 1, Graph Hacks)
toLower($q) RETURN n.id, labels(n)[0], n.name'}
def find_attack_paths(start_id, max_depth=7):
res = paths.find_attack_paths(graph(), start_id, max_depth)
return {'count': len(res['paths']), 'paths': res['paths'], 'cypher':
res['cypher']}
def blast_radius(start_id):
q = ('MATCH (s {id:$id})-
[:OWNS|LOGS_INTO|HAS_ACCESS_TO|HOSTS_CREDENTIAL|AUTHENTICATES_TO|READS*1..7]-
>(n) '
'RETURN labels(n)[0] AS label, count(DISTINCT n) AS c')
rows = graph().query(q, {'id': start_id}).result_set
return {'reachable_by_label': {r[0]: r[1] for r in rows}, 'cypher': q}
def calculate_risk(start_id):
res = paths.find_attack_paths(graph(), start_id)
out = risk.calculate_risk(res['paths'])
out['formula'] = 'risk = 100*(1-exp(-
sum(criticality*privilege*reach_probability)/K))'
return out
def find_choke_points(start_id, top_n=5):
ps = paths.find_attack_paths(graph(), start_id)['paths']
count = {}
for p in ps:
for nid in set(p['ids'][1:-1]):
count[nid] = count.get(nid, 0) + 1
ranked = sorted(count.items(), key=lambda kv: -kv[1])[:top_n]
props = {}
if ranked:
rows = graph().query('MATCH (n) WHERE n.id IN $ids RETURN n.id,
labels(n)[0], n.token_age_days',
{'ids': [k for k, _ in ranked]}).result_set
props = {r[0]: (r[1], r[2]) for r in rows}
nodes = [{'id': k, 'label': props.get(k, ('?', None))[0],
'token_age_days': props.get(k, ('?', None))[1],
'paths_through': v, 'path_coverage': round(v / len(ps), 2)} for
k, v in ranked]
return {'metric': 'path_coverage (share of attack paths passing through
the node)', 'nodes': nodes}
def simulate_containment(start_id, alert_id):
Page 39 of 77

## PDF page 40

NEXUS Build Specification (Track 1, Graph Hacks)
sim = simulate.simulate(start_id, alert_id)
rec = pareto.recommend(sim['initial']['score'], sim['matrix'])
inv_id = store.new_id()
row = rec['row']
record = dict(sim)
record['recommendation'] = {'action': row['action'], 'target':
row['target'],
'requires_approval':
rec['requires_approval'], 'why': rec['why']}
record['executed'] = None
store.save(inv_id, record)
return {'investigation_id': inv_id, 'initial_risk': sim['initial']
['score'],
'matrix': sim['matrix'], 'recommendation':
record['recommendation']}
def execute_containment(investigation_id, action, target=None,
approved=False):
return execute.execute(investigation_id, action, target, approved)
def rollback(investigation_id):
return execute.rollback(investigation_id)
FUNCS = {'resolve_entities': resolve_entities, 'find_attack_paths':
find_attack_paths,
'blast_radius': blast_radius, 'calculate_risk': calculate_risk,
'find_choke_points': find_choke_points, 'simulate_containment':
simulate_containment,
'execute_containment': execute_containment, 'rollback': rollback}
def call(name, args):
if name not in FUNCS:
return {'error': 'unknown tool ' + name}
try:
return FUNCS[name](**args)
except TypeError as e:
return {'error': 'bad arguments: %s' % e}
except Exception as e:
return {'error': 'tool failed: %s' % e}
S = {'type': 'string'}
def _t(name, desc, props, req):
Page 40 of 77

## PDF page 41

NEXUS Build Specification (Track 1, Graph Hacks)
return {'name': name, 'description': desc,
'input_schema': {'type': 'object', 'properties': props,
'required': req}}
TOOL_DEFS = [
_t('resolve_entities', 'Match names, ids or fragments from the alert text
to graph entities.',
{'queries': {'type': 'array', 'items': S}}, ['queries']),
_t('find_attack_paths', 'Find multi-hop attack paths from an entity to
crown-jewel data stores.',
{'start_id': S, 'max_depth': {'type': 'integer'}}, ['start_id']),
_t('blast_radius', 'Count everything reachable from an entity, grouped by
type.',
{'start_id': S}, ['start_id']),
_t('calculate_risk', 'Deterministic risk score 0-100 with a term-by-term
breakdown.',
{'start_id': S}, ['start_id']),
_t('find_choke_points', 'Rank nodes by the share of attack paths passing
through them.',
{'start_id': S, 'top_n': {'type': 'integer'}}, ['start_id']),
_t('simulate_containment', 'Simulate every candidate containment action
on graph copies. Returns a matrix, Pareto flags and a policy
recommendation.',
{'start_id': S, 'alert_id': S}, ['start_id', 'alert_id']),
_t('execute_containment', 'Execute an action. Only actions returned by
simulate_containment are accepted. Respect requires_approval.',
{'investigation_id': S, 'action': S, 'target': S, 'approved': {'type':
'boolean'}}, ['investigation_id', 'action']),
_t('rollback', 'Undo the containment of an investigation.',
{'investigation_id': S}, ['investigation_id']),
]
Checkpoint (gate B, the most important test in the project): create scripts_decide.py
and run it.
Page 41 of 77

## PDF page 42

NEXUS Build Specification (Track 1, Graph Hacks)
from engine import tools
for subject, alert in [('U-ALEX', 'ALT-1042'), ('SVC-ACCT-17', 'ALT-2071'),
('U-PRIYA', 'ALT-3310')]:
out = tools.simulate_containment(subject, alert)
rec = out['recommendation']
print(alert, 'initial', out['initial_risk'], '->', rec['action'],
rec['target'], '|', rec['why'])
for r in out['matrix']:
print(' %-20s %-14s residual %3d impact %3d %-8s dominated_by %s'
% (
r['action'], r['target'], r['residual_risk'], r['impact'],
r['impact_label'], r.get('dominated_by')))
Expected decisions: ALT-1042 gives isolate_device LAPTOP-042, ALT-2071 gives
disable_account SVC-ACCT-17, ALT-3310 gives monitor_only. If these three differ, fix the
engine now, before building anything on top. Remember to run rollback or re-seed (python
-m seed.generate) if you execute actions while testing.
B14. The agent (agent/loop.py)
The agent is a loop: send the alert and the tool list to the AI model, run whichever tools it
asks for, feed the results back, and repeat until it writes a final answer. Two safety rules
live in code, not in the prompt, so the model cannot talk its way around them:
1. The agent path always sends approved=False. Only a human pressing CONTAIN in the
UI can approve a high-impact action.
2. If autonomous mode is off, execution is blocked entirely and the agent must present its
recommendation.
There are two runners. run_llm uses a real model and lets it choose the tools.
run_scripted (mock mode) calls the same real tools in a fixed order with no AI, so the
demo works without a key or internet. In your README and video, say clearly which mode
you are showing. Never present scripted mode as AI decision-making.
import json
import os
import time
from engine import tools, store
from engine.db import graph
Page 42 of 77

## PDF page 43

NEXUS Build Specification (Track 1, Graph Hacks)
MODEL = os.getenv('NEXUS_MODEL', 'claude-sonnet-5-5')
MAX_STEPS = 12
SYSTEM = '''You are NEXUS, a security operations agent. You investigate one
alert at a time using tools that read a graph of company infrastructure (all
data is synthetic).
Procedure:
1. Call resolve_entities with the names, ids and hostnames found in the alert
text. The subject is the person or service account the alert is about.
2. Call find_attack_paths, calculate_risk and find_choke_points for the
subject. If no path is found, widen the search or try related entities such
as the subject devices before concluding.
3. Call simulate_containment with the subject id and the alert id.
4. Choose an action only from the simulate_containment matrix. Prefer the
policy recommendation. If you choose differently, justify it with the
numbers.
5. If execution is allowed and the action does not require approval, call
execute_containment, then report the verified before and after risk. If
approval is required, stop and explain what a human must approve.
Rules: never state a number that is not in a tool result. Cite node ids from
tool results. Do not claim to predict attacker behaviour; call it risk
analysis. List missing evidence, for example a server with no vulnerability
data. Final answer sections: Decision, Evidence, Alternatives considered,
Missing evidence, Verification. Be concise.'''
def summarize(name, out):
if 'error' in out:
return 'ERROR ' + str(out['error'])
if name == 'find_attack_paths':
return '%d attack paths found' % out['count']
if name == 'calculate_risk':
return 'risk %s %s' % (out['score'], out['label'])
if name == 'simulate_containment':
rec = out['recommendation']
return '%d actions simulated; recommends %s %s' %
(len(out['matrix']), rec['action'], rec['target'] or '')
if name == 'execute_containment':
if out.get('ok'):
return 'risk %s -> %s, verified=%s' % (out['before'],
out['after'], out['verified'])
return 'blocked: ' + str(out.get('error'))
return json.dumps(out)[:200]
Page 43 of 77

## PDF page 44

NEXUS Build Specification (Track 1, Graph Hacks)
def run_tool(trace, name, args, forced=None):
t0 = time.time()
out = forced if forced is not None else tools.call(name, args)
trace.append({'step': len(trace) + 1, 'tool': name, 'args': args,
'cypher': out.get('cypher'), 'summary': summarize(name,
out),
'ms': round((time.time() - t0) * 1000)})
return out
def package(trace, summary, mode):
inv = None
for step in trace:
pass
return {'mode': mode, 'trace': trace, 'summary': summary}
def finish(trace, summary, mode, inv_id):
rec = store.get(inv_id) if inv_id else None
return {'mode': mode, 'trace': trace, 'summary': summary,
'investigation_id': inv_id,
'initial': rec['initial'] if rec else None,
'matrix': rec['matrix'] if rec else None,
'recommendation': rec['recommendation'] if rec else None,
'executed': rec['executed'] if rec else None}
def run_llm(alert_id, alert_text, autonomous=False):
import anthropic
client = anthropic.Anthropic()
trace, inv_id, final = [], None, ''
first = 'Alert id: %s. Autonomous execution allowed: %s. Raw alert: %s' %
(alert_id, autonomous, alert_text)
messages = [{'role': 'user', 'content': first}]
for _ in range(MAX_STEPS):
resp = client.messages.create(model=MODEL, max_tokens=1500,
system=SYSTEM,
tools=tools.TOOL_DEFS,
messages=messages)
messages.append({'role': 'assistant', 'content': resp.content})
calls = [b for b in resp.content if b.type == 'tool_use']
if not calls:
final = ' '.join(b.text for b in resp.content if b.type ==
'text')
break
results = []
Page 44 of 77

## PDF page 45

NEXUS Build Specification (Track 1, Graph Hacks)
for b in calls:
args = dict(b.input)
forced = None
if b.name == 'execute_containment':
args['approved'] = False
if not autonomous:
forced = {'ok': False, 'error': 'EXECUTION_DISABLED: a
human must press CONTAIN'}
out = run_tool(trace, b.name, args, forced)
if 'investigation_id' in out:
inv_id = out['investigation_id']
results.append({'type': 'tool_result', 'tool_use_id': b.id,
'content': json.dumps(out)})
messages.append({'role': 'user', 'content': results})
return finish(trace, final, 'llm', inv_id)
def explain(rec):
ini, pick = rec['initial'], rec['recommendation']
lines = ['Decision: %s %s (%s)' % (pick['action'], pick['target'] or '',
pick['why']),
'Evidence: initial risk %s %s from %d attack paths.' %
(ini['score'], ini['label'], len(rec['base_paths'])),
'Alternatives considered:']
for r in rec['matrix']:
dom = ' [dominated by %s]' % r['dominated_by'] if
r.get('dominated_by') else ''
lines.append(' - %s %s: residual risk %d, impact %s (%d)%s' % (
r['action'], r['target'] or '', r['residual_risk'],
r['impact_label'], r['impact'], dom))
ex = rec.get('executed')
if ex:
lines.append('Verification: risk %d -> %d, matches simulation: %s' %
(ex['before'], ex['after'], ex['verified']))
elif pick['requires_approval']:
lines.append('Human approval is required before this action runs.')
else:
lines.append('Not executed yet. Press CONTAIN to apply the
recommended action.')
return chr(10).join(lines)
def run_scripted(alert_id, alert_text, autonomous=False):
trace = []
row = graph().query('MATCH (a:Alert {id:$id})-[:ABOUT]->(e) RETURN e.id',
Page 45 of 77

## PDF page 46

NEXUS Build Specification (Track 1, Graph Hacks)
{'id': alert_id}).result_set
subject = row[0][0]
run_tool(trace, 'resolve_entities', {'queries': [subject]})
run_tool(trace, 'find_attack_paths', {'start_id': subject})
run_tool(trace, 'calculate_risk', {'start_id': subject})
run_tool(trace, 'find_choke_points', {'start_id': subject})
sim = run_tool(trace, 'simulate_containment', {'start_id': subject,
'alert_id': alert_id})
inv_id, rec = sim['investigation_id'], sim['recommendation']
if autonomous and not rec['requires_approval']:
run_tool(trace, 'execute_containment', {'investigation_id': inv_id,
'action': rec['action'],
'target': rec['target'],
'approved': False})
run_tool(trace, 'calculate_risk', {'start_id': subject})
return finish(trace, explain(store.get(inv_id)), 'scripted', inv_id)
Delete the unused package function if you copy this; it is a leftover and not called
anywhere.
Checkpoint (gate C): in a Python shell, run these lines. You should get a trace list and a
readable summary for each scenario.
from agent import loop
out = loop.run_scripted('ALT-1042', '', autonomous=False)
print(out['summary'])
B15. What the mock mode does and does not prove
The scripted runner proves the graph engine, the simulation, the policy and the safety
rules work. It does not prove an AI can choose tools well. The real mode does that. For the
video and the benchmark use real mode (set MOCK_LLM=0 and a valid key). Keep mock
mode as the fallback for judges who run your project without a key.
What the AI adds in real mode, in terms you can say to judges: it reads the messy alert text
and works out which entities matter, it picks the order of tool calls and widens its search
if a path is missing, it notices missing evidence, and it writes the explanation tied to node
ids. The numbers, the simulation and the safety checks are deterministic code.
Page 46 of 77

## PDF page 47

NEXUS Build Specification (Track 1, Graph Hacks)
B16. The backend (api/main.py)
FastAPI turns the engine and agent into web addresses the UI can call.
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine.db import graph
from engine import execute, store
from agent import loop
app = FastAPI(title='NEXUS')
class InvestigateReq(BaseModel):
alert_id: str
mode: str = 'auto'
autonomous: bool = False
class ActReq(BaseModel):
investigation_id: str
action: str = ''
target: str | None = None
@app.get('/api/alerts')
def alerts():
rows = graph().query('MATCH (a:Alert) RETURN a.id, a.type, a.raw_text
ORDER BY a.id').result_set
return [{'id': r[0], 'type': r[1], 'raw_text': r[2]} for r in rows]
@app.post('/api/investigate')
def investigate(req: InvestigateReq):
rows = graph().query('MATCH (a:Alert {id:$id}) RETURN a.raw_text', {'id':
req.alert_id}).result_set
if not rows:
raise HTTPException(404, 'unknown alert')
mock = req.mode == 'mock' or os.getenv('MOCK_LLM') == '1' or not
os.getenv('ANTHROPIC_API_KEY')
runner = loop.run_scripted if mock else loop.run_llm
return runner(req.alert_id, rows[0][0], req.autonomous)
@app.post('/api/contain')
def contain(req: ActReq):
Page 47 of 77

## PDF page 48

NEXUS Build Specification (Track 1, Graph Hacks)
rec = store.get(req.investigation_id)
if not rec:
raise HTTPException(404, 'unknown investigation')
rc = rec['recommendation']
action = req.action or rc['action']
target = req.target if req.action else rc['target']
return execute.execute(req.investigation_id, action, target,
approved=True)
@app.post('/api/rollback')
def rollback(req: ActReq):
return execute.rollback(req.investigation_id)
@app.get('/api/graph/{inv_id}')
def subgraph(inv_id: str):
rec = store.get(inv_id)
if not rec:
raise HTTPException(404, 'unknown investigation')
ids = sorted({i for p in rec['base_paths'] for i in p['ids']})
q = '''MATCH (n) WHERE n.id IN $ids
RETURN n.id, labels(n)[0], n.name, coalesce(n.status, 'ACTIVE')'''
rows = graph().query(q, {'ids': ids}).result_set
edges = set()
for p in rec['base_paths']:
for i, t in enumerate(p['types']):
edges.add((p['ids'][i], p['ids'][i + 1], t))
return {'nodes': [{'id': r[0], 'label': r[1], 'name': r[2], 'status':
r[3]} for r in rows],
'edges': [{'source': a, 'target': b, 'type': t} for a, b, t in
sorted(edges)]}
app.mount('/', StaticFiles(directory='ui', html=True), name='ui')
Start it (with FalkorDB running and the graph seeded):
uvicorn api.main:app --reload --port 8000
Open http://localhost:8000/docs. FastAPI draws an automatic test page where you can
click POST /api/investigate, press Try it out, enter {"alert_id": "ALT-1042", "mode": "mock"}
and run it. Checkpoint: you get JSON with a trace and a summary.
Page 48 of 77

## PDF page 49

NEXUS Build Specification (Track 1, Graph Hacks)
B17. The interface (ui/index.html)
One file, no build tools. The page order follows the pitch: decision first, then evidence,
then the graph.
<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>NEXUS</title>
<script
src='https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.2/cytoscape.min.js
'></script>
<style>
body{font-family:system-ui,sans-
serif;margin:0;background:#0f1419;color:#e6e6e6}
header{padding:14px 20px;border-bottom:1px solid
#2a323c;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header b{letter-spacing:2px}
main{max-width:1100px;margin:0 auto;padding:16px;display:grid;gap:16px}
.card{background:#161d26;border:1px solid #2a323c;border-
radius:10px;padding:16px}
.big{font-size:56px;font-weight:700;line-height:1}
.CRITICAL{color:#ff5c5c}.HIGH{color:#ff9f43}.MEDIUM{color:#f7d154}.LOW{color:
#4cd98a}
button{background:#2f6df6;color:#fff;border:0;border-radius:6px;padding:10px
18px;font-size:15px;cursor:pointer}
button.warn{background:#c0392b}button:disabled{opacity:.5}
select,label{font-size:14px}
table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:6px 8px;border-bottom:1px solid #2a323c;text-align:left}
tr.pick{background:#1f3a2a}
.dom{color:#8892a0;font-size:12px}
pre{background:#0b0f14;padding:8px;overflow:auto;font-size:12px;white-
space:pre-wrap}
.step{padding:6px 0;border-bottom:1px solid #2a323c;font-size:14px}
.tag{font-size:11px;padding:2px 6px;border-radius:4px;background:#2a323c}
#cy{height:380px;background:#0b0f14;border-radius:8px}
#summary{white-space:pre-wrap;font-size:14px}
</style>
</head>
Page 49 of 77

## PDF page 50

NEXUS Build Specification (Track 1, Graph Hacks)
<body>
<header>
<b>NEXUS</b><span class='tag'>SYNTHETIC DATA</span>
<select id='alert'></select>
<select id='mode'><option value='auto'>Real agent (needs key)</option>
<option value='mock'>Scripted tools (no AI)</option></select>
<label><input type='checkbox' id='auto'> Autonomous mode</label>
<button id='go' onclick='run()'>Investigate</button>
<span id='status'></span>
</header>
<main>
<section class='card' id='decision'>Pick an alert and press Investigate.
</section>
<section class='card'><h3>Containment matrix</h3><div id='matrix'></div>
</section>
<section class='card'><h3>Agent trace</h3><div id='trace'></div><div
id='summary'></div></section>
<section class='card'><h3>Attack graph</h3><div id='cy'></div></section>
</main>
<script>
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const sleep = ms => new Promise(r => setTimeout(r, ms));
let INV = null;
async function post(url, body){
const r = await fetch(url, {method: 'POST', headers: {'Content-Type':
'application/json'}, body: JSON.stringify(body)});
return r.json();
}
async function init(){
const a = await (await fetch('/api/alerts')).json();
$('alert').innerHTML = a.map(x => `<option value='${x.id}'>${x.id} -
${x.type}</option>`).join('');
}
async function run(){
$('go').disabled = true; $('status').textContent = 'Investigating...';
$('trace').innerHTML = ''; $('summary').textContent = '';
const d = await post('/api/investigate', {alert_id: $('alert').value, mode:
$('mode').value, autonomous: $('auto').checked});
INV = d.investigation_id;
Page 50 of 77

## PDF page 51

NEXUS Build Specification (Track 1, Graph Hacks)
for (const s of d.trace){
const cy = s.cypher ? `<details><summary>Show Cypher</summary>
<pre>${esc(s.cypher)}</pre></details>` : '';
$('trace').insertAdjacentHTML('beforeend', `<div class='step'><span
class='tag'>${s.step}</span> <b>${s.tool}</b> ${esc(JSON.stringify(s.args))}
<br>${esc(s.summary)} <span class='dom'>${s.ms} ms</span>${cy}</div>`);
await sleep(250);
}
$('summary').textContent = d.summary;
render(d); await drawGraph();
$('go').disabled = false; $('status').textContent = 'mode: ' + d.mode;
}
function render(d){
if (!d.initial){ $('decision').textContent = 'No simulation result.';
return; }
const rec = d.recommendation, ini = d.initial, ex = d.executed;
const act = rec.action === 'monitor_only' ? 'MONITOR ONLY' : (rec.action +
' ' + rec.target).toUpperCase();
let btn = '';
if (rec.action !== 'monitor_only' && !ex){
btn = `<button class='${rec.requires_approval ? 'warn' : ''}'
onclick='contain()'>${rec.requires_approval ? 'APPROVE AND CONTAIN' :
'CONTAIN'}</button>`;
}
if (ex) btn = `<button class='warn'
onclick='rollback()'>ROLLBACK</button>`;
const after = ex ? `<div>After containment: <b class='${ex.after >= 75 ?
'CRITICAL' : 'LOW'}'>${ex.after}</b> (verified: ${ex.verified})</div>` : '';
$('decision').innerHTML = `<div class='dom'>${esc(d.investigation_id)}
</div>
<div class='big ${ini.label}'>${ini.score}<span style='font-size:20px'> /
100 ${ini.label}</span></div>
<div>${d.matrix[0].paths_before} attack paths found</div>
<p>RECOMMENDED: <b>${esc(act)}</b><br><span class='dom'>${esc(rec.why)}
</span></p>${after}${btn}
<details><summary>How was this score computed?</summary>
<pre>${esc(JSON.stringify(ini, null, 1))}</pre></details>`;
const rows = d.matrix.map(r => {
const pick = r.action === rec.action && r.target === rec.target ? 'pick'
: '';
const dom = r.dominated_by ? `<span class='dom'>dominated by
${esc(r.dominated_by)}</span>` : '<span class="tag">Pareto</span>';
Page 51 of 77

## PDF page 52

NEXUS Build Specification (Track 1, Graph Hacks)
return `<tr class='${pick}'><td>${r.action}</td><td>${r.target || ''}
</td><td>${r.residual_risk}</td><td>${r.paths_broken}/${r.paths_before}</td>
<td class='${r.impact_label}'>${r.impact_label} (${r.impact})</td><td>${dom}
</td></tr>`;
}).join('');
$('matrix').innerHTML = `<table><tr><th>Action</th><th>Target</th>
<th>Residual risk</th><th>Paths broken</th><th>Business impact</th>
<th>Pareto</th></tr>${rows}</table>`;
}
async function contain(){
const r = await post('/api/contain', {investigation_id: INV});
$('status').textContent = r.ok ? `risk ${r.before} -> ${r.after}, verified
${r.verified}` : r.error;
await refresh();
}
async function rollback(){
await post('/api/rollback', {investigation_id: INV});
await refresh();
}
async function refresh(){
const d = await (await fetch('/api/investigations/' + INV)).json();
render(d); await drawGraph();
}
async function drawGraph(){
const g = await (await fetch('/api/graph/' + INV)).json();
const bad = new Set(g.nodes.filter(n => n.status !== 'ACTIVE').map(n =>
n.id));
const els = g.nodes.map(n => ({data: {id: n.id, label: n.id, bad:
bad.has(n.id) ? 1 : 0}}))
.concat(g.edges.map(e => ({data: {source: e.source, target: e.target,
label: e.type, bad: (bad.has(e.source) || bad.has(e.target)) ? 1 : 0}})));
cytoscape({container: $('cy'), elements: els, layout: {name:
'breadthfirst', directed: true, padding: 10},
style: [
{selector: 'node', style: {label: 'data(label)', color: '#e6e6e6',
'font-size': 10, 'background-color': '#2f6df6'}},
{selector: 'node[bad = 1]', style: {'background-color': '#c0392b'}},
{selector: 'edge', style: {width: 2, 'line-color': '#ff9f43', 'target-
arrow-shape': 'triangle', 'target-arrow-color': '#ff9f43', 'curve-style':
'bezier'}},
{selector: 'edge[bad = 1]', style: {'line-style': 'dashed', 'line-
Page 52 of 77

## PDF page 53

NEXUS Build Specification (Track 1, Graph Hacks)
color': '#555', 'target-arrow-color': '#555'}}
]});
}
init();
</script>
</body>
</html>
The UI calls one endpoint that was not in the backend yet: /api/investigations/ plus the id,
which returns a saved investigation in the same shape as the investigate response. Add it
to api/main.py above the app.mount line:
@app.get('/api/investigations/{inv_id}')
def get_investigation(inv_id: str):
rec = store.get(inv_id)
if not rec:
raise HTTPException(404, 'unknown investigation')
return {'investigation_id': inv_id, 'initial': rec['initial'], 'matrix':
rec['matrix'],
'recommendation': rec['recommendation'], 'executed':
rec['executed']}
Checkpoint (gate D): open http://localhost:8000. Choose ALT-1042, mode Scripted tools,
press Investigate. You should see a big risk number, a recommended action, a matrix, a
trace with expandable Cypher and a graph. Press CONTAIN: the number after
containment appears, the isolated node turns red, the paths become dashed. Press
ROLLBACK to undo. Repeat for ALT-2071 (disable account, needs approval, so the button
says APPROVE AND CONTAIN) and ALT-3310 (monitor only, no button).
B18. One-command start (Dockerfile and docker-compose.yml)
The goal: a judge clones your repository, runs one command and sees the same thing you
do.
Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
Page 53 of 77

## PDF page 54

NEXUS Build Specification (Track 1, Graph Hacks)
docker-compose.yml
services:
falkordb:
image: falkordb/falkordb:latest
ports:
- '6379:6379'
- '3000:3000'
volumes:
- falkor_data:/var/lib/falkordb/data
app:
build: .
depends_on:
- falkordb
environment:
FALKOR_HOST: falkordb
ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
NEXUS_MODEL: ${NEXUS_MODEL:-claude-sonnet-5-5}
MOCK_LLM: ${MOCK_LLM:-1}
ports:
- '8000:8000'
volumes:
- ./data:/app/data
command: sh -c 'python -m seed.generate && uvicorn api.main:app --host
0.0.0.0 --port 8000'
volumes:
falkor_data:
Create a .dockerignore with the lines .venv, .git, pycache and .env. Then run:
docker rm -f falkordb
docker compose up --build
(The first command removes the container you started by hand in B7 so ports 6379 and
3000 are free.) Open http://localhost:8000. To use the real agent, create a .env file next to
the compose file with ANTHROPIC_API_KEY=your key and MOCK_LLM=0, then run
docker compose up again. Checkpoint: a fresh clone of your repository in an empty folder
works with this one command. Test exactly that before submitting.
Page 54 of 77

## PDF page 55

NEXUS Build Specification (Track 1, Graph Hacks)
B19. Automated tests (tests/test_engine.py)
Tests are your proof that the system does what you claim. They re-seed the graph, so run
them only against your demo database.
import pytest
from seed.generate import build
from engine import tools
from engine.db import client
@pytest.fixture(scope='session', autouse=True)
def seeded():
build()
def decide(subject, alert):
out = tools.simulate_containment(subject, alert)
return out, out['recommendation']
def test_scenario1_isolates_laptop():
out, rec = decide('U-ALEX', 'ALT-1042')
assert out['initial_risk'] >= 75
assert rec['action'] == 'isolate_device' and rec['target'] == 'LAPTOP-
042'
assert tools.find_attack_paths('U-ALEX')['count'] == 3
def test_scenario2_disables_account():
out, rec = decide('SVC-ACCT-17', 'ALT-2071')
assert rec['action'] == 'disable_account' and rec['target'] == 'SVC-ACCT-
17'
def test_scenario3_monitors_only():
out, rec = decide('U-PRIYA', 'ALT-3310')
assert rec['action'] == 'monitor_only'
def test_unsimulated_action_is_rejected():
out, rec = decide('U-ALEX', 'ALT-1042')
res = tools.execute_containment(out['investigation_id'],
'isolate_device', 'LAPTOP-PRIYA')
assert res['ok'] is False and 'not simulated' in res['error']
def test_high_impact_needs_approval():
out, rec = decide('U-ALEX', 'ALT-1042')
res = tools.execute_containment(out['investigation_id'],
Page 55 of 77

## PDF page 56

NEXUS Build Specification (Track 1, Graph Hacks)
'disable_account', 'SVC-ACCT-09')
assert res['ok'] is False and res['error'] == 'APPROVAL_REQUIRED'
def test_execute_verify_rollback():
out, rec = decide('U-ALEX', 'ALT-1042')
inv = out['investigation_id']
res = tools.execute_containment(inv, rec['action'], rec['target'])
assert res['ok'] and res['verified']
back = tools.rollback(inv)
assert back['risk_now'] == out['initial_risk']
def test_sandbox_graphs_are_deleted():
decide('U-ALEX', 'ALT-1042')
leftovers = [n for n in client().list_graphs() if
n.startswith('nexus_sim_')]
assert leftovers == []
Run from the project root:
python -m pytest -q
Checkpoint (gate E): all tests pass. If one fails, read the message, fix the engine, and do
not weaken the test.
B20. The benchmark (bench/run_benchmark.py)
The benchmark turns claims into evidence. It makes 30 alerts (the three scenarios, seven
interesting infrastructure entities and twenty random ones), computes the engine's
optimal decision, then checks two things:
1. Verification rate: after executing, does the live graph risk match the simulated residual
risk? (Run with the scripted tools, no AI needed.)
2. Agent agreement: when a real AI agent investigates the same alert, does it pick the
same action as the engine's optimum? (Only if a key is set.)
Be honest about what this measures. The engine optimum is the best action under your
stated policy on a synthetic graph. Agreement with it shows the agent follows the
evidence, not that it would be right in a real company.
Page 56 of 77

## PDF page 57

NEXUS Build Specification (Track 1, Graph Hacks)
import os
import random
from engine.db import graph
from engine import tools, execute
from agent import loop
from seed.generate import node
N = int(os.getenv('BENCH_N', '30'))
EXTRA = ['SVC-ACCT-09', 'LAPTOP-042', 'DEV-SERVER-03', 'DEV-SERVER-07',
'JUMPBOX-01', 'PROD-API', 'BILLING-SVC']
def make_alerts(n):
g = graph()
random.seed(7)
fixed = [('ALT-1042', 'U-ALEX'), ('ALT-2071', 'SVC-ACCT-17'), ('ALT-
3310', 'U-PRIYA')]
out = []
for aid, s in fixed:
text = g.query('MATCH (a:Alert {id:$id}) RETURN a.raw_text', {'id':
aid}).result_set[0][0]
out.append((aid, s, text))
people = [r[0] for r in g.query('MATCH (p:Person) RETURN
p.id').result_set if r[0].startswith('U-BG')]
accts = [r[0] for r in g.query('MATCH (a:ServiceAccount) RETURN
a.id').result_set if r[0].startswith('ACC-BG')]
pool = EXTRA + random.sample(people + accts, n - 3 - len(EXTRA))
for i, s in enumerate(pool):
aid = 'BENCH-%03d' % i
text = '%s | ANOMALY | unusual activity observed for entity %s' %
(aid, s)
node(g, 'Alert', aid, type='ANOMALY', raw_text=text)
g.query('MATCH (a {id:$a}), (e {id:$e}) MERGE (a)-[:ABOUT]->(e)',
{'a': aid, 'e': s})
out.append((aid, s, text))
return out
def last_execute(trace):
for step in reversed(trace):
if step['tool'] == 'execute_containment':
return step['args'].get('action'), (step['args'].get('target') or
None)
return None
Page 57 of 77

## PDF page 58

NEXUS Build Specification (Track 1, Graph Hacks)
def main():
use_llm = os.getenv('MOCK_LLM') != '1' and
bool(os.getenv('ANTHROPIC_API_KEY'))
rows = []
for aid, subject, text in make_alerts(N):
opt = tools.simulate_containment(subject, aid)['recommendation']
res = loop.run_scripted(aid, text, autonomous=True)
ex = res['executed']
verified = ex['verified'] if ex else None
if ex:
execute.rollback(res['investigation_id'])
row = {'alert': aid, 'subject': subject, 'optimum': '%s %s' %
(opt['action'], opt['target'] or ''),
'verified': verified, 'match': None, 'agent': ''}
if use_llm:
r2 = loop.run_llm(aid, text, autonomous=True)
chosen = last_execute(r2['trace'])
if r2['executed']:
execute.rollback(r2['investigation_id'])
if chosen is None:
row['match'] = opt['action'] == 'monitor_only'
row['agent'] = 'no action'
else:
row['match'] = chosen == (opt['action'], opt['target'])
row['agent'] = '%s %s' % (chosen[0], chosen[1] or '')
rows.append(row)
ver = [r['verified'] for r in rows if r['verified'] is not None]
lines = ['# NEXUS benchmark (synthetic graph, %d alerts)' % len(rows),
'']
lines.append('Verification: %d of %d executed actions matched the
simulated residual risk.' % (sum(ver), len(ver)))
if use_llm:
agree = sum(1 for r in rows if r['match'])
lines.append('Agent agreement with engine optimum: %d of %d.' %
(agree, len(rows)))
lines += ['', '| Alert | Subject | Engine optimum | Agent | Match |', '|-
--|---|---|---|---|']
for r in rows:
lines.append('| %s | %s | %s | %s | %s |' % (r['alert'],
r['subject'], r['optimum'], r['agent'], r['match']))
with open('bench/results.md', 'w') as f:
f.write(chr(10).join(lines))
Page 58 of 77

## PDF page 59

NEXUS Build Specification (Track 1, Graph Hacks)
print(chr(10).join(lines[:4]))
if __name__ == '__main__':
main()
Run with python -m bench.run_benchmark. Paste the headline numbers into the README
and the misses, with one line explaining each miss. Publishing misses reads as
confidence, not weakness. If you are short of time, set BENCH_N=15 and say so.
B21. The MCP server (mcp_server/server.py)
MCP lets any compatible AI app (Claude Desktop, Claude Code, an inspector tool)
discover and use your tools without custom glue. This file wraps the same eight functions.
from mcp.server.fastmcp import FastMCP
from engine import tools
mcp = FastMCP('nexus')
@mcp.tool(description='Match names, ids or fragments from alert text to graph
entities.')
def resolve_entities(queries: list[str]) -> dict:
return tools.call('resolve_entities', {'queries': queries})
@mcp.tool(description='Find multi-hop attack paths from an entity to crown-
jewel data stores.')
def find_attack_paths(start_id: str, max_depth: int = 7) -> dict:
return tools.call('find_attack_paths', {'start_id': start_id,
'max_depth': max_depth})
@mcp.tool(description='Count everything reachable from an entity, grouped by
type.')
def blast_radius(start_id: str) -> dict:
return tools.call('blast_radius', {'start_id': start_id})
@mcp.tool(description='Deterministic risk score 0-100 with a term-by-term
breakdown.')
def calculate_risk(start_id: str) -> dict:
return tools.call('calculate_risk', {'start_id': start_id})
@mcp.tool(description='Rank nodes by the share of attack paths passing
through them.')
Page 59 of 77

## PDF page 60

NEXUS Build Specification (Track 1, Graph Hacks)
def find_choke_points(start_id: str, top_n: int = 5) -> dict:
return tools.call('find_choke_points', {'start_id': start_id, 'top_n':
top_n})
@mcp.tool(description='Simulate every candidate containment action on graph
copies and recommend one.')
def simulate_containment(start_id: str, alert_id: str) -> dict:
return tools.call('simulate_containment', {'start_id': start_id,
'alert_id': alert_id})
@mcp.tool(description='Execute a simulated action. Rejects anything not
simulated. High impact needs human approval.')
def execute_containment(investigation_id: str, action: str, target: str = '')
-> dict:
return tools.call('execute_containment', {'investigation_id':
investigation_id, 'action': action,
'target': target or None,
'approved': False})
@mcp.tool(description='Undo the containment of an investigation.')
def rollback(investigation_id: str) -> dict:
return tools.call('rollback', {'investigation_id': investigation_id})
if __name__ == '__main__':
mcp.run()
Run it with python -m mcp_server.server (it waits silently for an MCP client). To test it
visually, install Node.js and run npx @modelcontextprotocol/inspector python -m
mcp_server.server, open the printed address, press Connect, and call a tool from the list.
To use it from Claude Desktop, add an mcpServers entry named nexus whose command is
the full path to your virtual environment's python and whose args are -m and
mcp_server.server, with the working directory set to your project folder. Be accurate in
your README: the built-in agent calls the same tool functions directly, and the MCP
server exposes them to external clients.
B22. The README (what judges read first)
Create README.md with these sections in this order. Use plain, specific sentences.
1. Title and one-line pitch: NEXUS, an autonomous attack-path agent that uses FalkorDB
as its decision substrate. Add the badge text SYNTHETIC DATA.
Page 60 of 77

## PDF page 61

NEXUS Build Specification (Track 1, Graph Hacks)
2. The problem in three sentences: an alert looks small, the danger is in what it can
reach, and the safest response is not always the lowest-risk one.
3. Demo: link to the video and two screenshots (decision card, containment matrix).
4. How it works: a diagram (draw it in any tool and add the image) showing alert, agent,
FalkorDB graph, deterministic engine, simulation on graph copies, decision, execution,
verification. Then the division of labour sentence: the LLM orchestrates the
investigation, FalkorDB provides the ground truth, and deterministic graph analysis
constrains the action.
5. How FalkorDB is used: typed graph schema, multi-hop Cypher traversals,
GRAPH.COPY sandboxes for counterfactual simulation, status properties for non-
destructive containment, one graph per investigation copy.
6. The formulas: risk, business impact, Pareto and policy, copied from sections B10 to B12.
7. Three scenarios and their decisions: a small table.
8. Run it: git clone, copy .env.example to .env, docker compose up --build, open
localhost:8000. Mention mock mode and the real mode key.
9. Benchmark: the numbers and the misses.
10. Limitations and honesty notes: synthetic data, modelling assumptions (IP_FACTOR,
REVOKE_FACTOR, K), no latency claims, the agent never self-approves, path coverage
rather than betweenness (if that is what you used).
11. What I would build next: two or three real ideas.
Credibility rules for everything you write: say synthetic, never production-calibrated.
Say 1.25M PII records, not transactions. Use SYNTH-VULN-2026-01, not a real CVE. Say
next-move risk analysis, not attacker prediction. Do not claim speed numbers you did not
measure. Say Pareto only because you implemented it.
B23. The 90-second video
Record at 1080p with the screen recorder you already have: Windows key plus G (Xbox
Game Bar), Mac Shift plus Command plus 5, or OBS Studio (free). Close notifications first.
Record in real mode (a valid key), since that shows the agent choosing tools. Do two or
three takes and keep the best.
Page 61 of 77

## PDF page 62

NEXUS Build Specification (Track 1, Graph Hacks)
Time Show Say
0 to 10 s Decision card after pressing This alert looks like impossible travel.
Investigate on ALT-1042 NEXUS finds out whether it is
dangerous by tracing what the account
can actually reach
10 to 35 Agent trace scrolling, one Show The agent chooses graph tools.
s Cypher opened, the graph FalkorDB returns real multi-hop paths
to a database of 1.25 million synthetic
PII records
35 to 60 Containment matrix with the Pareto It simulated every action on a copy of
s column the graph. Disabling the account is
lowest risk but breaks production, so it
is dominated. It picks the safe action
60 to 80 Press CONTAIN, graph turns red, Contained and verified against the
s before and after numbers, then switch simulation. A different alert gives a
to ALT-2071 different decision: here disabling the
account wins
80 to 90 README benchmark line Benchmark result, then: the LLM
s orchestrates, FalkorDB grounds,
deterministic analysis constrains the
action
Add captions (YouTube can auto-generate them; correct the technical words). Upload as
unlisted to YouTube or any host the rules allow, and paste the link in the submission and
the README.
B24. The blog post (the AirPods side prize) and submission
A strong blog post is a design story, not a feature list. Suggested outline, about 1000 to
1500 words:
1. The hook: an alert is cheap, understanding its reach is hard.
2. Why a graph: describe the attack-path question and why joins would struggle. Include
one Cypher query.
3. The architecture: LLM, graph, deterministic engine, and why each part does only what
it is good at.
Page 62 of 77

## PDF page 63

NEXUS Build Specification (Track 1, Graph Hacks)
4. Counterfactual simulation with GRAPH.COPY: the key idea. Show the matrix for
scenario 1.
5. Restraint: scenario 3, where the right decision is to do nothing.
6. Guardrails: simulate before execute, approval gate, rollback, verification.
7. Benchmark results including the misses.
8. Limitations and what you would do next.
Publish on dev.to, Hashnode or Medium and include the link in your submission. Check the
Rules tab for how blog posts must be submitted.
Submission checklist
Rules and FAQ tabs on the hackathon page read in full (judging criteria, required items,
deployment question)
Public repository with README, screenshots, .env.example, no secrets committed
docker compose up --build works from a fresh clone in an empty folder
All tests pass
Benchmark file and numbers in the README
Video under 90 seconds, captions on, link works when logged out
Blog post published and linked
Synthetic data label visible in the UI and README
Team members confirmed before submitting (the team cannot change after
submitting)
Submitted early, not in the last hour
B25. Troubleshooting and pitfalls
Symptom Likely cause and fix
docker: command not found, or cannot Open Docker Desktop and wait until it says
connect to the Docker daemon running
Port 6379 or 3000 already in use Another FalkorDB container is running. Run
docker ps then docker rm -f falkordb
ModuleNotFoundError: engine Run commands from the project root, use
python -m for scripts, and make sure each
folder has an init.py
Page 63 of 77

## PDF page 64

NEXUS Build Specification (Track 1, Graph Hacks)
Symptom Likely cause and fix
Cannot reach FalkorDB The container is not running, or in Docker
the host must be falkordb, not localhost
Syntax error on SET n += $p Your version lacks map merge. Loop over
the properties and SET one by one
Syntax error on a variable-length path with Test the query in the Browser. As a fallback
several relationship types run one query per relationship type and
merge the results in Python
GRAPH.COPY not found Upgrade the image. If still missing, use the
temporary-mutation fallback below
Risk numbers far from the expected table Check edge weights in seed/generate.py,
then K in engine/risk.py. Tune once only
Agent loops without answering The 12-step cap ends it. Tighten the system
prompt, and check tool errors in the trace
Model name rejected Set NEXUS_MODEL in .env to a tool-calling
model your key can use
Tests fail after you executed an action by Re-seed with python -m seed.generate
hand
UI shows nothing Open the browser console (F12) and read
the first red error. Check /docs works
GRAPH.COPY fallback (temporary mutation). In simulate.py replace the copy-and-delete
block with the following. It still measures a real counterfactual but it is not safe for
concurrent users, so state that in the README.
apply_action(live, action, target, subject, 'SIM-TMP')
try:
after = paths.find_attack_paths(live, subject)
after_paths, r = after['paths'],
risk.calculate_risk(after['paths'])
finally:
restore(live, 'SIM-TMP')
Page 64 of 77

## PDF page 65

NEXUS Build Specification (Track 1, Graph Hacks)
Other pitfalls. Always cap path depth and result count. Always filter on status or
containment will appear to do nothing. Never tune weights after seeing results to flatter a
scenario. Never let the model quote a number that is not in a tool result. Do not spend
time on animations.
B26. A ready-to-paste prompt for another AI coding assistant
If you want a different AI (or a human helper) to build this from the document, give it the
whole document and this instruction:
You are building the NEXUS project described in this document for the Graph
Hacks Track 1 hackathon.
Rules:
1. Follow Part B in order, section by section. Create every file exactly as
written, then run the checkpoint that follows it.
2. Do not continue past a failed checkpoint. Fix the cause, re-run, and
report what you changed.
3. Do not change formulas, thresholds, the safety rules or the scenario
structure. If a number looks wrong, tell me and wait.
4. Do not add features that are not in the document.
5. Never hardcode a result to make a checkpoint pass. All scores must be
computed from the graph.
6. Never put secrets in code or commit .env.
7. After each section, give me a short report: files created, command run,
output seen, pass or fail.
8. If a FalkorDB feature behaves differently from the document, use the
fallback listed in B25 and tell me.
Start with B4 and ask me for anything you cannot do yourself, such as
installing Docker or creating an API key.
B27. Your schedule from now to the deadline
The hackathon ends Oct 18 at 11:59 PM IST. Submissions open Oct 17 at 1:03 AM IST. This
plan assumes you start on Oct 16 around midday and works backwards so that you submit
with a buffer.
When (IST) Do Gate
Oct 16, B4 to B7: install, project, FalkorDB, GRAPH.COPY ok
afternoon capability check
Page 65 of 77

## PDF page 66

NEXUS Build Specification (Track 1, Graph Hacks)
When (IST) Do Gate
Oct 16, evening B8 to B10: database helper, seed, Gate A: three scenarios show
paths, risk, impact sensible risk
Oct 16, night B11 to B13: simulation, Pareto, Gate B: three scenarios give three
execute, tools different decisions
Oct 17, morning B14 to B16: agent, backend. Invite Gate C: scripted run works, then a
or find teammates now if you real-key run works
want any
Oct 17, B17 to B19: UI, one-command start, Gates D and E
afternoon tests
Oct 17, evening B20 and B21: benchmark, MCP Benchmark file exists
server. Start the README and
blog draft
Oct 18, morning Record the video (real mode), Video link works
finish README, publish blog
Oct 18, by about Fresh-clone test, then submit Submitted with 8 or more hours to
3 PM spare
Oct 18, evening Only fix typos and broken links.
No new code
If you fall behind, cut in this order: reduce the benchmark size, polish of the graph view,
the MCP inspector test, rollback button polish. Never cut: the real GRAPH.COPY
simulation, the three different decisions, the tests, the one-command start, or the video.
B28. The one-page recap
The graph is the decision substrate: alerts resolve to entities, paths come from Cypher
traversals, containment is status changes on nodes and edges.
Every number comes from computation you can print on screen.
Every candidate action is tested on a graph copy before anything touches the real
graph.
The agent cannot execute an unsimulated action and cannot approve its own high-
impact action.
Three scenarios give three different decisions, including doing nothing.
Page 66 of 77

## PDF page 67

NEXUS Build Specification (Track 1, Graph Hacks)
The benchmark reports its misses.
Everything is labelled synthetic, and every claim is something you measured or
implemented.
When you finish, you will have a project that a judge can run in one command, understand
in ten seconds, and trust because it shows its work.
Part C: The AI Build Kit (How to Build This
With an AI Assistant, and the Premium UI
Spec)
You plan to build NEXUS with an AI coding assistant. That works well if you steer it. The
risk is not that the AI cannot code; it is that it quietly invents FalkorDB features, changes a
number to make a test pass, or builds more than you asked for. Part C gives you a working
method, copy-paste prompts for every phase, an API contract so backend and UI can be
built separately, and a complete minimalist-premium UI specification written so an AI can
implement it exactly.
C1. The working method (follow this and the AI stays on rails)
1. Export this document to Markdown (use the doc menu) and save it in your project
folder as PROJECT.md. Every AI session starts by reading it. This is your single source
of truth.
2. Use one session per phase, not one endless chat. Long chats drift. Start a fresh
session for each prompt in C2 and tell it to read PROJECT.md first.
3. Make the AI restate the plan before it writes code (prompt P0). If the restatement is
wrong, the build will be wrong.
4. Run the checkpoint yourself after every phase. Do not accept the AI saying it works.
You run the command and read the output.
5. Commit to Git after every gate (git add -A and git commit). If a later AI change breaks
things, you can return to the last good state.
6. Mark what must never change. The formulas, thresholds, the scenario structure and
the safety rules. Tell the AI to stop and ask before touching them.
7. Review each change in plain language. Ask the AI: explain what you changed and why,
file by file. If you cannot follow it, ask again simpler.
Page 67 of 77

## PDF page 68

NEXUS Build Specification (Track 1, Graph Hacks)
Suitable tools: Claude Code in the terminal, Cursor, or VS Code with an AI extension. Any
of them works if it can read your project files and run commands. Check the hackathon
FAQ about coding assistants (the page lists a question on it) so you are within the rules,
and mention in your README that you used AI assistance.
C2. Prompts to paste, in order
Replace the text in square brackets only if it applies. Each prompt assumes PROJECT.md
exists in the project root.
P0: alignment check (no code)
Read PROJECT.md completely. Do not write any code yet.
Reply with: (1) the architecture in 8 bullets, (2) the three scenarios and
their expected decisions, (3) the safety rules the code must enforce, (4)
everything marked must-not-change (formulas, thresholds, safety rules,
scenario structure), (5) any ambiguity or risk you see, with your proposed
resolution.
Wait for my reply before continuing.
P1: environment and project skeleton (B4 to B7)
Read PROJECT.md. Implement sections B5 to B7 only: project folders with
__init__.py files, requirements.txt, .env.example, .gitignore, and
check_capabilities.py.
I will run FalkorDB in Docker myself. After creating the files, tell me the
exact commands to run and what output means success. Do not continue to other
sections.
P2: data and engine part 1 (B8 to B10)
Read PROJECT.md. Implement B8, B9 and B10 exactly: engine/db.py,
seed/generate.py, engine/paths.py, engine/risk.py, engine/impact.py and
scripts_demo.py.
Rules: copy the formulas and constants as written. Do not tune any number. If
a FalkorDB syntax in the document fails on my version, show me the error and
propose the smallest fix, then wait.
When done, tell me how to run scripts_demo.py and what table of results I
should expect.
P3: simulation and decisions (B11 to B13)
Page 68 of 77

## PDF page 69

NEXUS Build Specification (Track 1, Graph Hacks)
Read PROJECT.md. Implement B11, B12 and B13: engine/simulate.py,
engine/pareto.py, engine/store.py, engine/execute.py, engine/tools.py and
scripts_decide.py.
Also add the surviving_paths field described in C5.
Safety rules are code, not prompts: execute must reject unsimulated actions,
require approval for HIGH or CRITICAL impact, verify against the simulated
residual risk, and support rollback. Do not hardcode any decision. Sandbox
graphs must always be deleted in a finally block.
Stop after scripts_decide.py runs and shows three different decisions.
P4: agent and backend (B14 to B16)
Read PROJECT.md. Implement B14 and B16: agent/loop.py and api/main.py,
including the /api/investigations/{id} endpoint. Remove the unused package
function.
The agent path must always send approved=False and must block execution when
autonomous is false, in code. Keep scripted mode and real mode separate and
labelled in the response.
After it works, show me a curl command for each endpoint.
P5: baseline UI (B17)
Read PROJECT.md. Implement the baseline ui/index.html from B17 exactly so I
can test the full flow end to end. Do not restyle it yet.
P6: premium UI (C4 to C6)
Read PROJECT.md, especially Part C sections C3 to C6. Rebuild ui/index.html
as the premium minimalist interface described there, in a single file with no
build step, using GSAP from cdnjs for animation.
Keep every API call and field exactly as in the contract in C3. Animate only
transform, opacity and stroke-dashoffset. Respect prefers-reduced-motion.
Build in this order and show me each result before moving on: (1) design
tokens and layout, (2) hero decision with animated risk gauge, (3) attack
path lane, (4) Pareto plot, (5) trace timeline, (6) hold-to-approve button,
(7) hover counterfactual preview.
P7: tests, benchmark, MCP (B19 to B21)
Page 69 of 77

## PDF page 70

NEXUS Build Specification (Track 1, Graph Hacks)
Read PROJECT.md. Implement B19, B20 and B21: tests/test_engine.py,
bench/run_benchmark.py and mcp_server/server.py. Run the tests and report the
real output. Do not weaken or delete a failing test; fix the cause or tell
me.
P8: packaging and docs (B18, B22)
Read PROJECT.md. Implement B18 (Dockerfile, docker-compose.yml,
.dockerignore) and draft README.md following B22. In the README only state
things that are true of the code in this repository. Mark the benchmark
numbers as TO BE FILLED until I run the benchmark.
P9: honesty audit (run this before you submit)
Read PROJECT.md and the whole repository. Audit it against the credibility
rules in B22 and the safety rules in B14 and B13.
List: any hardcoded scores or decisions; any claim in README.md or the UI
that the code does not support (speed, production calibration, attacker
prediction, Pareto, betweenness); any place the agent could execute without
simulation or approval; any secret in the repo; any unlabelled synthetic
data.
For each finding give the file and line and a fix. Do not change code until I
approve.
C3. The API contract (so backend and UI can be built in parallel)
Give this table to whichever AI builds the UI. It must not invent fields beyond it.
Endpoint Method Request Response
/api/alerts GET none list of id, type, raw_text
/api/investigate POST alert_id, mode (auto or the investigation object
mock), autonomous below, plus mode (llm or
(true or false) scripted), trace and summary
/api/investigations/{id} GET none the investigation object
below
Page 70 of 77

## PDF page 71

NEXUS Build Specification (Track 1, Graph Hacks)
Endpoint Method Request Response
/api/contain POST investigation_id ok, before, after, before_label,
(optional action and after_label, verified, or ok
target) false with error
(APPROVAL_REQUIRED,
REJECTED...)
/api/rollback POST investigation_id ok, risk_now
/api/graph/{id} GET none nodes (id, label, name, status)
and edges (source, target,
type)
The investigation object:
investigation_id: text
initial: score (0 to 100), label (LOW, MEDIUM, HIGH, CRITICAL), raw, K, terms (list of
target, criticality, privilege, reach_probability, paths, term)
matrix: list of rows with action, target, residual_risk, residual_label, paths_before,
paths_after, paths_broken, surviving_paths (list of indexes into the base paths that
remain), impact, impact_label, needs_approval, dominated_by (text or null)
recommendation: action, target, requires_approval, why
executed: null, or action, target, before, after, verified
Each trace step: step, tool, args, cypher (text or null), summary, ms.
C4. The premium UI design system
Goal: minimalist, calm, expensive. The look comes from restraint: few colors, lots of space,
precise typography, and motion that explains what the system is doing.
Tokens
Token Value
Background #0A0B0D
Surface #111317
Surface raised #161A20
Page 71 of 77

## PDF page 72

NEXUS Build Specification (Track 1, Graph Hacks)
Token Value
Border rgba(255,255,255,0.06)
Text #E8EAED
Muted text #8B929C
Accent (one only) #7C9CFF
Risk low, medium, high, critical #4ADE80, #FACC15, #FB923C, #F87171
Fonts Inter for text, JetBrains Mono for node ids and
Cypher. Load both from Google Fonts
Numbers font-variant-numeric: tabular-nums everywhere so
digits never jitter
Radius 14px for cards, 999px for pills
Spacing 8px grid. Card padding 24px. Page max width
1280px
Easing cubic-bezier(0.16, 1, 0.3, 1) for almost everything
Durations 180 ms micro, 320 ms standard, 900 to 1400 ms for
hero moments
Rules: no heavy shadows, no gradients except the cursor glow and the gauge arc, no more
than one accent, thin 1px borders, generous whitespace, uppercase tiny labels with letter
spacing for section titles.
Layout (desktop)
1. Top bar: NEXUS wordmark, a small SYNTHETIC DATA pill, a segmented control for the
three alerts, a segmented switch for Real agent or Scripted tools, an Autonomous
switch.
2. Hero decision card, full width.
3. Row two: attack path lane (7 columns) and Pareto plot (5 columns).
4. Row three: agent trace (5 columns) and explanation with the why-score bar (7
columns).
On narrow screens everything stacks in that order.
Page 72 of 77

## PDF page 73

NEXUS Build Specification (Track 1, Graph Hacks)
Components and their motion
1. Hero decision card (data: initial, recommendation, executed).
A 270 degree SVG arc gauge. The arc length animates with stroke-dashoffset from 0 to
score over about 1.2 s. The big number counts up in step using a GSAP tween on a plain
object. The arc color blends to the risk band color.
Beside it: the alert id, the recommended action as a chip (for example ISOLATE
DEVICE and LAPTOP-042), and the why text in muted type.
The action button on the right. After execution the number tweens down from the old
score to executed.after, the arc recolors, and a small check mark draws itself (stroke-
dashoffset) if executed.verified is true. A quiet Rollback link replaces the button.
2. Attack path lane (data: /api/graph/{id}).
Custom SVG, not a generic graph library. Compute each node's column as its distance
from the start node, so the picture reads left to right: person, device, servers, account,
service, data store.
Nodes are small circles with a monospace label below. Edges are curved paths with
1.5px strokes.
On load, a bright pulse travels along each attack path from start to data store (animate
a gradient or dash along the edge, staggered by 150 ms per path).
On containment, every node whose status is not ACTIVE gets a red ring that scales in
with a single small shake. Edges touching it break (dash gap opens) and fade to 15
percent opacity. Surviving paths keep pulsing.
Hover a node: show a small tooltip with its label, status and, if present, token age.
3. Pareto plot (data: matrix).
SVG about 360 by 240. X axis is business impact (0 to 100), Y axis is residual risk (0 to
100, low at the bottom). Light grid at 25, 50, 75.
Each action is a dot. Dots spring in from the origin with a 60 ms stagger. The frontier
(rows where dominated_by is null) is joined by a polyline that draws itself. Dominated
dots drop to 35 percent opacity.
The recommended dot gets a soft pulsing ring. Hovering a dot or a matrix row shows its
name and numbers.
This chart is the visual proof of the trade-off between safety and disruption.
4. Matrix rows (data: matrix).
Page 73 of 77

## PDF page 74

NEXUS Build Specification (Track 1, Graph Hacks)
A slim list under or beside the plot: action, target, residual risk, paths broken, impact.
The recommended row has an accent left border.
Hover counterfactual preview: when the pointer is over a row, dim every attack path in
the lane that is not in that row's surviving_paths. The viewer sees which routes that
action would cut, before anything is executed. Release and everything restores
smoothly over 200 ms.
5. Agent trace timeline (data: trace).
A thin vertical line that grows downward as each step appears (step by step, 250 ms
apart, matching the order of real tool calls).
Each step: a dot that pulses while appearing, the tool name in monospace, a one-line
summary, the duration in milliseconds, and a Show Cypher disclosure that expands
with an animated height change.
Do not fake typing. Show real steps from the response.
6. Explanation panel (data: summary, initial.terms).
Reveal the summary line by line with a 120 ms fade and 6px upward slide per line. The
text is complete; only the reveal is animated.
Below it, a why-score stacked bar: each term in initial.terms becomes a segment whose
width is term divided by raw. Segments grow from zero width. Labels show the target
id and the term value.
7. Hold-to-approve button.
If recommendation.requires_approval is true, the button reads HOLD TO APPROVE. A
ring around it fills over 1 s while the pointer or finger is down. Releasing early reverses
the ring. Completing it calls /api/contain. This makes the human approval gate
something you feel and something you can show in the video.
If approval is not required the button reads CONTAIN and acts on a normal click.
8. Small touches that add the premium feel.
A very faint radial glow that follows the cursor (set CSS variables on mousemove, low
opacity).
Skeleton shimmer in cards while the investigation runs.
A toast at the bottom for results such as risk 80 to 0, verified.
A Replay button that re-runs the animations from the stored result without calling the
backend (useful for filming).
Keyboard: Enter investigates, Escape closes expanded Cypher.
Page 74 of 77

## PDF page 75

NEXUS Build Specification (Track 1, Graph Hacks)
Motion rules
Animate only transform, opacity and stroke-dashoffset. Never animate width, height or
top and left of large layouts (the stacked bar and the Cypher disclosure are the only
exceptions and are small).
Use springs or the expo-out easing above. No bounce on data, no spinning logos,
nothing that moves without meaning.
Respect prefers-reduced-motion: in that mode skip the traveling pulses and counts
and just fade states in.
Target 60 frames per second. Check by recording the screen.
C5. The one engine change the hover preview needs
The preview needs to know which attack paths survive each action, not just how many. In
engine/simulate.py, inside simulate(), compute the surviving indexes and add them to
each matrix row.
base_keys = [tuple(p['ids']) for p in base['paths']]
Place the line above right after base is computed. Then, after after_paths is known for a
row (for monitor_only it equals the base paths), add:
after_keys = {tuple(p['ids']) for p in after_paths}
surviving = [i for i, k in enumerate(base_keys) if k in after_keys]
and add 'surviving_paths': surviving to the dictionary appended to rows. The list
base_paths stored in the record already has the paths in the same order, so index i in
surviving_paths refers to index i in base_paths. The UI then maps each base path to the
edges it uses. Nothing else changes, and the unit tests still pass.
Page 75 of 77

## PDF page 76

NEXUS Build Specification (Track 1, Graph Hacks)
C6. One big prompt for the UI, if you prefer a single instruction
Read PROJECT.md Part C. Build ui/index.html as one self-contained file (HTML,
CSS, JS, no build step). Load GSAP from cdnjs and Inter plus JetBrains Mono
from Google Fonts.
Design: dark minimalist premium. Use exactly the tokens in C4. One accent
colour. Thin borders. Lots of space.
Data: use only the endpoints and fields in the API contract in C3.
Components: top bar with scenario segmented control, mode switch and
autonomous switch; hero decision card with an animated 270 degree arc gauge
and counting number; attack path lane as a custom SVG with traveling pulses
and a break animation on containment; Pareto scatter plot with a self-drawing
frontier line; matrix rows with hover counterfactual preview using
surviving_paths; agent trace timeline with expandable Cypher; explanation
panel with line reveal and a stacked why-score bar; hold-to-approve button;
cursor glow; skeleton loading; toast; Replay button.
Constraints: animate only transform, opacity and stroke-dashoffset (small
exceptions allowed for the stacked bar and the disclosure height). Respect
prefers-reduced-motion. Work at 360px width. No invented data: if a field is
missing, hide that element.
After building, list each component and the API field it reads, so I can
verify nothing is faked.
C7. UI acceptance checklist
The decision is readable within 3 seconds of opening the page
Every number on screen comes from an API field (the AI listed the mapping)
The risk number after containment matches the verified value
The hover preview dims exactly the paths that action would cut
Hold-to-approve appears only when requires_approval is true
SYNTHETIC DATA label is visible at all times
Works at phone width and with reduced motion turned on
No console errors; animations stay smooth while recording the video
Page 76 of 77

## PDF page 77

NEXUS Build Specification (Track 1, Graph Hacks)
C8. Where AI assistants usually go wrong here, and how to correct
them
Failure What to say
Invents a FalkorDB function or procedure Test that call in the FalkorDB Browser. If it
fails, use the fallback in B25 or a plain Python
implementation
Changes a constant or threshold to pass a Revert it. Those are must-not-change. Show
test me the failing output instead
Hardcodes the expected decision Remove it. Decisions must come from the
simulation and policy code. Add a test that
would fail if it were hardcoded
Builds extra features (login, memory, Out of scope. Remove them and keep to
charts) PROJECT.md
Says it is done without running anything Run the checkpoint command and paste the
real output
Rewrites large files when you asked for a Ask for the smallest possible change and
small fix show the diff
Puts the API key in code Move it to .env and confirm .env is ignored by
Git
Over-animates Remove any animation that does not show a
real event in the pipeline
C9. Time-boxing with AI (about 2.5 days left)
Spend your hours on gates, not on writing code. The AI writes; you verify.
If a phase burns more than 90 minutes without passing its checkpoint, stop, paste the
exact error and the relevant file into a fresh session, and ask for the smallest fix.
Build the plain baseline UI (P5) and get a full end-to-end run before the premium UI
(P6). A working ugly demo beats a beautiful broken one, and the baseline is your
fallback if P6 goes wrong.
Freeze all code at the point you start recording the video, apart from fixes to anything
that breaks the demo.
Page 77 of 77