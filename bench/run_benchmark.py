import os
import random

from agent import loop
from engine import execute, tools
from engine.db import graph
from seed.generate import node

N = int(os.getenv("BENCH_N", "30"))
EXTRA = ["SVC-ACCT-09", "LAPTOP-042", "DEV-SERVER-03", "DEV-SERVER-07", "JUMPBOX-01", "PROD-API", "BILLING-SVC"]


def make_alerts(count):
    current = graph()
    random.seed(7)
    fixed = [("ALT-1042", "U-ALEX"), ("ALT-2071", "SVC-ACCT-17"), ("ALT-3310", "U-PRIYA")]
    alerts = []
    for alert_id, subject in fixed:
        node(current, "Alert", alert_id, type="benchmark", raw_text=f"Synthetic benchmark alert for {subject}")
        current.query("MATCH (a:Alert {id:$alert}), (e {id:$entity}) MERGE (a)-[:ABOUT]->(e)", {"alert": alert_id, "entity": subject})
        alerts.append((alert_id, subject))
    for index in range(7):
        subject = EXTRA[index]
        alert_id = f"ALT-BENCH-{index:02d}"
        node(current, "Alert", alert_id, type="benchmark", raw_text=f"Synthetic benchmark alert for {subject}")
        current.query("MATCH (a:Alert {id:$alert}), (e {id:$entity}) MERGE (a)-[:ABOUT]->(e)", {"alert": alert_id, "entity": subject})
        alerts.append((alert_id, subject))
    subjects = [row[0] for row in current.query("MATCH (n) WHERE n:Person OR n:ServiceAccount RETURN n.id").result_set]
    for index in range(max(0, count - len(alerts))):
        subject = random.choice(subjects)
        alert_id = f"ALT-RANDOM-{index:03d}"
        node(current, "Alert", alert_id, type="benchmark", raw_text=f"Synthetic benchmark alert for {subject}")
        current.query("MATCH (a:Alert {id:$alert}), (e {id:$entity}) MERGE (a)-[:ABOUT]->(e)", {"alert": alert_id, "entity": subject})
        alerts.append((alert_id, subject))
    return alerts[:count]


def last_execute(trace):
    for step in reversed(trace):
        if step["tool"] == "execute_containment" and step["summary"].startswith("risk "):
            return step["args"].get("action"), step["args"].get("target")
    return None


def main():
    use_llm = bool(os.getenv("ANTHROPIC_API_KEY")) and os.getenv("MOCK_LLM", "0") != "1"
    rows = []
    for alert_id, subject in make_alerts(N):
        simulation = tools.simulate_containment(subject, alert_id)
        optimum = simulation["recommendation"]
        result = execute.execute(simulation["investigation_id"], optimum["action"], optimum["target"], approved=True)
        execute.rollback(simulation["investigation_id"])
        row = {
            "alert": alert_id, "subject": subject,
            "optimum": f"{optimum['action']} {optimum['target'] or ''}".strip(),
            "verified": result.get("verified"), "match": None, "agent": "not run",
        }
        if use_llm:
            agent_result = loop.run_llm(alert_id, graph().query("MATCH (a:Alert {id:$id}) RETURN a.raw_text", {"id": alert_id}).result_set[0][0], autonomous=True)
            chosen = last_execute(agent_result["trace"])
            if agent_result.get("executed"):
                execute.rollback(agent_result["investigation_id"])
            row["match"] = chosen == (optimum["action"], optimum["target"])
            row["agent"] = f"{chosen[0]} {chosen[1] or ''}".strip() if chosen else "no action"
        rows.append(row)
    verification = [row["verified"] for row in rows if row["verified"] is not None]
    lines = [f"# NEXUS benchmark (synthetic graph, {len(rows)} alerts)", "", f"Verification: {sum(verification)} of {len(verification)} executed actions matched the simulated residual risk."]
    if use_llm:
        lines.append(f"Agent agreement with engine optimum: {sum(bool(row['match']) for row in rows)} of {len(rows)}.")
    lines += ["", "| Alert | Subject | Engine optimum | Agent | Match |", "|---|---|---|---|---|"]
    lines += [f"| {row['alert']} | {row['subject']} | {row['optimum']} | {row['agent']} | {row['match']} |" for row in rows]
    with open("bench/results.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines[:4]))


if __name__ == "__main__":
    main()
