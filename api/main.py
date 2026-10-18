import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import loop
from engine import execute, store
from engine.db import graph
from seed.generate import build as rebuild_demo_graph

app = FastAPI(title="NEXUS")


class InvestigateReq(BaseModel):
    alert_id: str
    mode: str = "auto"
    autonomous: bool = False


class ActReq(BaseModel):
    investigation_id: str
    action: str = ""
    target: str | None = None


class CypherReq(BaseModel):
    query: str


def _serialize_cell(val):
    if hasattr(val, "properties") and hasattr(val, "labels"):
        return {"_type": "Node", "labels": val.labels, "properties": val.properties}
    if hasattr(val, "properties") and hasattr(val, "relation"):
        return {"_type": "Edge", "relation": val.relation, "properties": val.properties}
    if hasattr(val, "nodes") and hasattr(val, "relationships"):
        return {"_type": "Path", "length": len(val.relationships)}
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    if isinstance(val, (list, tuple)):
        return [_serialize_cell(x) for x in val]
    if isinstance(val, dict):
        return {k: _serialize_cell(v) for k, v in val.items()}
    return str(val)


@app.post("/api/cypher")
@app.post("/cypher")
def run_cypher(req: CypherReq):
    start = time.perf_counter()
    query_str = (req.query or "").strip()
    if not query_str:
        raise HTTPException(400, "Query cannot be empty")
    try:
        res = graph().query(query_str)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        headers = []
        if hasattr(res, "header") and res.header:
            headers = [
                h[1] if isinstance(h, (list, tuple)) and len(h) > 1 else str(h)
                for h in res.header
            ]
        elif hasattr(res, "result_set") and res.result_set:
            headers = [f"col_{i}" for i in range(len(res.result_set[0]))]

        rows = []
        for row in (res.result_set or [])[:100]:
            rows.append([_serialize_cell(c) for c in row])

        return {
            "ok": True,
            "latency_ms": elapsed_ms,
            "headers": headers,
            "rows": rows,
            "total_count": len(res.result_set) if res.result_set else 0,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "ok": False,
            "latency_ms": elapsed_ms,
            "error": str(exc),
        }


@app.get("/api/health")
@app.get("/health")
def health():
    start = time.perf_counter()
    try:
        g = graph()
        node_res = g.query("MATCH (n) RETURN count(n)").result_set
        node_count = node_res[0][0] if node_res else 0
        edge_res = g.query("MATCH ()-[r]->() RETURN count(r)").result_set
        edge_count = edge_res[0][0] if edge_res else 0

        # Check for any active containment mutations or saved incidents in FalkorDB
        mutated_res = g.query("MATCH (n) WHERE coalesce(n.status, 'ACTIVE') <> 'ACTIVE' RETURN count(n), collect(n.id)").result_set
        mutated_count = mutated_res[0][0] if mutated_res else 0
        mutated_ids = [str(x) for x in (mutated_res[0][1] or [])] if mutated_res else []

        inc_res = g.query("MATCH (inc:Incident) RETURN count(inc), collect(inc.action + ' ' + coalesce(inc.target, ''))").result_set
        incident_count = inc_res[0][0] if inc_res else 0
        saved_actions = [str(x).strip() for x in (inc_res[0][1] or [])] if inc_res else []

        is_pristine = (mutated_count == 0 and incident_count == 0)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "healthy",
            "falkordb_connected": True,
            "latency_ms": latency_ms,
            "node_count": node_count,
            "edge_count": edge_count,
            "is_pristine": is_pristine,
            "mutated_count": mutated_count,
            "mutated_ids": mutated_ids,
            "incident_count": incident_count,
            "saved_actions": saved_actions,
            "synthetic_dataset": True,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "unhealthy",
            "falkordb_connected": False,
            "latency_ms": latency_ms,
            "is_pristine": True,
            "mutated_count": 0,
            "saved_actions": [],
            "error": str(exc),
        }


