from engine import execute, impact, pareto, paths, risk, simulate, store
from engine.db import graph


def resolve_entities(queries):
    current_graph = graph()
    query = (
        "MATCH (n) WHERE n.id=$query OR "
        "toLower(n.name) CONTAINS toLower($query) "
        "RETURN n.id, labels(n)[0], n.name LIMIT 5"
    )
    found, missing = [], []
    for term in queries:
        rows = current_graph.query(query, {"query": term}).result_set
        if rows:
            found.extend({"id": row[0], "label": row[1], "name": row[2]} for row in rows)
        else:
            missing.append(term)
    return {"entities": found, "unmatched": missing, "cypher": query}


def find_attack_paths(start_id, max_depth=7):
    result = paths.find_attack_paths(graph(), start_id, max_depth=max_depth)
    return {"count": len(result["paths"]), "paths": result["paths"], "cypher": result["cypher"]}


def blast_radius(start_id):
    query = """
MATCH p=(s {id:$id})-[:OWNS|LOGS_INTO|HAS_ACCESS_TO|HOSTS_CREDENTIAL|AUTHENTICATES_TO|READS*1..7]->(n)
WHERE all(x IN nodes(p) WHERE coalesce(x.status,'ACTIVE')='ACTIVE')
AND all(r IN relationships(p) WHERE coalesce(r.status,'ACTIVE')='ACTIVE')
RETURN labels(n)[0] AS label, count(DISTINCT n) AS count
""".strip()
    rows = graph().query(query, {"id": start_id}).result_set
    return {"reachable_by_label": {row[0]: row[1] for row in rows}, "cypher": query}


def calculate_risk(start_id):
    result = paths.find_attack_paths(graph(), start_id)
    output = risk.calculate_risk(result["paths"])
    output["cypher"] = result["cypher"]
    output["formula"] = "risk = round(100 * (1 - exp(-sum(criticality * privilege * reach_probability) / K))); K=4"
    return output


def find_choke_points(start_id, top_n=5):
    if not 1 <= int(top_n) <= 20:
        raise ValueError("top_n must be between 1 and 20")
    result = paths.find_attack_paths(graph(), start_id)
    path_list = result["paths"]
    if not path_list:
        return {"metric": "path_coverage", "nodes": [], "cypher": result["cypher"]}
    counts = {}
    critical_counts = {}
    for path in path_list:
        for node_id in set(path["ids"][1:-1]):
            counts[node_id] = counts.get(node_id, 0) + 1
            critical_counts[node_id] = critical_counts.get(node_id, 0) + 1
    ranked_ids = sorted(counts, key=lambda node_id: (-counts[node_id], node_id))[: int(top_n)]
    property_query = (
        "MATCH (n) WHERE n.id IN $ids "
        "RETURN n.id, labels(n)[0], n.token_age_days"
    )
    rows = graph().query(property_query, {"ids": ranked_ids}).result_set
    properties = {row[0]: (row[1], row[2]) for row in rows}
    nodes = [
        {
            "id": node_id,
            "label": properties.get(node_id, ("?", None))[0],
            "token_age_days": properties.get(node_id, ("?", None))[1],
            "paths_through": counts[node_id],
            "critical_paths_through": critical_counts[node_id],
            "path_coverage": round(counts[node_id] / len(path_list), 2),
        }
        for node_id in ranked_ids
    ]
    return {
        "metric": "path_coverage (share of attack paths passing through the node)",
        "nodes": nodes,
        "cypher": result["cypher"] + "\n" + property_query,
    }


def query_incident_memory(start_id):
    current_graph = graph()
    query = """
    MATCH (inc:Incident)
    WHERE inc.status = 'CONTAINED'
    OPTIONAL MATCH (inc)-[:CONTAINED_ENTITY]->(target)
    RETURN inc.id AS incident_id, inc.alert_id AS alert_id, inc.action AS action,
           coalesce(target.id, inc.target) AS target, inc.timestamp AS timestamp,
           inc.status AS status
    ORDER BY inc.timestamp DESC
    LIMIT 5
    """
    try:
        rows = current_graph.query(query).result_set
    except Exception:
        rows = []
    history = [
        {
            "incident_id": r[0],
            "alert_id": r[1],
            "action": r[2],
            "target": r[3],
            "timestamp": r[4],
            "status": r[5],
        }
        for r in rows
    ]

    # Check if this subject or owned/connected devices have active containment history in FalkorDB
    related_query = """
    MATCH (inc:Incident)
    WHERE inc.status = 'CONTAINED'
    MATCH (s {id: $id})
    MATCH (inc)-[:CONTAINED_ENTITY]->(t)
    WHERE t.id = s.id OR inc.target = s.id OR (s)-[:OWNS|LOGS_INTO|AUTHENTICATES_TO*1..2]-(t)
    RETURN inc.id, inc.alert_id, inc.action, coalesce(t.id, inc.target)
    LIMIT 1
    """
    escalation = None
    try:
        matched = current_graph.query(related_query, {"id": start_id}).result_set
        if matched and matched[0][0]:
            inc_id, alert_id, action, target = matched[0]
            escalation = {
                "has_memory": True,
                "incident_id": inc_id,
                "prior_alert": alert_id,
                "prior_action": action,
                "prior_target": target,
                "reason": f"Repeat incident detected in FalkorDB: entity {target} was previously contained under {alert_id} ({action}).",
            }
    except Exception:
        pass

    return {
        "memory_records": history,
        "escalation": escalation,
        "cypher": query.strip(),
    }


