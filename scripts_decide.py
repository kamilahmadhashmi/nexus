from engine import tools

SCENARIOS = [
    ("U-ALEX", "ALT-1042"),
    ("SVC-ACCT-17", "ALT-2071"),
    ("U-PRIYA", "ALT-3310"),
]


def main():
    for subject, alert_id in SCENARIOS:
        result = tools.simulate_containment(subject, alert_id)
        if "error" in result:
            raise RuntimeError(result["error"])
        recommendation = result["recommendation"]
        print(
            f"{alert_id} initial {result['initial_risk']} -> "
            f"{recommendation['action']} {recommendation['target']} "
            f"| {recommendation['why']}"
        )
        for row in result["matrix"]:
            print(
                " %-20s %-18s residual %3d impact %3d %-8s dominated_by %s"
                % (
                    row["action"],
                    row["target"] or "",
                    row["residual_risk"],
                    row["impact"],
                    row["impact_label"],
                    row.get("dominated_by"),
                )
            )


if __name__ == "__main__":
    main()