@app.get("/api/history")
@app.get("/history")
def incident_history():
    try:
        rows = graph().query(
            """
            MATCH (inc:Incident)
            OPTIONAL MATCH (inc)-[:CONTAINED_ENTITY]->(t)
            RETURN inc.id, inc.alert_id, inc.action, coalesce(t.name, inc.target), inc.status, inc.timestamp
            ORDER BY inc.timestamp DESC
            LIMIT 10
            """
        ).result_set
        return [
            {
                "id": r[0],
                "alert_id": r[1],
                "action": r[2],
                "target": r[3],
                "status": r[4],
                "timestamp": r[5],
            }
            for r in rows
        ]
    except Exception:
        return []


@app.get("/api/alerts")
@app.get("/alerts")
def alerts():
    rows = graph().query(
        "MATCH (a:Alert) RETURN a.id, a.type, a.raw_text ORDER BY a.id"
    ).result_set
    return [{"id": row[0], "type": row[1], "raw_text": row[2]} for row in rows]


@app.post("/api/reset")
@app.post("/reset")
def reset_demo():
    count = rebuild_demo_graph()
    try:
        graph().query("MATCH (inc:Incident) DETACH DELETE inc")
    except Exception:
        pass
    store.clear()
    return {"ok": True, "nodes": count, "message": "Synthetic demo graph restored."}


@app.post("/api/investigate")
@app.post("/investigate")
def investigate(request: InvestigateReq):
    rows = graph().query(
        "MATCH (a:Alert {id:$id}) RETURN a.raw_text", {"id": request.alert_id}
    ).result_set
    if not rows:
        raise HTTPException(404, "unknown alert")
    mock = request.mode == "mock" or os.getenv("MOCK_LLM") == "1" or not os.getenv("ANTHROPIC_API_KEY")
    runner = loop.run_scripted if mock else loop.run_llm
    res = runner(request.alert_id, rows[0][0], request.autonomous)
    try:
        hist_rows = graph().query(
            """
            MATCH (inc:Incident)
            OPTIONAL MATCH (inc)-[:CONTAINED_ENTITY]->(t)
            RETURN inc.id, inc.alert_id, inc.action, coalesce(t.name, inc.target), inc.status, inc.timestamp
            ORDER BY inc.timestamp DESC
            LIMIT 5
            """
        ).result_set
        res["history"] = [
            {
                "id": r[0],
                "alert_id": r[1],
                "action": r[2],
                "target": r[3],
                "status": r[4],
                "timestamp": r[5],
            }
            for r in hist_rows
        ]
    except Exception:
        res["history"] = []
    return res


@app.post("/api/contain")
@app.post("/contain")
def contain(request: ActReq):
    record = store.get(request.investigation_id)
    if not record:
        raise HTTPException(404, "unknown investigation")
    recommendation = record["recommendation"]
    action = request.action or recommendation["action"]
    target = request.target if request.action else recommendation["target"]
    # This endpoint represents the explicit human CONTAIN/approval action.
    return execute.execute(request.investigation_id, action, target, approved=True)


@app.post("/api/rollback")
@app.post("/rollback")
def rollback(request: ActReq):
    return execute.rollback(request.investigation_id)


@app.get("/api/investigations/{investigation_id}")
@app.get("/investigations/{investigation_id}")
def investigation(investigation_id: str):
    record = store.get(investigation_id)
    if not record:
        raise HTTPException(404, "unknown investigation")
    try:
        hist_rows = graph().query(
            """
            MATCH (inc:Incident)
            OPTIONAL MATCH (inc)-[:CONTAINED_ENTITY]->(t)
            RETURN inc.id, inc.alert_id, inc.action, coalesce(t.name, inc.target), inc.status, inc.timestamp
            ORDER BY inc.timestamp DESC
            LIMIT 5
            """
        ).result_set
        history = [
            {
                "id": r[0],
                "alert_id": r[1],
                "action": r[2],
                "target": r[3],
                "status": r[4],
                "timestamp": r[5],
            }
            for r in hist_rows
        ]
    except Exception:
        history = []
    return {
        "mode": "scripted",
        "trace": [],
        "summary": "Investigation state refreshed.",
        "investigation_id": investigation_id,
        "initial": record["initial"],
        "matrix": record["matrix"],
        "recommendation": record["recommendation"],
        "evidence_paths": record["base_paths"][:3],
        "evidence_path_count": len(record["base_paths"]),
        "executed": record.get("executed"),
        "falkordb_memory": record.get("falkordb_memory"),
        "history": history,
    }