def simulate_containment(start_id, alert_id):
    memory_info = query_incident_memory(start_id)
    escalation = memory_info.get("escalation")
    simulation = simulate.simulate(start_id, alert_id)
    decision = pareto.recommend(simulation["initial"]["score"], simulation["matrix"], prior_incident=escalation)
    investigation_id = store.new_id()
    selected = decision["row"]
    record = dict(simulation)
    record["investigation_id"] = investigation_id
    record["recommendation"] = {
        "action": selected["action"],
        "target": selected["target"],
        "requires_approval": decision["requires_approval"],
        "why": decision["why"],
        "memory_escalated": decision.get("memory_escalated", False),
    }
    record["falkordb_memory"] = escalation
    record["executed"] = None
    record["change_log"] = []
    store.save(investigation_id, record)
    return {
        "investigation_id": investigation_id,
        "initial_risk": simulation["initial"]["score"],
        "matrix": simulation["matrix"],
        "recommendation": record["recommendation"],
        "falkordb_memory": escalation,
        "cypher": simulation["cypher"],
    }


def execute_containment(investigation_id, action, target=None, approved=False):
    return execute.execute(investigation_id, action, target, approved)


def rollback(investigation_id):
    return execute.rollback(investigation_id)


FUNCS = {
    "resolve_entities": resolve_entities,
    "find_attack_paths": find_attack_paths,
    "blast_radius": blast_radius,
    "calculate_risk": calculate_risk,
    "find_choke_points": find_choke_points,
    "query_incident_memory": query_incident_memory,
    "simulate_containment": simulate_containment,
    "execute_containment": execute_containment,
    "rollback": rollback,
}

TOOL_DEFS = [
    {"name": "resolve_entities", "description": "Resolve synthetic entity names or IDs.", "input_schema": {"type": "object", "properties": {"queries": {"type": "array", "items": {"type": "string"}}}, "required": ["queries"]}},
    {"name": "find_attack_paths", "description": "Find multi-hop attack paths from an entity to critical data stores.", "input_schema": {"type": "object", "properties": {"start_id": {"type": "string"}, "max_depth": {"type": "integer"}}, "required": ["start_id"]}},
    {"name": "blast_radius", "description": "Count reachable entities by type.", "input_schema": {"type": "object", "properties": {"start_id": {"type": "string"}}, "required": ["start_id"]}},
    {"name": "calculate_risk", "description": "Calculate deterministic graph-grounded risk.", "input_schema": {"type": "object", "properties": {"start_id": {"type": "string"}}, "required": ["start_id"]}},
    {"name": "find_choke_points", "description": "Rank nodes by attack-path coverage.", "input_schema": {"type": "object", "properties": {"start_id": {"type": "string"}, "top_n": {"type": "integer"}}, "required": ["start_id"]}},
    {"name": "query_incident_memory", "description": "Retrieve historical security incidents and containment records from FalkorDB graph memory.", "input_schema": {"type": "object", "properties": {"start_id": {"type": "string"}}, "required": ["start_id"]}},
    {"name": "simulate_containment", "description": "Simulate candidate containment actions on disposable graph copies.", "input_schema": {"type": "object", "properties": {"start_id": {"type": "string"}, "alert_id": {"type": "string"}}, "required": ["start_id", "alert_id"]}},
    {"name": "execute_containment", "description": "Execute only a previously simulated action, respecting human approval.", "input_schema": {"type": "object", "properties": {"investigation_id": {"type": "string"}, "action": {"type": "string"}, "target": {"type": ["string", "null"]}}, "required": ["investigation_id", "action"]}},
    {"name": "rollback", "description": "Restore graph status and edge weights changed by an investigation.", "input_schema": {"type": "object", "properties": {"investigation_id": {"type": "string"}}, "required": ["investigation_id"]}},
]


def call(name, args):
    if name not in FUNCS:
        return {"error": f"unknown tool {name}"}
    try:
        return FUNCS[name](**args)
    except TypeError as exc:
        return {"error": f"bad arguments: {exc}"}
    except Exception as exc:
        return {"error": f"tool failed: {exc}"}
