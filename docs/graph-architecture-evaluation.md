# NEXUS Graph Architecture & Physics Engine Research Report

**Date:** 2026-10-16  
**Subject:** Cybersecurity Attack Graph Visualization, Layout Engines, and Interactive Force-Directed Physics  
**Branch:** `feature/advanced-attack-graph-physics`

---

## 1. Phase 1 — Technical Audit of Existing NEXUS Graph Pipeline

Before evaluating external visualization and layout libraries, we performed a thorough inspection of the NEXUS codebase, tracing attack graph data from database storage to the browser canvas.

### 1.1 Data Origin and Schema (FalkorDB)
- **Seeding (`seed/generate.py`)**:
  - The deterministic synthetic graph comprises 157 nodes representing an enterprise IT/OT environment.
  - **Entity Labels**: `Person`, `Device`, `Server`, `ServiceAccount`, `Service`, `DataStore`, `Vulnerability`, `IPAddress`, and `Alert`.
  - **Relationships**: `OWNS`, `LOGS_INTO`, `HAS_ACCESS_TO`, `HOSTS_CREDENTIAL`, `AUTHENTICATES_TO`, `READS`, `DEPENDS_ON`, `ATTRIBUTED_TO`.
  - **Attributes**:
    - Nodes carry `id` (e.g., `U-ALEX`, `LAPTOP-042`, `DS-CROWN-01`), `name`, `status` (`ACTIVE`, `ISOLATED`, `DISABLED`, `QUARANTINED`), and domain metrics (`criticality`, `privilege`, `business_value`).
    - Relationships carry `status` and `exploit` weights (0.1 to 0.95).

### 1.2 Path Discovery & Risk Calculations (`engine/paths.py`, `engine/risk.py`)
- Attack paths are discovered via parameterized Cypher traversals up to 7 hops:
  ```cypher
  MATCH p=(s {id:$start})-[:OWNS|LOGS_INTO|HAS_ACCESS_TO|HOSTS_CREDENTIAL|AUTHENTICATES_TO|READS*1..7]->(d:DataStore)
  WHERE d.criticality >= 7
    AND all(n IN nodes(p) WHERE coalesce(n.status,'ACTIVE') = 'ACTIVE')
    AND all(r IN relationships(p) WHERE coalesce(r.status,'ACTIVE') = 'ACTIVE')
  RETURN [n IN nodes(p) | n.id] AS ids,
         [r IN relationships(p) | type(r)] AS types,
         [r IN relationships(p) | r.exploit] AS exploit_weights,
         [n IN nodes(p) | coalesce(n.privilege, -1.0)] AS privileges,
         d.id AS target, d.criticality AS criticality
  ```
- **Exploitability**: Multiplicative product of edge weights along the chain.
- **Risk Formula**: Noisy-OR formula combining exploitability, target criticality, and maximum privilege:
  $$\text{Risk} = \text{round}\left(100 \times \left(1 - \exp\left(-\frac{\sum \text{terms}}{4.0}\right)\right)\right)$$
- Results are stored in memory (`engine/store.py`) keyed by `investigation_id`.

### 1.3 Subgraph API Endpoint (`api/main.py`)
- Endpoint: `GET /api/graph/{investigation_id}`
- Resolves the investigation record, extracts all unique node IDs across `record["base_paths"]`, queries FalkorDB for real-time node metadata:
  ```cypher
  MATCH (n) WHERE n.id IN $ids
  RETURN n.id, labels(n)[0], n.name, coalesce(n.status, 'ACTIVE')
  ```
- Constructs directed edge tuples `(source, target, type)` and returns:
  ```json
  {
    "nodes": [{"id": "...", "label": "Device", "name": "LAPTOP-042", "status": "ACTIVE"}],
    "edges": [{"source": "U-ALEX", "target": "LAPTOP-042", "type": "OWNS"}]
  }
  ```

### 1.4 Client-Side Visualization (`ui/index.html`)
- Cytoscape.js is loaded via CDN (`cytoscape.min.js`, v3.30.2).
- Graph initialization parses nodes into Cytoscape data models (`data: { id, label, kind, bad }`).
- Styling uses declarative Cytoscape CSS selectors:
  - Shape & color mapping per entity kind (e.g. `DataStore` barrel in crimson red, `Device` round-rectangle in sky cyan).
  - High-contrast edge labels rendered on contrast pill badges (`text-background-color: #0B111E`, `text-rotation: autorotate`).
- Layout lifecycle: Initial layout executes `cose` (Compound Spring Embedder).

---

## 2. Phase 2 — In-Depth Repository Research

