import math

K = 4.0


def band(score):
    if score < 25:
        return "LOW"
    if score < 50:
        return "MEDIUM"
    if score < 75:
        return "HIGH"
    return "CRITICAL"


def calculate_risk(paths):
    by_target = {}
    for path in paths:
        by_target.setdefault(path["target"], []).append(path)
    terms = []
    raw = 0.0
    for target, target_paths in sorted(by_target.items()):
        miss_probability = 1.0
        for path in target_paths:
            miss_probability *= 1.0 - path["exploit"]
        reach_probability = 1.0 - miss_probability
        # Part B's worked implementation takes the maximum privilege property
        # found on any route to this target; use the stated fallback if absent.
        privilege = max(
            [max(path["priv"]) for path in target_paths if path["priv"]] + [0.0]
        )
        if privilege <= 0:
            privilege = 0.5
        criticality = target_paths[0]["crit"]
        term = criticality * privilege * reach_probability
        raw += term
        terms.append(
            {
                "target": target,
                "criticality": criticality,
                "privilege": privilege,
                "reach_probability": round(reach_probability, 3),
                "paths": len(target_paths),
                "term": round(term, 3),
            }
        )
    score = round(100 * (1 - math.exp(-raw / K)))
    return {"score": score, "label": band(score), "raw": round(raw, 3), "K": K, "terms": terms}
