MAX_DEPTH = 7
MAX_PATHS = 200
MIN_CRITICALITY = 7


def _query(depth):
    return f"""
MATCH p=(s {{id:$start}})-
[:OWNS|LOGS_INTO|HAS_ACCESS_TO|HOSTS_CREDENTIAL|AUTHENTICATES_TO|READS*1..{depth}]->
(d:DataStore)
WHERE d.criticality >= $min_criticality
AND all(n IN nodes(p) WHERE coalesce(n.status,'ACTIVE') = 'ACTIVE')
AND all(r IN relationships(p) WHERE coalesce(r.status,'ACTIVE') = 'ACTIVE')
RETURN [n IN nodes(p) | n.id] AS ids,
[r IN relationships(p) | type(r)] AS types,
[r IN relationships(p) | r.exploit] AS exploit_weights,
[n IN nodes(p) | coalesce(n.privilege, -1.0)] AS privileges,
d.id AS target, d.criticality AS criticality
LIMIT $limit
""".strip()


def find_attack_paths(graph, start_id, max_depth=MAX_DEPTH, min_criticality=MIN_CRITICALITY, limit=MAX_PATHS):
    if not isinstance(max_depth, int) or not 1 <= max_depth <= MAX_DEPTH:
        raise ValueError(f"max_depth must be an integer from 1 to {MAX_DEPTH}")
    limit = min(MAX_PATHS, max(1, int(limit)))
    query = _query(max_depth)
    rows = graph.query(
        query,
        {"start": start_id, "min_criticality": min_criticality, "limit": limit},
    ).result_set
    paths = []
    for ids, types, weights, privileges, target, criticality in rows:
        if len(set(ids)) != len(ids):
            continue
        exploitability = 1.0
        for weight in weights:
            exploitability *= weight if weight is not None else 0.5
        paths.append(
            {
                "ids": ids,
                "types": types,
                "exploit": round(exploitability, 4),
                "priv": privileges,
                "target": target,
                "crit": criticality,
                "hops": len(types),
            }
        )
    paths.sort(key=lambda path: (path["target"], tuple(path["ids"])))
    return {"paths": paths[:MAX_PATHS], "cypher": query}