We conducted deep technical evaluations of the four candidate libraries:
1. **Cytoscape.js** (`cytoscape/cytoscape.js`)
2. **fCoSE** (`iVis-at-Bilkent/cytoscape.js-fcose`)
3. **CoSE-Bilkent** (`cytoscape/cytoscape.js-cose-bilkent`)
4. **vis-network** (`visjs/vis-network`)

### 2.1 Cytoscape.js Core (`cytoscape/cytoscape.js`)
- **Architecture**: Headless graph theory architecture separating graph structure, layout calculation, and rendering (HTML5 Canvas).
- **Renderer**: High-performance multi-layered canvas (node layer, edge layer, drag/selection layer). Supports curved bezier edges, customizable arrowheads, and compound parent-child hierarchies.
- **Built-in `cose` Layout**:
  - Located in `src/extensions/layout/cose.js`.
  - Implements a Compound Spring Embedder using simulated annealing.
  - Iterates for a fixed count (`numIter: 600`), cooling temperature from initial to final value.
  - **Limitation**: `cose` is a **one-time batch layout**. Once temperature cools to zero, it dispatches `layoutstop` and terminates. Dragging a node in Cytoscape does not re-simulate other nodes unless a layout is actively running.

### 2.2 fCoSE (`iVis-at-Bilkent/cytoscape.js-fcose`)
- **Architecture**: Fast Compound Spring Embedder developed by i-Vis Lab at Bilkent University. Successor to `cose-bilkent`.
- **Algorithm**:
  1. *Spectral Phase*: Computes an initial layout in $O(V)$ time using eigenvector projection, eliminating line-crossing tangles early.
  2. *Force-Directed Phase*: Applies spring and repulsion forces with non-uniform node sizes and compound structures.
  3. *Constraint Enforcement*: Supports fixed node positions, horizontal/vertical alignment constraints, and relative placement rules.
- **Performance**: Up to 2x faster than `cose-bilkent` on dense graphs.
- **Limitation**: Like `cose`, `fCoSE` is a **batch convergence algorithm** (`layout.run()`). It is designed to compute a clean static equilibrium and stop. It does not provide real-time 60 FPS physics during user dragging. Furthermore, it introduces 2 external dependencies (`layout-base` and `cose-base`).

### 2.3 CoSE-Bilkent (`cytoscape/cytoscape.js-cose-bilkent`)
- **Architecture**: Previous generation compound spring embedder from Bilkent University.
- **Algorithm**: Pure spring embedder with grid-based spatial indexing for repulsion.
- **Limitation**: Superseded by `fCoSE`. Lacks the spectral draft phase, converges slower on graphs with >50 nodes, and lacks user constraint support. Also a batch algorithm without continuous drag physics.

### 2.4 vis-network (`visjs/vis-network`)
- **Architecture**: Monolithic visualization library with tightly integrated physics engine (`lib/network/modules/PhysicsEngine.js`).
- **Physics Solvers**:
  - `barnesHut`: Quadtree-based $N$-body approximation ($O(N \log N)$), ideal for general network layouts.
  - `repulsion`: Direct $O(N^2)$ Coulomb repulsion with customizable distance cutoff.
  - `forceAtlas2Based`: Spatial clustering layout with degree-weighted repulsion.
- **Live Dragging**: Genuinely supports continuous physics during drag:
  - When `physics.enabled: true`, dragging node $A$ locks its coordinates to the cursor while spring forces immediately pull connected neighbors, and Barnes-Hut repulsion pushes colliding nodes away.
  - When the node is released, it carries release momentum and the network stabilizes.
- **Drawbacks & Limitations for NEXUS**:
  - **Styling Architecture**: Relies on imperative JavaScript options rather than declarative CSS-like stylesheets. Custom states (such as `.obsidian-dimmed`, `.obsidian-focused`, dashed quarantine rings, high-contrast text pill backgrounds) require custom canvas hooks (`beforeDrawing`, `afterDrawing`) or frequent mutations to `DataSet`.
  - **Specification Alignment**: The project specification (`PROJECT.md`) explicitly specifies Cytoscape.js for the graph view.
  - **Bundle Footprint**: Large standalone library (~700 KB minified) replacing an already functional Cytoscape.js setup.

---

## 3. The Three Physics Paradigms Explained

Understanding the exact operational differences between physics models is critical to choosing the correct architecture:

