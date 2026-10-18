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


def explain_candidate(row, pick, initial_score, target_threshold=TARGET):
    action = row["action"]
    target = row.get("target") or "perimeter"
    broken = row.get("paths_broken", 0)
    total = row.get("paths_before", 0)
    residual = row.get("residual_risk", 0)
    impact_val = row.get("impact", 0)
    dominated = row.get("dominated_by")

    is_pick = (row["action"] == pick["action"] and row.get("target") == pick.get("target"))

    if is_pick:
        if action == "monitor_only":
            return "Selected: initial risk below monitor threshold (benign event, no critical assets threatened)."
        return f"Selected: breaks {broken}/{total} attack paths at choke point, cutting risk {initial_score} -> {residual}/100 with optimal business impact ({impact_val})."

    if action == "monitor_only":
        return f"Rejected: leaves all {total} critical attack paths active to Crown Jewel (residual risk: {residual}/100 > {target_threshold})."

    if dominated:
        return f"Dominated by {dominated}: breaks only {broken}/{total} paths (residual risk: {residual}/100) while superior action eliminates paths at lower/equal impact."

    if residual <= target_threshold:
        return f"Pareto optimal: breaks {broken}/{total} paths (risk {residual}/100), but has higher business disruption ({impact_val} vs {pick.get('impact', 1)}) than selected policy."

    return f"Rejected: breaks {broken}/{total} paths, but leaves excessive residual risk ({residual}/100 > {target_threshold})."


def recommend(initial_score, rows, prior_incident=None):
    rows = mark_pareto(rows)
    monitor = next((row for row in rows if row["action"] == "monitor_only"), None)

    # Check if prior incident memory from FalkorDB alters recommendation
    if prior_incident and prior_incident.get("has_memory"):
        active_candidates = [
            r for r in rows
            if r["action"] in ("revoke_credentials", "disable_account", "isolate_device")
        ]
        if active_candidates:
            pick = min(active_candidates, key=lambda r: (r["residual_risk"], r["impact"]))
            inc_id = prior_incident.get("incident_id", "prior")
            prior_target = prior_incident.get("prior_target", "entity")
            prior_alert = prior_incident.get("prior_alert", "alert")
            why_text = (
                f"ESCALATED VIA FALKORDB PERSISTENT MEMORY: Repeat incident detected. "
                f"{prior_target} was previously contained under {prior_alert} ({inc_id}). "
                f"Escalating response policy to enforce strict {pick['action']} on {pick['target']} to prevent secondary token replay."
            )
            for row in rows:
                row["reason"] = explain_candidate(row, pick, initial_score)
            return {
                "row": pick,
                "requires_approval": pick.get("needs_approval", False),
                "why": why_text,
                "memory_escalated": True,
            }

    if initial_score < MONITOR_BELOW:
        pick = monitor or rows[0]
        for row in rows:
            row["reason"] = explain_candidate(row, pick, initial_score)
        return {
            "row": pick,
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
        for row in rows:
            row["reason"] = explain_candidate(row, pick, initial_score)
        return {
            "row": pick,
            "requires_approval": pick["needs_approval"],
            "why": f"lowest business impact among frontier actions reaching risk <= {TARGET}",
        }
    candidates = frontier or [row for row in rows if row["action"] != "monitor_only"]
    if not candidates:
        pick = monitor or rows[0]
        for row in rows:
            row["reason"] = explain_candidate(row, pick, initial_score)
        return {
            "row": pick,
            "requires_approval": False,
            "why": "no applicable containment action; monitor only",
        }
    pick = min(candidates, key=lambda row: (row["residual_risk"], row["impact"]))
    for row in rows:
        row["reason"] = explain_candidate(row, pick, initial_score)
    return {
        "row": pick,
        "requires_approval": True,
        "why": "no action reaches the target; lowest residual risk chosen, human approval required",
    }
