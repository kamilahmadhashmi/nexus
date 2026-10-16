import uuid
from falkordb import FalkorDB


def main():
    client = FalkorDB(host="localhost", port=6379)
    graph_name = f"nexus_cap_test_{uuid.uuid4().hex[:8]}"
    copy_name = f"{graph_name}_copy"
    graph = client.select_graph(graph_name)
    copied = None
    try:
        graph.query("RETURN 1 AS ok")
        print("query ok")
        graph.query(
            "CREATE (:A {id:$a})-[:R]->(:B {id:$b})",
            {"a": "A1", "b": "B1"},
        )
        copied = graph.copy(copy_name)
        print("GRAPH.COPY ok")
        rows = copied.query("MATCH (n) RETURN count(n)").result_set
        print("copied nodes:", rows[0][0])
        procedures = graph.query(
            "CALL dbms.procedures() YIELD name RETURN name"
        ).result_set
        for name in sorted(row[0] for row in procedures):
            print(name)
    finally:
        if copied is not None:
            copied.delete()
        graph.delete()


if __name__ == "__main__":
    main()