| Paradigm | How It Works | Drag Behavior | CPU Usage | Best Use Case |
|---|---|---|---|---|
| **1. One-Time Force-Directed Layout** (`cose`, `fcose`, `cose-bilkent`) | Computes $N$ mathematical iterations, cools temperature, positions nodes, and terminates. | Moving a node moves only that node; all other nodes remain completely static. | 0% at rest. | Initial graph organization, report rendering, printing diagrams. |
| **2. Stabilized Simulation with Restart** (`vis-network` with stabilization) | Runs physics behind the scenes until kinetic energy drops below threshold, then sleeps. Wakes on user interaction. | Dragging a node wakes the engine; springs pull neighbors; settles when released. | Active only during stabilization and drag. | Interactive exploration where static resting state is desired. |
| **3. Continuous Dynamic Simulation** (Verlet/Euler force-directed loop) | Runs a 60 FPS physics loop calculating inter-node repulsion, edge springs, and gravity. | Dragging a node stretches connected springs in real time, pulling neighbors in an organic wave. Graph settles dynamically into new resting positions. | Light continuous computation (~1-2ms per frame). | Fluid, living network visualizers (Obsidian Graph View, Cyber SOC topologies). |

---

## 4. Comprehensive Comparison Matrix

| Evaluation Criterion | Cytoscape.js (Core CoSE) | Cytoscape + fCoSE | Cytoscape + CoSE-Bilkent | vis-network | Cytoscape.js + Custom 60 FPS Physics Engine |
|---|---|---|---|---|---|
| **Existing Stack Fit** | Native (already in NEXUS) | High (Cytoscape plugin) | High (Cytoscape plugin) | Low (complete rewrite) | **Native (built on Cytoscape)** |
| **Force-Directed Quality** | Very Good (CoSE) | Excellent (Spectral + CoSE) | Very Good | Very Good (Barnes-Hut) | **Superior (Hybrid CoSE + Force)** |
| **Repulsion & Spacing** | Configurable (`nodeRepulsion`) | Configurable (`nodeRepulsion`) | Configurable | High (`gravitationalConstant`) | **Parametric (Live Sliders)** |
| **Live Physics on Drag** | ❌ None (batch only) | ❌ None (batch only) | ❌ None (batch only) | ✅ Native | **✅ Full 60 FPS Spring Chain** |
| **Node/Edge Styling** | Declarative CSS selectors | Declarative CSS selectors | Declarative CSS selectors | Imperative Options API | **Declarative CSS + Obsidian Aura** |
| **Label Readability** | Contrast pills, autorotate | Contrast pills, autorotate | Contrast pills, autorotate | Canvas baseline text | **Autorotate Contrast Badges** |
| **Attack-Path Highlighting** | Class-based selector API | Class-based selector API | Class-based selector API | Complex DataSet updates | **Instant Focus / Dim Spotlight** |
| **Performance (Small/Med)** | 60 FPS | 60 FPS | 60 FPS | 60 FPS | **60 FPS Hardware Accelerated** |
| **Large Graph Scalability** | Excellent | Exceptional | Good | Good | **Clamped Verlet with Dormancy** |
| **Position Locking** | Native (`node.lock()`) | Supported (Constraints) | ❌ No constraints | Supported | **Native Interactive Lock/Unlock** |
| **External Dependencies** | 0 (pure Cytoscape) | 2 (`layout-base`, `cose-base`) | 1 (`cose-bilkent`) | 1 (`vis-network`) | **0 Extra Dependencies** |
| **License** | MIT | MIT | MIT | Apache-2.0 / MIT | **MIT** |
| **Memory / Teardown Safety** | Clean | Clean | Clean | Needs destroy() | **Full requestAnimationFrame cleanup** |

---

## 5. Architecture Decision & Rationale

### Selected Architecture:
**Cytoscape.js paired with an Integrated 60 FPS Force-Directed Physics Engine**

### Rationale:
1. **Preserves Security Semantics & Declarative Styling**:
   Cytoscape.js provides the industry standard for graph stylesheet declarations. We preserve entity-specific shapes, high-contrast labels, dashed alert borders, and the Obsidian focus halo without brittle canvas hacking.
2. **True Interactive Physics Without Dependency Bloat**:
   Neither `fCoSE` nor `cose-bilkent` provides live dragging physics—both are batch layouts that stop after cooling. Switching to `vis-network` would violate the project specification and break existing Cytoscape stylesheets.
   By implementing a mathematically sound, Euler-Verlet force-directed simulation on top of Cytoscape.js, we achieve:
   - True inter-node Coulomb repulsion ($F = k / d^2$).
   - True Hooke's Law edge elasticity ($F = k \cdot (d - L)$).
   - Gravitational centering to prevent drift.
   - Dynamic spring-chain dragging where moving any node pulls its connected neighbors in real time.
   - Interactive physics controls (Forces drawer with Repulsion, Link Distance, Spring Force, Gravity sliders, Pause/Resume, and Node Pinning).
3. **Zero External Flakiness**:
   Requires no extra CDN dependencies that could fail in offline or air-gapped test environments.
