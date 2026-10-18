import json
import os
import time

from engine import store, tools
from engine.db import graph

MODEL = os.getenv("NEXUS_MODEL", "claude-sonnet-5-5")
MAX_STEPS = 12
SYSTEM = """You are NEXUS, a security operations agent. All company data is synthetic.
Investigate one alert using graph tools. Resolve entities, trace multi-hop paths,
calculate deterministic risk, inspect choke points, and simulate containment.
Choose only an action from that simulation and prefer its policy recommendation.
Never invent numbers; cite entity IDs. State missing evidence. Describe this as risk
analysis, not attacker prediction. The LLM orchestrates; deterministic tools compute
the evidence and enforce safety. Never claim synthetic/mock mode is AI reasoning.
"""


def summarize(name, out):
    if "error" in out:
        return "ERROR " + str(out["error"])
    if name == "find_attack_paths":
        return f"{out['count']} attack paths found"
    if name == "calculate_risk":
        return f"risk {out['score']} {out['label']}"
    if name == "simulate_containment":
        rec = out["recommendation"]
        return f"{len(out['matrix'])} actions simulated; recommends {rec['action']} {rec['target'] or ''}".strip()
    if name == "execute_containment" and out.get("ok"):
        return f"risk {out['before']} -> {out['after']}, verified={out['verified']}"
    if name == "execute_containment":
        return "blocked: " + str(out.get("error"))
    return json.dumps(out, default=str)[:240]


def run_tool(trace, name, args, forced=None):
    started = time.time()
    output = forced if forced is not None else tools.call(name, args)
    trace.append({
        "step": len(trace) + 1, "tool": name, "args": args,
        "cypher": output.get("cypher"), "summary": summarize(name, output),
        "ms": round((time.time() - started) * 1000),
    })
    return output


def finish(trace, summary, mode, investigation_id):
    record = store.get(investigation_id) if investigation_id else None
    return {
        "mode": mode, "trace": trace, "summary": summary,
        "investigation_id": investigation_id,
        "initial": record["initial"] if record else None,
        "matrix": record["matrix"] if record else None,
        "recommendation": record["recommendation"] if record else None,
        "evidence_paths": record["base_paths"][:3] if record else [],
        "evidence_path_count": len(record["base_paths"]) if record else 0,
        "executed": record["executed"] if record else None,
        "falkordb_memory": record.get("falkordb_memory") if record else None,
    }


def explain(record):
    initial, pick = record["initial"], record["recommendation"]
    lines = [
        f"Decision: {pick['action']} {pick['target'] or ''} ({pick['why']})".strip(),
        f"Evidence: initial risk {initial['score']} {initial['label']} from {len(record['base_paths'])} attack paths.",
    ]
    if record.get("falkordb_memory"):
        mem = record["falkordb_memory"]
        lines.append(f"FalkorDB Persistent Memory: Prior incident {mem['incident_id']} on {mem['prior_target']} under {mem['prior_alert']} retrieved.")
    lines.append("Alternatives considered:")
    for row in record["matrix"]:
        dominated = f" [dominated by {row['dominated_by']}]" if row.get("dominated_by") else ""
        reason = f" - Reason: {row['reason']}" if row.get("reason") else ""
        lines.append(f" - {row['action']} {row['target'] or ''}: residual risk {row['residual_risk']}, impact {row['impact_label']} ({row['impact']}){dominated}{reason}")
    executed = record.get("executed")
    if executed:
        lines.append(f"Verification: risk {executed['before']} -> {executed['after']}, matches simulation: {executed['verified']}")
    elif pick["requires_approval"]:
        lines.append("Human approval is required before this action runs.")
    else:
        lines.append("Not executed yet. A human may press CONTAIN to apply the recommended action.")
    return "\n".join(lines)


def run_scripted(alert_id, alert_text="", autonomous=False):
    """Deterministic mock path; exercises real tools but does not use an LLM."""
    del alert_text
    trace = []
    rows = graph().query(
        "MATCH (a:Alert {id:$id})-[:ABOUT]->(e) RETURN e.id", {"id": alert_id}
    ).result_set
    if not rows:
        raise ValueError(f"unknown alert: {alert_id}")
    subject = rows[0][0]
    run_tool(trace, "resolve_entities", {"queries": [subject]})
    run_tool(trace, "find_attack_paths", {"start_id": subject})
    run_tool(trace, "calculate_risk", {"start_id": subject})
    run_tool(trace, "find_choke_points", {"start_id": subject})
    simulation = run_tool(trace, "simulate_containment", {"start_id": subject, "alert_id": alert_id})
    investigation_id = simulation["investigation_id"]
    recommendation = simulation["recommendation"]
    if autonomous and not recommendation["requires_approval"]:
        run_tool(trace, "execute_containment", {
            "investigation_id": investigation_id, "action": recommendation["action"],
            "target": recommendation["target"], "approved": False,
        })
        run_tool(trace, "calculate_risk", {"start_id": subject})
    return finish(trace, explain(store.get(investigation_id)), "scripted", investigation_id)


def run_llm(alert_id, alert_text, autonomous=False):
    import anthropic

    client = anthropic.Anthropic()
    trace, investigation_id, final = [], None, ""
    messages = [{"role": "user", "content": f"Alert id: {alert_id}. Autonomous execution allowed: {autonomous}. Raw alert: {alert_text}"}]
    for _ in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL, max_tokens=1500, system=SYSTEM,
            tools=tools.TOOL_DEFS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            final = " ".join(block.text for block in response.content if block.type == "text")
            break
        results = []
        for block in calls:
            args = dict(block.input)
            forced = None
            if block.name == "execute_containment":
                args["approved"] = False
                if not autonomous:
                    forced = {"ok": False, "error": "EXECUTION_DISABLED: a human must press CONTAIN"}
            output = run_tool(trace, block.name, args, forced)
            investigation_id = output.get("investigation_id", investigation_id)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output, default=str)})
        messages.append({"role": "user", "content": results})
    return finish(trace, final, "llm", investigation_id)
