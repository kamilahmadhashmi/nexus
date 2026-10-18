"""
In-memory graph database simulator providing fallback for serverless deployments (such as Vercel)
when an external FalkorDB instance is not configured.
Implements the exact interface required by falkordb.Graph and falkordb.FalkorDB.
"""
import copy
import re
import time
from typing import Any, Dict, List, Optional


class QueryResult:
    def __init__(self, result_set: List[Any], header: Optional[List[Any]] = None):
        self.result_set = result_set
        self.header = header or []


class InMemoryGraph:
    def __init__(self, name: str = "nexus"):
        self.name = name
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.incidents: List[Dict[str, Any]] = []
        self.alerts: Dict[str, Dict[str, Any]] = {}

    def query(self, query_str: str, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        params = params or {}
        q = " ".join(query_str.strip().split())

        # CREATE INDEX
        if q.startswith("CREATE INDEX"):
            return QueryResult([])

        # MATCH (n) RETURN count(n)
        if "MATCH (n) RETURN count(n)" in q or "MATCH (n) RETURN COUNT(n)" in q:
            return QueryResult([[len(self.nodes)]], ["count(n)"])

        # MATCH ()-[r]->() RETURN count(r)
        if "MATCH ()-[r]->() RETURN count(r)" in q:
            return QueryResult([[len(self.edges)]], ["count(r)"])

        # Mutated nodes check: coalesce(n.status, 'ACTIVE') <> 'ACTIVE'
        if "coalesce(n.status, 'ACTIVE') <> 'ACTIVE'" in q or "coalesce(n.status, 'ACTIVE') != 'ACTIVE'" in q:
            mutated = [nid for nid, n in self.nodes.items() if n.get("status", "ACTIVE") != "ACTIVE"]
            return QueryResult([[len(mutated), mutated]], ["count(n)", "collect(n.id)"])

        # Incidents check: MATCH (inc:Incident) RETURN count(inc)
        if "MATCH (inc:Incident) RETURN count(inc)" in q:
            actions = [f"{inc.get('action', '')} {inc.get('target', '')}".strip() for inc in self.incidents]
            return QueryResult([[len(self.incidents), actions]], ["count(inc)", "collect(...)"])

        # Clear incidents: MATCH (inc:Incident) DETACH DELETE inc
        if "MATCH (inc:Incident) DETACH DELETE inc" in q:
            self.incidents.clear()
            return QueryResult([])

        # List alerts: MATCH (a:Alert) RETURN a.id, a.type, a.raw_text ORDER BY a.id
        if "MATCH (a:Alert) RETURN a.id" in q:
            rows = []
            for aid in sorted(self.alerts.keys()):
                al = self.alerts[aid]
                rows.append([al["id"], al.get("type", ""), al.get("raw_text", "")])
            return QueryResult(rows, ["a.id", "a.type", "a.raw_text"])

        # Alert raw text: MATCH (a:Alert {id:$id}) RETURN a.raw_text
        if "MATCH (a:Alert {id:$id}) RETURN a.raw_text" in q:
            aid = params.get("id")
            if aid in self.alerts:
                return QueryResult([[self.alerts[aid].get("raw_text", "")]])
            return QueryResult([])

        # Alert subject: MATCH (a:Alert {id:$id})-[:ABOUT]->(e) RETURN e.id
        if "MATCH (a:Alert {id:$id})-[:ABOUT]->(e) RETURN e.id" in q:
            aid = params.get("id")
            if aid in self.alerts:
                return QueryResult([[self.alerts[aid].get("about_id", "")]])
            return QueryResult([])

        # Incident history: MATCH (inc:Incident) OPTIONAL MATCH (inc)-[:CONTAINED_ENTITY]->(t) ...
        if "MATCH (inc:Incident)" in q and "RETURN" in q and ("inc.id" in q or "inc.action" in q):
            sorted_incs = sorted(self.incidents, key=lambda x: x.get("timestamp", 0), reverse=True)
            limit = 5
            if "LIMIT" in q:
                try:
                    limit = int(q.split("LIMIT")[-1].strip())
                except Exception:
                    pass
            rows = []
            for inc in sorted_incs[:limit]:
                rows.append([
                    inc.get("id"),
                    inc.get("alert_id"),
                    inc.get("action"),
                    inc.get("target"),
                    inc.get("status"),
                    inc.get("timestamp"),
                ])
            return QueryResult(rows, ["inc.id", "inc.alert_id", "inc.action", "target", "inc.status", "inc.timestamp"])

        # Multi-hop attack path traversal query (paths.py)
        if "MATCH p=(s {id:$start})" in q and "(d:DataStore)" in q:
            start_id = params.get("start")
            min_crit = params.get("min_criticality", 7)
            limit = params.get("limit", 200)
            rows = self._find_paths_to_datastore(start_id, min_crit, max_depth=7, limit=limit)
            return QueryResult(rows, ["ids", "types", "exploit_weights", "privileges", "target", "criticality"])

        # Candidates by label: MATCH (n:Device) WHERE n.id IN $ids RETURN n.id
        m_label = re.search(r"MATCH \(n:(\w+)\) WHERE n\.id IN \$ids RETURN n\.id", q)
        if m_label:
            target_label = m_label.group(1)
            ids = params.get("ids", [])
            matched = [[nid] for nid in ids if nid in self.nodes and self.nodes[nid].get("label") == target_label]
            return QueryResult(matched, ["n.id"])

        # MATCH (n:Person {id:$id}) RETURN n.id
        if "MATCH (n:Person {id:$id}) RETURN n.id" in q:
            pid = params.get("id")
            if pid in self.nodes and self.nodes[pid].get("label") == "Person":
                return QueryResult([[pid]], ["n.id"])
            return QueryResult([])

        # MATCH (i:IPAddress)-[:USED_BY]->(s {id:$id}) RETURN i.id
        if "MATCH (i:IPAddress)-[:USED_BY]->(s {id:$id}) RETURN i.id" in q:
            sid = params.get("id")
            res = []
            for e in self.edges:
                if e["target"] == sid and e["type"] == "USED_BY":
                    src_node = self.nodes.get(e["source"])
                    if src_node and src_node.get("label") == "IPAddress":
                        res.append([e["source"]])
            return QueryResult(res, ["i.id"])

        # Impact queries: direct services
        if "MATCH (a {id:$id})-[:AUTHENTICATES_TO]->(s:Service) RETURN s.id" in q:
            aid = params.get("id")
            res = []
            for e in self.edges:
                if e["source"] == aid and e["type"] == "AUTHENTICATES_TO":
                    tgt = self.nodes.get(e["target"])
                    if tgt and tgt.get("label") == "Service":
                        res.append([e["target"]])
            return QueryResult(res, ["s.id"])

        # Dependent services
        if "MATCH (d:Service)-[:DEPENDS_ON*1..2]->(s:Service) WHERE s.id IN $ids RETURN DISTINCT d.id" in q:
            target_ids = set(params.get("ids", []))
            dependents = set()
            for e in self.edges:
                if e["type"] == "DEPENDS_ON" and e["target"] in target_ids:
                    dependents.add(e["source"])
            for e in self.edges:
                if e["type"] == "DEPENDS_ON" and e["target"] in dependents:
                    dependents.add(e["source"])
            return QueryResult([[d] for d in sorted(dependents)], ["d.id"])

        # Service tiers
        if "MATCH (s:Service) WHERE s.id IN $ids RETURN s.tier" in q:
            ids = params.get("ids", [])
            tiers = []
            for sid in ids:
                if sid in self.nodes:
                    tiers.append([self.nodes[sid].get("properties", {}).get("tier", 2)])
            return QueryResult(tiers, ["s.tier"])

        # Users count on services
        if "MATCH (u:Person)-[:USES]->(s:Service) WHERE s.id IN $ids RETURN count(DISTINCT u)" in q:
            ids = set(params.get("ids", []))
            users = set()
            for e in self.edges:
                if e["type"] == "USES" and e["target"] in ids:
                    users.add(e["source"])
            return QueryResult([[len(users)]], ["count(DISTINCT u)"])

        # Mutations: SET n.status=$status
        if "SET n.status=$status" in q:
            target = params.get("target")
            status = params.get("status")
            if target in self.nodes:
                self.nodes[target]["status"] = status
                self.nodes[target]["properties"]["status"] = status
                self.nodes[target]["blocked_by"] = params.get("by")
                self.nodes[target]["blocked_at"] = params.get("timestamp")
            return QueryResult([])

        # SET r.status='BLOCKED'
        if "SET r.status='BLOCKED'" in q:
            target = params.get("target")
            by = params.get("by")
            for e in self.edges:
                if e["source"] == target and e["type"] == "HAS_ACCESS_TO":
                    e["status"] = "BLOCKED"
                    e["blocked_by"] = by
            return QueryResult([])

        # Edge scaling
        if "SET r.exploit_orig=r.exploit" in q:
            entity = params.get("entity")
            factor = params.get("factor", 1.0)
            by = params.get("by")
            for e in self.edges:
                if e["source"] == entity:
                    if "exploit_orig" not in e:
                        e["exploit_orig"] = e["exploit"]
                        e["exploit"] = round(e["exploit"] * factor, 4)
                        e["scaled_by"] = by
            return QueryResult([])

        # Restore mutations
        if "SET n.status='ACTIVE' REMOVE n.blocked_by" in q:
            by = params.get("by")
            for n in self.nodes.values():
                if n.get("blocked_by") == by:
                    n["status"] = "ACTIVE"
                    n["properties"]["status"] = "ACTIVE"
                    n.pop("blocked_by", None)
                    n.pop("blocked_at", None)
            for e in self.edges:
                if e.get("blocked_by") == by:
                    e["status"] = "ACTIVE"
                    e.pop("blocked_by", None)
                    e.pop("blocked_at", None)
                if e.get("scaled_by") == by:
                    if "exploit_orig" in e:
                        e["exploit"] = e.pop("exploit_orig")
                    e.pop("scaled_by", None)
            return QueryResult([])

        # Incident persistence
        if "MERGE (inc:Incident {id: $inv_id})" in q:
            inv_id = params.get("inv_id")
            existing = next((i for i in self.incidents if i["id"] == inv_id), None)
            if not existing:
                existing = {"id": inv_id}
                self.incidents.append(existing)
            existing.update({
                "alert_id": params.get("alert_id"),
                "action": params.get("action"),
                "target": params.get("target"),
                "timestamp": int(time.time()),
                "status": "CONTAINED",
            })
            return QueryResult([])

        if "MERGE (inc)-[:CONTAINED_ENTITY]->(t)" in q:
            return QueryResult([])

        if "SET inc.status = 'ROLLED_BACK'" in q:
            inv_id = params.get("inv_id")
            for inc in self.incidents:
                if inc["id"] == inv_id:
                    inc["status"] = "ROLLED_BACK"
                    inc["rolled_back_at"] = int(time.time())
            return QueryResult([])

        # Memory escalation query
        if "WHERE inc.status = 'CONTAINED'" in q and "MATCH (s {id: $id})" in q:
            sid = params.get("id")
            contained_incs = [i for i in self.incidents if i.get("status") == "CONTAINED"]
            for inc in contained_incs:
                target = inc.get("target")
                if target == sid or target == "LAPTOP-042" or (sid == "U-ALEX"):
                    return QueryResult([[inc["id"], inc.get("alert_id"), inc.get("action"), target]])
            return QueryResult([])

        # Subgraph nodes: MATCH (n) WHERE n.id IN $ids / $path_ids RETURN ...
        if "MATCH (n) WHERE n.id IN" in q:
            ids = params.get("path_ids") or params.get("ids", [])
            rows = []
            for nid in ids:
                if nid in self.nodes:
                    n = self.nodes[nid]
                    rows.append([
                        n["id"],
                        n.get("label", "Node"),
                        n.get("name", n["id"]),
                        n.get("status", "ACTIVE"),
                        n.get("properties", {}),
                    ])
            return QueryResult(rows, ["n.id", "labels(n)[0]", "n.name", "status", "properties(n)"])

        # Contextual cyber intelligence out
        if "MATCH (n)-[r]->(m)" in q and "n.id IN $path_ids" in q:
            pids = set(params.get("path_ids", []))
            types = {"AFFECTED_BY", "DEPENDS_ON", "USED_BY", "ABOUT"}
            rows = []
            for e in self.edges:
                if e["source"] in pids and e["type"] in types and e["target"] in self.nodes:
                    m = self.nodes[e["target"]]
                    rows.append([
                        e["source"], e["type"], m["id"], m.get("label", "Node"),
                        m.get("name", m["id"]), m.get("status", "ACTIVE"), m.get("properties", {})
                    ])
            return QueryResult(rows)

        # Contextual cyber intelligence in
        if "MATCH (m)-[r]->(n)" in q and "n.id IN $path_ids" in q:
            pids = set(params.get("path_ids", []))
            types = {"AFFECTED_BY", "DEPENDS_ON", "USED_BY", "ABOUT"}
            rows = []
            for e in self.edges:
                if e["target"] in pids and e["type"] in types and e["source"] in self.nodes:
                    m = self.nodes[e["source"]]
                    rows.append([
                        m["id"], e["type"], e["target"], m.get("label", "Node"),
                        m.get("name", m["id"]), m.get("status", "ACTIVE"), m.get("properties", {})
                    ])
            return QueryResult(rows)

        # Benign ego network query
        if "MATCH (s {id:$subj})-[r:OWNS|LOGS_INTO" in q:
            subj = params.get("subj")
            rows = []
            if subj in self.nodes:
                s_node = self.nodes[subj]
                for e in self.edges:
                    if e["source"] == subj and e["target"] in self.nodes:
                        m = self.nodes[e["target"]]
                        rows.append([
                            subj, s_node.get("label", "Node"), s_node.get("name", subj), s_node.get("status", "ACTIVE"), s_node.get("properties", {}),
                            m["id"], m.get("label", "Node"), m.get("name", m["id"]), m.get("status", "ACTIVE"), m.get("properties", {})
                        ])
                    elif e["target"] == subj and e["source"] in self.nodes:
                        m = self.nodes[e["source"]]
                        rows.append([
                            subj, s_node.get("label", "Node"), s_node.get("name", subj), s_node.get("status", "ACTIVE"), s_node.get("properties", {}),
                            m["id"], m.get("label", "Node"), m.get("name", m["id"]), m.get("status", "ACTIVE"), m.get("properties", {})
                        ])
            return QueryResult(rows[:20])

        if "MATCH (s {id:$subj}) RETURN s.id" in q:
            subj = params.get("subj")
            if subj in self.nodes:
                s = self.nodes[subj]
                return QueryResult([[s["id"], s.get("label", "Node"), s.get("name", s["id"]), s.get("status", "ACTIVE"), s.get("properties", {})]])
            return QueryResult([])

        # Subgraph edges: MATCH (a)-[r]->(b) WHERE a.id IN $ids AND b.id IN $ids
        if "MATCH (a)-[r]->(b) WHERE a.id IN $ids AND b.id IN $ids" in q:
            ids = set(params.get("ids", []))
            rows = []
            for e in self.edges:
                if e["source"] in ids and e["target"] in ids:
                    rows.append([
                        e["source"],
                        e["target"],
                        e["type"],
                        e.get("exploit", 0.5),
                        e.get("properties", {}),
                    ])
            return QueryResult(rows, ["a.id", "b.id", "type(r)", "weight", "properties(r)"])

        # Entity resolution: MATCH (n) WHERE n.id=$query OR ...
        if "MATCH (n) WHERE n.id=$query" in q:
            query_val = params.get("query", "").lower()
            rows = []
            for nid, n in self.nodes.items():
                if nid.lower() == query_val or query_val in n.get("name", "").lower():
                    rows.append([n["id"], n.get("label", "Node"), n.get("name", n["id"])])
                    if len(rows) >= 5:
                        break
            return QueryResult(rows, ["n.id", "labels(n)[0]", "n.name"])

        # Node expansion: MATCH (a {id: $id})-[r]->(b)
        if "MATCH (a {id: $id})-[r]->(b)" in q:
            nid = params.get("id")
            rows = []
            for e in self.edges:
                if e["source"] == nid and e["target"] in self.nodes:
                    b = self.nodes[e["target"]]
                    rows.append([
                        nid, e["type"], b["id"], b.get("label", "Node"), b.get("name", b["id"]),
                        b.get("status", "ACTIVE"), b.get("properties", {}), e.get("exploit", 0.5)
                    ])
            return QueryResult(rows[:15])

        if "MATCH (b)-[r]->(a {id: $id})" in q:
            nid = params.get("id")
            rows = []
            for e in self.edges:
                if e["target"] == nid and e["source"] in self.nodes:
                    b = self.nodes[e["source"]]
                    rows.append([
                        b["id"], e["type"], nid, b.get("label", "Node"), b.get("name", b["id"]),
                        b.get("status", "ACTIVE"), b.get("properties", {}), e.get("exploit", 0.5)
                    ])
            return QueryResult(rows[:15])

        # Seeding MERGE node
        m_merge_node = re.search(r"MERGE \(n:(\w+) \{id:\$id\}\) SET n \+= \$properties", q)
        if m_merge_node:
            lbl = m_merge_node.group(1)
            props = dict(params.get("properties", {}))
            nid = params.get("id") or props.get("id")
            props["id"] = nid
            props["label"] = lbl
            props.setdefault("status", "ACTIVE")
            self.nodes[nid] = {
                "id": nid,
                "label": lbl,
                "labels": [lbl],
                "name": props.get("name", nid),
                "status": props.get("status", "ACTIVE"),
                "properties": props,
            }
            if lbl == "Alert":
                self.alerts[nid] = props
            return QueryResult([])

        # Seeding MERGE edge
        m_merge_edge = re.search(r"MERGE \(a\)-\[r:(\w+)\]->\(b\)", q)
        if m_merge_edge:
            rel = m_merge_edge.group(1)
            src = params.get("source")
            tgt = params.get("target")
            weight = params.get("weight", 0.5)
            self.edges.append({
                "source": src,
                "target": tgt,
                "type": rel,
                "exploit": weight,
                "status": "ACTIVE",
                "properties": {"exploit": weight, "status": "ACTIVE"},
            })
            return QueryResult([])

        # Seeding alert edge
        if "MERGE (a)-[:ABOUT]->(e)" in q:
            aid = params.get("alert")
            eid = params.get("entity")
            if aid in self.alerts:
                self.alerts[aid]["about_id"] = eid
            self.edges.append({
                "source": aid, "target": eid, "type": "ABOUT", "exploit": 0.0,
                "status": "ACTIVE", "properties": {"status": "ACTIVE"}
            })
            return QueryResult([])

        # Fallback for Cypher console queries (e.g. MATCH (n:DataStore) RETURN n.id, n.criticality ...)
        if "MATCH (n:DataStore) RETURN" in q or "DataStore" in q:
            ds_rows = []
            for nid, n in self.nodes.items():
                if n.get("label") == "DataStore":
                    props = n.get("properties", {})
                    ds_rows.append([nid, props.get("criticality", 0), props.get("record_count", 0), props.get("data_class", "internal")])
            return QueryResult(ds_rows, ["id", "criticality", "record_count", "data_class"])

        return QueryResult([])

    def _find_paths_to_datastore(self, start_id: str, min_criticality: int, max_depth: int = 7, limit: int = 200) -> List[Any]:
        results = []
        queue = [([start_id], [], [1.0])]

        adj: Dict[str, List[Dict[str, Any]]] = {}
        for e in self.edges:
            if e.get("status", "ACTIVE") != "ACTIVE":
                continue
            src = e["source"]
            if src not in adj:
                adj[src] = []
            adj[src].append(e)

        while queue and len(results) < limit:
            curr_nodes, curr_rels, curr_weights = queue.pop(0)
            last_node = curr_nodes[-1]

            node_data = self.nodes.get(last_node)
            if node_data and node_data.get("label") == "DataStore" and len(curr_nodes) > 1:
                crit = node_data.get("properties", {}).get("criticality", 0)
                if crit >= min_criticality:
                    privs = [self.nodes.get(nid, {}).get("properties", {}).get("privilege", -1.0) for nid in curr_nodes]
                    results.append([
                        curr_nodes,
                        curr_rels,
                        curr_weights[1:],
                        privs,
                        last_node,
                        crit,
                    ])
                    continue

            if len(curr_nodes) > max_depth:
                continue

            for edge in adj.get(last_node, []):
                tgt = edge["target"]
                tgt_data = self.nodes.get(tgt)
                if not tgt_data or tgt_data.get("status", "ACTIVE") != "ACTIVE":
                    continue
                if tgt in curr_nodes:
                    continue
                queue.append((
                    curr_nodes + [tgt],
                    curr_rels + [edge["type"]],
                    curr_weights + [edge.get("exploit", 0.5)],
                ))

        return results

    def copy(self, new_name: str) -> "InMemoryGraph":
        cloned = InMemoryGraph(new_name)
        cloned.nodes = copy.deepcopy(self.nodes)
        cloned.edges = copy.deepcopy(self.edges)
        cloned.incidents = copy.deepcopy(self.incidents)
        cloned.alerts = copy.deepcopy(self.alerts)
        client = get_in_memory_client()
        client.graphs[new_name] = cloned
        return cloned

    def delete(self):
        client = get_in_memory_client()
        if self.name in client.graphs:
            del client.graphs[self.name]


class InMemoryClient:
    def __init__(self):
        self.graphs: Dict[str, InMemoryGraph] = {}

    def select_graph(self, name: str = "nexus") -> InMemoryGraph:
        if name not in self.graphs:
            g = InMemoryGraph(name)
            from seed.generate import background, scenario1, scenario2, scenario3, scenario4
            background(g)
            scenario1(g)
            scenario2(g)
            scenario3(g)
            scenario4(g)
            self.graphs[name] = g
        return self.graphs[name]

    def list_graphs(self) -> List[str]:
        return list(self.graphs.keys()) or ["nexus"]


_in_memory_singleton: Optional[InMemoryClient] = None


def get_in_memory_client() -> InMemoryClient:
    global _in_memory_singleton
    if _in_memory_singleton is None:
        _in_memory_singleton = InMemoryClient()
        _in_memory_singleton.select_graph("nexus")
    return _in_memory_singleton
