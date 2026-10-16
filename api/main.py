import os

from fastapi import FastAPI, HTTPException
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


@app.get("/api/alerts")
def alerts():
    rows = graph().query(
        "MATCH (a:Alert) RETURN a.id, a.type, a.raw_text ORDER BY a.id"
    ).result_set
    return [{"id": row[0], "type": row[1], "raw_text": row[2]} for row in rows]


@app.post("/api/reset")
def reset_demo():
    count = rebuild_demo_graph()
    store.clear()
    return {"ok": True, "nodes": count, "message": "Synthetic demo graph restored."}


@app.post("/api/investigate")
def investigate(request: InvestigateReq):
    rows = graph().query(
        "MATCH (a:Alert {id:$id}) RETURN a.raw_text", {"id": request.alert_id}
    ).result_set
    if not rows:
        raise HTTPException(404, "unknown alert")
    mock = request.mode == "mock" or os.getenv("MOCK_LLM") == "1" or not os.getenv("ANTHROPIC_API_KEY")
    runner = loop.run_scripted if mock else loop.run_llm
    return runner(request.alert_id, rows[0][0], request.autonomous)


@app.post("/api/contain")
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
def rollback(request: ActReq):
    return execute.rollback(request.investigation_id)


@app.get("/api/investigations/{investigation_id}")
def investigation(investigation_id: str):
    record = store.get(investigation_id)
    if not record:
        raise HTTPException(404, "unknown investigation")
    return {
        "mode": "scripted",
        "trace": [],
        "summary": "Investigation state refreshed.",
        "investigation_id": investigation_id,
        "initial": record["initial"],
        "matrix": record["matrix"],
        "recommendation": record["recommendation"],
        "executed": record.get("executed"),
    }


@app.get("/api/graph/{investigation_id}")
def subgraph(investigation_id: str):
    record = store.get(investigation_id)
    if not record:
        raise HTTPException(404, "unknown investigation")
    ids = sorted({node_id for path in record["base_paths"] for node_id in path["ids"]})
    query = """MATCH (n) WHERE n.id IN $ids
RETURN n.id, labels(n)[0], n.name, coalesce(n.status, 'ACTIVE')"""
    rows = graph().query(query, {"ids": ids}).result_set
    edges = set()
    for path in record["base_paths"]:
        for index, relationship in enumerate(path["types"]):
            edges.add((path["ids"][index], path["ids"][index + 1], relationship))
    return {
        "nodes": [{"id": row[0], "label": row[1], "name": row[2], "status": row[3]} for row in rows],
        "edges": [{"source": source, "target": target, "type": kind} for source, target, kind in sorted(edges)],
    }


app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
