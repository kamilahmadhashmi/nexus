import random
from engine.db import MAIN, client

random.seed(42)
ROLES = ["engineer", "analyst", "sales", "support", "finance", "hr"]
LABELS = [
    "Person", "Device", "Server", "ServiceAccount", "Service", "DataStore",
    "Vulnerability", "IPAddress", "Alert",
]


def node(graph, label, node_id, **properties):
    properties["id"] = node_id
    properties["synthetic"] = True
    properties.setdefault("name", node_id)
    properties.setdefault("status", "ACTIVE")
    query = f"MERGE (n:{label} {{id:$id}}) SET n += $properties"
    graph.query(query, {"id": node_id, "properties": properties})


def edge(graph, source_id, target_id, relationship, weight):
    query = (
        "MATCH (a {id:$source}), (b {id:$target}) "
        f"MERGE (a)-[r:{relationship}]->(b) "
        "SET r.exploit=$weight, r.status='ACTIVE'"
    )
    graph.query(query, {"source": source_id, "target": target_id, "weight": weight})


def alert(graph, alert_id, alert_type, about_id, raw_text):
    node(graph, "Alert", alert_id, type=alert_type, raw_text=raw_text)
    graph.query(
        "MATCH (a:Alert {id:$alert}), (e {id:$entity}) "
        "MERGE (a)-[:ABOUT]->(e)",
        {"alert": alert_id, "entity": about_id},
    )


def background(graph):
    for index in range(10):
        node(
            graph,
            "DataStore",
            f"DS-BG-{index:02d}",
            criticality=random.randint(1, 4),
            record_count=random.randint(100, 5000),
            data_class="internal",
        )
    for index in range(12):
        node(
            graph,
            "Service",
            f"SVC-BG-{index:02d}",
            tier=random.choice([2, 3]),
            criticality=random.randint(1, 4),
        )
        edge(graph, f"SVC-BG-{index:02d}", f"DS-BG-{random.randint(0, 9):02d}", "READS", 0.8)
    for index in range(12):
        node(
            graph,
            "ServiceAccount",
            f"ACC-BG-{index:02d}",
            privilege=round(random.uniform(0.2, 0.5), 2),
            token_age_days=random.randint(5, 200),
            rotated=True,
        )
        edge(graph, f"ACC-BG-{index:02d}", f"SVC-BG-{index:02d}", "AUTHENTICATES_TO", 0.7)
    for index in range(20):
        node(
            graph,
            "Server",
            f"SRV-BG-{index:02d}",
            env=random.choice(["dev", "prod"]),
            criticality=random.randint(1, 4),
        )
        edge(graph, f"SRV-BG-{index:02d}", f"ACC-BG-{random.randint(0, 11):02d}", "HOSTS_CREDENTIAL", 0.5)
    for index in range(40):
        node(graph, "Person", f"U-BG-{index:02d}", role=random.choice(ROLES))
        node(
            graph,
            "Device",
            f"DEV-BG-{index:02d}",
            os=random.choice(["win", "mac", "linux"]),
            patched=random.random() > 0.3,
        )
        edge(graph, f"U-BG-{index:02d}", f"DEV-BG-{index:02d}", "OWNS", 0.9)
        edge(
            graph,
            f"DEV-BG-{index:02d}",
            f"SRV-BG-{random.randint(0, 19):02d}",
            "LOGS_INTO",
            0.6,
        )
        edge(
            graph,
            f"U-BG-{index:02d}",
            f"SVC-BG-{random.randint(0, 11):02d}",
            "USES",
            0.0,
        )


