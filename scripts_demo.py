from engine import impact, paths, risk
from engine.db import graph


def main():
    current_graph = graph()
    for start_id in ["U-ALEX", "SVC-ACCT-17", "U-PRIYA"]:
        result = paths.find_attack_paths(current_graph, start_id)
        score = risk.calculate_risk(result["paths"])
        print(f"{start_id} paths: {len(result['paths'])} risk: {score['score']} {score['label']}")
        for path in result["paths"]:
            print("  " + " > ".join(path["ids"]) + f" exploit {path['exploit']}")
    for account_id in ["SVC-ACCT-09", "SVC-ACCT-17"]:
        result = impact.action_impact(current_graph, "disable_account", account_id)
        print(f"impact if {account_id} disabled: {result}")


if __name__ == "__main__":
    main()