@app.get("/api/graph/{investigation_id}")
@app.get("/graph/{investigation_id}")
def subgraph(investigation_id: str):
    record = store.get(investigation_id)
    if not record:
        raise HTTPException(404, "unknown investigation")
    path_node_ids = set()
    edges = set()
    for path in record.get("base_paths", []):
        for node_id in path["ids"]:
            path_node_ids.add(node_id)
        for index, relationship in enumerate(path["types"]):
            edges.add((path["ids"][index], path["ids"][index + 1], relationship, True))
    
    # If 0 critical paths found, fetch the local benign ego-network around the subject
    if not path_node_ids and record.get("subject"):
        subj = record["subject"]
        ego_res = graph().query(
            """
            MATCH (s {id:$subj})-[r:OWNS|LOGS_INTO|AUTHENTICATES_TO|USED_BY|ABOUT*1..2]-(m)
            RETURN s.id, labels(s)[0], s.name, coalesce(s.status, 'ACTIVE'), properties(s),
                   m.id, labels(m)[0], m.name, coalesce(m.status, 'ACTIVE'), properties(m)
            LIMIT 20
            """,
            {"subj": subj}
        ).result_set
        ego_nodes = {}
        for r in ego_res:
            ego_nodes[r[0]] = {"id": r[0], "label": r[1], "name": r[2], "status": r[3], "properties": dict(r[4] or {})}
            ego_nodes[r[5]] = {"id": r[5], "label": r[6], "name": r[7], "status": r[8], "properties": dict(r[9] or {})}
        if not ego_nodes:
            s_row = graph().query("MATCH (s {id:$subj}) RETURN s.id, labels(s)[0], s.name, coalesce(s.status, 'ACTIVE'), properties(s)", {"subj": subj}).result_set
            if s_row:
                ego_nodes[subj] = {"id": s_row[0][0], "label": s_row[0][1], "name": s_row[0][2], "status": s_row[0][3], "properties": dict(s_row[0][4] or {})}
        edge_res = graph().query(
            """
            MATCH (a)-[r]->(b)
            WHERE a.id IN $ids AND b.id IN $ids
            RETURN a.id, b.id, type(r)
            """,
            {"ids": list(ego_nodes.keys())}
        ).result_set if ego_nodes else []
        return {
            "nodes": list(ego_nodes.values()),
            "edges": [{"source": r[0], "target": r[1], "type": r[2], "is_path": False} for r in edge_res],
            "is_benign": True,
        }

    # 1. Query path nodes with full properties
    path_nodes_res = graph().query(
        """
        MATCH (n) WHERE n.id IN $path_ids
        RETURN n.id, labels(n)[0], n.name, coalesce(n.status, 'ACTIVE'), properties(n)
        """,
        {"path_ids": list(path_node_ids)}
    ).result_set

    all_nodes = {}
    for r in path_nodes_res:
        all_nodes[r[0]] = {
            "id": r[0],
            "label": r[1],
            "name": r[2] or r[0],
            "status": r[3],
            "is_path_node": True,
            "properties": dict(r[4] or {}),
        }

    # 2. Query contextual cyber intelligence around path nodes
    alert_id = record.get("alert_id")

    ctx_out = graph().query(
        """
        MATCH (n)-[r]->(m)
        WHERE n.id IN $path_ids AND type(r) IN ['AFFECTED_BY', 'DEPENDS_ON', 'USED_BY', 'ABOUT']
        RETURN n.id, type(r), m.id, labels(m)[0], m.name, coalesce(m.status, 'ACTIVE'), properties(m)
        """,
        {"path_ids": list(path_node_ids)}
    ).result_set

    ctx_in = graph().query(
        """
        MATCH (m)-[r]->(n)
        WHERE n.id IN $path_ids AND type(r) IN ['AFFECTED_BY', 'DEPENDS_ON', 'USED_BY', 'ABOUT']
        RETURN m.id, type(r), n.id, labels(m)[0], m.name, coalesce(m.status, 'ACTIVE'), properties(m)
        """,
        {"path_ids": list(path_node_ids)}
    ).result_set

    for src, rel, tgt, label, name, status, props in ctx_out:
        if label == "Alert" and tgt != alert_id:
            continue
        if tgt not in all_nodes:
            all_nodes[tgt] = {
                "id": tgt,
                "label": label,
                "name": name or tgt,
                "status": status,
                "is_path_node": False,
                "properties": dict(props or {}),
            }
        edges.add((src, tgt, rel, False))

    for src, rel, tgt, label, name, status, props in ctx_in:
        if label == "Alert" and src != alert_id:
            continue
        if src not in all_nodes:
            all_nodes[src] = {
                "id": src,
                "label": label,
                "name": name or src,
                "status": status,
                "is_path_node": False,
                "properties": dict(props or {}),
            }
        edges.add((src, tgt, rel, False))

    formatted_edges = [
        {"source": src, "target": tgt, "type": rel, "is_path": is_path}
        for src, tgt, rel, is_path in sorted(edges, key=lambda x: (not x[3], x[0], x[1]))
    ]

    return {
        "nodes": list(all_nodes.values()),
        "edges": formatted_edges,
        "is_benign": False,
    }