def scenario1(graph):
    node(graph, "Person", "U-ALEX", name="alex.m", role="engineer", home_region="Seattle")
    node(graph, "Device", "LAPTOP-042", owner_id="U-ALEX", os="win", patched=False)
    for server_id in ["DEV-SERVER-03", "DEV-SERVER-07", "JUMPBOX-01"]:
        node(graph, "Server", server_id, env="dev", criticality=5)
    node(
        graph,
        "Vulnerability",
        "SYNTH-VULN-2026-01",
        cvss=10.0,
        exploitability=0.9,
        note="synthetic vulnerability for the demo",
    )
    node(graph, "ServiceAccount", "SVC-ACCT-09", privilege=0.9, token_age_days=184, rotated=False)
    node(graph, "Service", "PROD-API", tier=1, criticality=9)
    node(graph, "Service", "WEB-FRONTEND", tier=1, criticality=8)
    node(graph, "Service", "PAYMENTS-SVC", tier=1, criticality=9)
    node(graph, "Service", "MOBILE-APP", tier=2, criticality=6)
    node(graph, "DataStore", "CUSTOMER-DB", criticality=10, record_count=1_250_000, data_class="PII")
    node(graph, "IPAddress", "IP-203-0-113-77", region="BR", reputation="suspicious")
    edge(graph, "U-ALEX", "LAPTOP-042", "OWNS", 0.9)
    for server_id, weight in [("DEV-SERVER-03", 0.8), ("DEV-SERVER-07", 0.6), ("JUMPBOX-01", 0.6)]:
        edge(graph, "LAPTOP-042", server_id, "LOGS_INTO", weight)
        edge(graph, server_id, "SVC-ACCT-09", "HOSTS_CREDENTIAL", 0.8)
    edge(graph, "DEV-SERVER-03", "SYNTH-VULN-2026-01", "AFFECTED_BY", 1.0)
    edge(graph, "SVC-ACCT-09", "PROD-API", "AUTHENTICATES_TO", 0.8)
    edge(graph, "PROD-API", "CUSTOMER-DB", "READS", 0.9)
    for service_id in ["WEB-FRONTEND", "PAYMENTS-SVC", "MOBILE-APP"]:
        edge(graph, service_id, "PROD-API", "DEPENDS_ON", 0.0)
    for index in range(30):
        edge(
            graph,
            f"U-BG-{index:02d}",
            random.choice(["WEB-FRONTEND", "PAYMENTS-SVC", "MOBILE-APP", "PROD-API"]),
            "USES",
            0.0,
        )
    edge(graph, "IP-203-0-113-77", "U-ALEX", "USED_BY", 0.0)
    alert(
        graph,
        "ALT-1042",
        "IMPOSSIBLE_TRAVEL",
        "U-ALEX",
        "ALT-1042 | IMPOSSIBLE_TRAVEL | user alex.m logged in from Seattle US then Sao Paulo BR 14 min apart | device LAPTOP-042 | src_ip 203.0.113.77",
    )


def scenario2(graph):
    node(graph, "ServiceAccount", "SVC-ACCT-17", privilege=0.7, token_age_days=412, rotated=False)
    node(graph, "Service", "BILLING-SVC", tier=3, criticality=5)
    node(graph, "DataStore", "BILLING-DB", criticality=8, record_count=300_000, data_class="PII")
    node(graph, "IPAddress", "IP-198-51-100-23", region="unknown", reputation="malicious")
    edge(graph, "SVC-ACCT-17", "BILLING-SVC", "AUTHENTICATES_TO", 0.9)
    edge(graph, "BILLING-SVC", "BILLING-DB", "READS", 0.9)
    edge(graph, "IP-198-51-100-23", "SVC-ACCT-17", "USED_BY", 0.0)
    for index in range(30, 34):
        edge(graph, f"U-BG-{index:02d}", "BILLING-SVC", "USES", 0.0)
    alert(
        graph,
        "ALT-2071",
        "LEAKED_TOKEN",
        "SVC-ACCT-17",
        "ALT-2071 | LEAKED_TOKEN | service account SVC-ACCT-17 token used from unknown external IP 198.51.100.23 outside normal hours",
    )


def scenario3(graph):
    node(graph, "Person", "U-PRIYA", name="priya.k", role="analyst", home_region="Pune")
    node(graph, "Device", "LAPTOP-PRIYA", owner_id="U-PRIYA", os="mac", patched=True)
    node(graph, "IPAddress", "IP-192-0-2-8", region="IN", reputation="clean")
    edge(graph, "U-PRIYA", "LAPTOP-PRIYA", "OWNS", 0.9)
    edge(graph, "LAPTOP-PRIYA", "SRV-BG-03", "LOGS_INTO", 0.6)
    edge(graph, "IP-192-0-2-8", "U-PRIYA", "USED_BY", 0.0)
    alert(
        graph,
        "ALT-3310",
        "NEW_LOCATION_LOGIN",
        "U-PRIYA",
        "ALT-3310 | NEW_LOCATION_LOGIN | user priya.k signed in from a new city (Jaipur IN) | device LAPTOP-PRIYA | src_ip 192.0.2.8",
    )


def build():
    graph_client = client()
    try:
        graph_client.select_graph(MAIN).delete()
    except Exception:
        pass
    target_graph = graph_client.select_graph(MAIN)
    for label in LABELS:
        target_graph.query(f"CREATE INDEX FOR (n:{label}) ON (n.id)")
    background(target_graph)
    scenario1(target_graph)
    scenario2(target_graph)
    scenario3(target_graph)
    count = target_graph.query("MATCH (n) RETURN count(n)").result_set[0][0]
    print(f"seeded nodes: {count}")
    return count


if __name__ == "__main__":
    build()
