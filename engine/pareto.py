MONITOR_BELOW = 25
TARGET = 40


def mark_pareto(rows):
    for action in rows:
        action["dominated_by"] = None
    for action in rows:
        for alternative in rows:
            if alternative is action:
                continue
            no_worse = (
                alternative["residual_risk"] <= action["residual_risk"]
                and alternative["impact"] <= action["impact"]
            )
            strictly_better = (
                alternative["residual_risk"] < action["residual_risk"]
                or alternative["impact"] < action["impact"]
            )
            if no_worse and strictly_better:
                action["dominated_by"] = (
                    f"{alternative['action']} {alternative['target'] or ''}".strip()
                )
                break
    return rows


def recommend(initial_score, rows):
    rows = mark_pareto(rows)
    monitor = next(row for row in rows if row["action"] == "monitor_only")
    if initial_score < MONITOR_BELOW:
        return {
            "row": monitor,
            "requires_approval": False,
            "why": "initial risk below monitor threshold",
        }
    frontier = [
        row for row in rows
        if row["dominated_by"] is None and row["action"] != "monitor_only"
    ]
    feasible = [row for row in frontier if row["residual_risk"] <= TARGET]
    if feasible:
        pick = min(feasible, key=lambda row: (row["impact"], row["residual_risk"]))
        return {
            "row": pick,
            "requires_approval": pick["needs_approval"],
            "why": f"lowest business impact among frontier actions reaching risk <= {TARGET}",
        }
    candidates = frontier or [row for row in rows if row["action"] != "monitor_only"]
    if not candidates:
        return {
            "row": monitor,
            "requires_approval": False,
            "why": "no applicable containment action; monitor only",
        }
    pick = min(candidates, key=lambda row: (row["residual_risk"], row["impact"]))
    return {
        "row": pick,
        "requires_approval": True,
        "why": "no action reaches the target; lowest residual risk chosen, human approval required",
    }
