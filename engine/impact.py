CAP = 60.0
WEIGHT = {1: 10, 2: 5, 3: 1}
PERSON_WEIGHT = 0.5


def label(score):
    if score < 20:
        return "LOW"
    if score < 45:
        return "MEDIUM"
    if score < 70:
        return "HIGH"
    return "CRITICAL"


def affected_services(graph, account_id):
    direct_query = "MATCH (a {id:$id})-[:AUTHENTICATES_TO]->(s:Service) RETURN s.id"
    direct = [row[0] for row in graph.query(direct_query, {"id": account_id}).result_set]
    if not direct:
        return []
    dependent_query = (
        "MATCH (d:Service)-[:DEPENDS_ON*1..2]->(s:Service) "
        "WHERE s.id IN $ids RETURN DISTINCT d.id"
    )
    dependents = [
        row[0] for row in graph.query(dependent_query, {"ids": direct}).result_set
    ]
    return sorted(set(direct + dependents))


def action_impact(graph, action, target):
    if action == "monitor_only":
        return {"impact": 0, "label": "LOW", "services": [], "users": 0}
    if action != "disable_account":
        score = min(100, round(PERSON_WEIGHT * 100 / CAP))
        return {"impact": score, "label": label(score), "services": [], "users": 1}
    services = affected_services(graph, target)
    tiers_query = "MATCH (s:Service) WHERE s.id IN $ids RETURN s.tier"
    tiers = graph.query(tiers_query, {"ids": services}).result_set if services else []
    service_raw = sum(WEIGHT.get(row[0], 1) for row in tiers)
    if services:
        users_query = (
            "MATCH (u:Person)-[:USES]->(s:Service) WHERE s.id IN $ids "
            "RETURN count(DISTINCT u)"
        )
        users = graph.query(users_query, {"ids": services}).result_set[0][0]
    else:
        users = 0
    raw = service_raw + PERSON_WEIGHT * users
    score = min(100, round(raw * 100 / CAP))
    return {"impact": score, "label": label(score), "services": services, "users": users}
