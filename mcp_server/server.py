from mcp.server.fastmcp import FastMCP

from engine import tools

mcp = FastMCP("nexus")


@mcp.tool(description="Match names, IDs or fragments from alert text to synthetic graph entities.")
def resolve_entities(queries: list[str]) -> dict:
    return tools.call("resolve_entities", {"queries": queries})


@mcp.tool(description="Find multi-hop attack paths to critical synthetic data stores.")
def find_attack_paths(start_id: str, max_depth: int = 7) -> dict:
    return tools.call("find_attack_paths", {"start_id": start_id, "max_depth": max_depth})


@mcp.tool(description="Count reachable entities grouped by type.")
def blast_radius(start_id: str) -> dict:
    return tools.call("blast_radius", {"start_id": start_id})


@mcp.tool(description="Calculate deterministic graph-grounded risk with a term breakdown.")
def calculate_risk(start_id: str) -> dict:
    return tools.call("calculate_risk", {"start_id": start_id})


@mcp.tool(description="Rank nodes by the share of attack paths passing through them.")
def find_choke_points(start_id: str, top_n: int = 5) -> dict:
    return tools.call("find_choke_points", {"start_id": start_id, "top_n": top_n})


@mcp.tool(description="Simulate candidate containment actions on graph copies and recommend one.")
def simulate_containment(start_id: str, alert_id: str) -> dict:
    return tools.call("simulate_containment", {"start_id": start_id, "alert_id": alert_id})


@mcp.tool(description="Execute a simulated action; high-impact actions need human approval.")
def execute_containment(investigation_id: str, action: str, target: str = "") -> dict:
    return tools.call("execute_containment", {
        "investigation_id": investigation_id, "action": action,
        "target": target or None, "approved": False,
    })


@mcp.tool(description="Undo containment changes for an investigation.")
def rollback(investigation_id: str) -> dict:
    return tools.call("rollback", {"investigation_id": investigation_id})


if __name__ == "__main__":
    mcp.run()
