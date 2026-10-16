import time
import uuid
from engine import impact, paths, risk
from engine.db import MAIN, client

IP_FACTOR = 0.6
REVOKE_FACTOR = 0.7


def _mark_node(graph, label, target, status, by, timestamp):
    query = (
        f"MATCH (n:{label} {{id:$target}}) "
        "SET n.status=$status, n.blocked_by=$by, n.blocked_at=$timestamp"
    )
    graph.query(query, {"target": target, "status": status, "by": by, "timestamp": timestamp})


def _scale_edges(graph, entity_id, factor, by, relationship=None):
    relationship_pattern = f"[r:{relationship}]" if relationship else "[r]"
    query = (
        f"MATCH (e {{id:$entity}})-{relationship_pattern}->() "
        "WHERE r.exploit_orig IS NULL "
        "SET r.exploit_orig=r.exploit, r.exploit=r.exploit*$factor, r.scaled_by=$by"
    )
    graph.query(query, {"entity": entity_id, "factor": factor, "by": by})


def apply_action(graph, action, target, subject, by):
    timestamp = int(time.time())
    change = {"action": action, "target": target, "subject": subject, "by": by, "at": timestamp}
    if action == "isolate_device":
        _mark_node(graph, "Device", target, "ISOLATED", by, timestamp)
    elif action == "disable_account":
        _mark_node(graph, "ServiceAccount", target, "BLOCKED", by, timestamp)
    elif action == "revoke_credentials":
        graph.query(
            "MATCH (u {id:$target})-[r:HAS_ACCESS_TO]->() "
            "SET r.status='BLOCKED', r.blocked_by=$by, r.blocked_at=$timestamp",
            {"target": target, "by": by, "timestamp": timestamp},
        )
        _scale_edges(graph, target, REVOKE_FACTOR, by, "OWNS")
    elif action == "block_ip":
        _mark_node(graph, "IPAddress", target, "BLOCKED", by, timestamp)
        _scale_edges(graph, subject, IP_FACTOR, by)
    elif action != "monitor_only":
        raise ValueError(f"Unsupported containment action: {action}")
    change["modified"] = action != "monitor_only"
    return change


def restore(graph, by):
    graph.query(
        "MATCH (n) WHERE n.blocked_by=$by "
        "SET n.status='ACTIVE' REMOVE n.blocked_by, n.blocked_at",
        {"by": by},
    )
    graph.query(
        "MATCH ()-[r]->() WHERE r.blocked_by=$by "
        "SET r.status='ACTIVE' REMOVE r.blocked_by, r.blocked_at",
        {"by": by},
    )
    graph.query(
        "MATCH ()-[r]->() WHERE r.scaled_by=$by "
        "SET r.exploit=r.exploit_orig REMOVE r.exploit_orig, r.scaled_by",
        {"by": by},
    )


def candidates(graph, subject, base_paths):
    reachable_ids = sorted({node_id for path in base_paths for node_id in path["ids"]} | {subject})
    candidates_list = [("monitor_only", None)]
    label_query = "MATCH (n:%s) WHERE n.id IN $ids RETURN n.id"
    for (device_id,) in graph.query(label_query % "Device", {"ids": reachable_ids}).result_set:
        candidates_list.append(("isolate_device", device_id))
    for (account_id,) in graph.query(label_query % "ServiceAccount", {"ids": reachable_ids}).result_set:
        candidates_list.append(("disable_account", account_id))
    person_rows = graph.query(
        "MATCH (n:Person {id:$id}) RETURN n.id", {"id": subject}
    ).result_set
    if person_rows:
        candidates_list.append(("revoke_credentials", subject))
    ip_rows = graph.query(
        "MATCH (i:IPAddress)-[:USED_BY]->(s {id:$id}) RETURN i.id", {"id": subject}
    ).result_set
    for (ip_id,) in ip_rows:
        candidates_list.append(("block_ip", ip_id))
    return candidates_list


def simulate(subject, alert_id):
    live_graph = client().select_graph(MAIN)
    base = paths.find_attack_paths(live_graph, subject)
    base_paths = base["paths"]
    base_risk = risk.calculate_risk(base_paths)
    base_keys = [tuple(path["ids"]) for path in base_paths]
    rows = []
    for action, target in candidates(live_graph, subject, base_paths):
        if action == "monitor_only":
            after_paths = base_paths
            residual = base_risk
        else:
            simulation_name = "nexus_sim_" + uuid.uuid4().hex[:12]
            simulation_graph = live_graph.copy(simulation_name)
            try:
                apply_action(simulation_graph, action, target, subject, alert_id)
                after = paths.find_attack_paths(simulation_graph, subject)
                after_paths = after["paths"]
                residual = risk.calculate_risk(after_paths)
            finally:
                simulation_graph.delete()
        after_keys = {tuple(path["ids"]) for path in after_paths}
        surviving = [index for index, key in enumerate(base_keys) if key in after_keys]
        impact_result = impact.action_impact(live_graph, action, target)
        rows.append(
            {
                "action": action,
                "target": target,
                "residual_risk": residual["score"],
                "residual_label": residual["label"],
                "paths_before": len(base_paths),
                "paths_after": len(after_paths),
                "paths_broken": len(base_paths) - len(after_paths),
                "surviving_paths": surviving,
                "impact": impact_result["impact"],
                "impact_label": impact_result["label"],
                "impact_detail": impact_result,
                "needs_approval": impact_result["label"] in ("HIGH", "CRITICAL"),
            }
        )
    return {
        "subject": subject,
        "alert_id": alert_id,
        "initial": base_risk,
        "base_paths": [{"ids": path["ids"], "types": path["types"]} for path in base_paths],
        "matrix": rows,
        "cypher": base["cypher"],
    }
