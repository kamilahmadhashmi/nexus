from engine import paths, risk, simulate, store
from engine.db import graph


def live_risk(subject):
    result = paths.find_attack_paths(graph(), subject)
    return risk.calculate_risk(result["paths"])


def execute(investigation_id, action, target=None, approved=False):
    record = store.get(investigation_id)
    if record is None:
        return {"ok": False, "error": "UNKNOWN_INVESTIGATION"}
    if action == "monitor_only":
        target = None
    row = next(
        (
            item for item in record["matrix"]
            if item["action"] == action and item["target"] == target
        ),
        None,
    )
    if row is None:
        return {
            "ok": False,
            "error": "REJECTED: this action was not simulated in this investigation",
        }
    recommendation = record["recommendation"]
    needs_approval = row["needs_approval"] or recommendation["requires_approval"]
    if needs_approval and not approved and action != "monitor_only":
        return {"ok": False, "error": "APPROVAL_REQUIRED", "impact": row["impact_label"]}
    before = live_risk(record["subject"])
    change_log = None
    if action != "monitor_only":
        change_log = simulate.apply_action(
            graph(), action, target, record["subject"], record["alert_id"]
        )
    after = live_risk(record["subject"])
    verified = abs(after["score"] - row["residual_risk"]) <= 1
    record["executed"] = {
        "action": action,
        "target": target,
        "before": before["score"],
        "after": after["score"],
        "verified": verified,
    }
    if change_log is not None:
        record.setdefault("change_log", []).append(change_log)
    store.save(investigation_id, record)
    return {
        "ok": True,
        "before": before["score"],
        "after": after["score"],
        "before_label": before["label"],
        "after_label": after["label"],
        "verified": verified,
        "simulated_residual": row["residual_risk"],
        "change_log": change_log,
    }


def rollback(investigation_id):
    record = store.get(investigation_id)
    if record is None:
        return {"ok": False, "error": "UNKNOWN_INVESTIGATION"}
    if record.get("executed") and record["executed"]["action"] != "monitor_only":
        simulate.restore(graph(), record["alert_id"])
    record["executed"] = None
    record["change_log"] = []
    store.save(investigation_id, record)
    return {"ok": True, "risk_now": live_risk(record["subject"])["score"]}