@app.get("/api/graph/expand/{node_id}")
@app.get("/graph/expand/{node_id}")
def expand_node(node_id: str):
    g = graph()
    res_out = g.query(
        """
        MATCH (a {id: $id})-[r]->(b)
        RETURN a.id, type(r), b.id, labels(b)[0], b.name, coalesce(b.status, 'ACTIVE'), properties(b), coalesce(r.exploit, 0.5)
        LIMIT 15
        """,
        {"id": node_id}
    ).result_set
    res_in = g.query(
        """
        MATCH (b)-[r]->(a {id: $id})
        RETURN b.id, type(r), a.id, labels(b)[0], b.name, coalesce(b.status, 'ACTIVE'), properties(b), coalesce(r.exploit, 0.5)
        LIMIT 15
        """,
        {"id": node_id}
    ).result_set

    nodes = {}
    edges = set()
    for row in res_out:
        src, rel, tgt, label, name, status, props, weight = row
        if tgt not in nodes:
            nodes[tgt] = {
                "id": tgt,
                "label": label,
                "name": name or tgt,
                "status": status,
                "is_path_node": False,
                "properties": dict(props or {}),
            }
        edges.add((src, tgt, rel, float(weight)))

    for row in res_in:
        src, rel, tgt, label, name, status, props, weight = row
        if src not in nodes:
            nodes[src] = {
                "id": src,
                "label": label,
                "name": name or src,
                "status": status,
                "is_path_node": False,
                "properties": dict(props or {}),
            }
        edges.add((src, tgt, rel, float(weight)))

    return {
        "ok": True,
        "node_id": node_id,
        "nodes": list(nodes.values()),
        "edges": [{"source": s, "target": t, "type": r, "weight": w, "is_path": False} for s, t, r, w in sorted(edges)],
    }


UI_DIR = Path(__file__).resolve().parent.parent / "ui"


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def serve_ui():
    index_path = UI_DIR / "index.html"
    if not index_path.exists():
        index_path = Path(__file__).resolve().parent.parent / "public" / "index.html"
    content = index_path.read_text(encoding="utf-8")
    response = HTMLResponse(content=content)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if UI_DIR.exists():
    app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

