import pytest

from engine import execute, tools
from engine.db import client
from seed.generate import build


@pytest.fixture(scope="session", autouse=True)
def seeded():
    build()


def decide(subject, alert):
    return tools.simulate_containment(subject, alert)


def test_scenario1_isolates_laptop():
    out = decide("U-ALEX", "ALT-1042")
    assert out["initial_risk"] >= 75
    assert out["recommendation"]["action"] == "isolate_device"
    assert out["recommendation"]["target"] == "LAPTOP-042"
    assert tools.find_attack_paths("U-ALEX")["count"] == 3


def test_scenario2_disables_account():
    out = decide("SVC-ACCT-17", "ALT-2071")
    assert out["recommendation"]["action"] == "disable_account"
    assert out["recommendation"]["target"] == "SVC-ACCT-17"


def test_scenario3_monitors_only():
    out = decide("U-PRIYA", "ALT-3310")
    assert out["recommendation"]["action"] == "monitor_only"


def test_no_candidate_falls_back_to_monitor():
    from engine.pareto import recommend

    rows = [{
        "action": "monitor_only", "target": None,
        "residual_risk": 55, "impact": 0, "needs_approval": False,
    }]
    decision = recommend(55, rows)
    assert decision["row"]["action"] == "monitor_only"
    assert decision["requires_approval"] is False


def test_unsimulated_action_is_rejected():
    out = decide("U-ALEX", "ALT-1042")
    result = tools.execute_containment(out["investigation_id"], "isolate_device", "LAPTOP-PRIYA")
    assert result["ok"] is False and "not simulated" in result["error"]


def test_high_impact_needs_approval():
    out = decide("U-ALEX", "ALT-1042")
    result = tools.execute_containment(out["investigation_id"], "disable_account", "SVC-ACCT-09")
    assert result["ok"] is False and result["error"] == "APPROVAL_REQUIRED"


def test_execute_verify_rollback():
    out = decide("U-ALEX", "ALT-1042")
    inv, rec = out["investigation_id"], out["recommendation"]
    result = tools.execute_containment(inv, rec["action"], rec["target"])
    assert result["ok"] and result["verified"]
    assert tools.rollback(inv)["risk_now"] == out["initial_risk"]


def test_sandbox_graphs_are_deleted():
    decide("U-ALEX", "ALT-1042")
    leftovers = [name for name in client().list_graphs() if name.startswith("nexus_sim_")]
    assert leftovers == []


def test_all_scenarios_scripted_trace_and_decisions():
    from agent import loop

    expected = {
        "ALT-1042": ("isolate_device", "LAPTOP-042"),
        "ALT-2071": ("disable_account", "SVC-ACCT-17"),
        "ALT-3310": ("monitor_only", None),
    }
    for alert, choice in expected.items():
        subject = {"ALT-1042": "U-ALEX", "ALT-2071": "SVC-ACCT-17", "ALT-3310": "U-PRIYA"}[alert]
        out = loop.run_scripted(alert, subject, autonomous=False)
        rec = out["recommendation"]
        assert (rec["action"], rec["target"]) == choice
        assert out["mode"] == "scripted" and len(out["trace"]) == 5


def test_api_mock_flow():
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as web:
        alerts = web.get("/api/alerts")
        assert alerts.status_code == 200 and len(alerts.json()) >= 3
        investigation = web.post("/api/investigate", json={"alert_id": "ALT-1042", "mode": "mock"})
        assert investigation.status_code == 200
        body = investigation.json()
        inv = body["investigation_id"]
        assert body["mode"] == "scripted" and body["recommendation"]["action"] == "isolate_device"
        assert web.get(f"/api/graph/{inv}").status_code == 200
        contained = web.post("/api/contain", json={"investigation_id": inv})
        assert contained.json()["ok"] and contained.json()["verified"]
        assert web.get(f"/api/investigations/{inv}").json()["executed"]["action"] == "isolate_device"
        rolled = web.post("/api/rollback", json={"investigation_id": inv})
        assert rolled.json()["risk_now"] == 80


def test_falkordb_persistent_memory_escalation():
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as web:
        # Reset to ensure clean graph state
        web.post("/api/reset")
        # 1. Investigate and contain ALT-1042
        inv1 = web.post("/api/investigate", json={"alert_id": "ALT-1042", "mode": "mock"}).json()["investigation_id"]
        web.post("/api/contain", json={"investigation_id": inv1})

        # 2. Run follow-up investigation on ALT-1043 (repeat offender)
        inv2_res = web.post("/api/investigate", json={"alert_id": "ALT-1043", "mode": "mock"})
        assert inv2_res.status_code == 200
        data2 = inv2_res.json()

        # 3. Verify that FalkorDB memory was retrieved and visibly escalated the policy
        assert data2.get("falkordb_memory") is not None
        assert data2["falkordb_memory"]["has_memory"] is True
        assert data2["falkordb_memory"]["prior_alert"] == "ALT-1042"
        assert "ESCALATED VIA FALKORDB PERSISTENT MEMORY" in data2["recommendation"]["why"]

        # Cleanup: rollback ALT-1042 and reset
        web.post("/api/rollback", json={"investigation_id": inv1})
        web.post("/api/reset")
