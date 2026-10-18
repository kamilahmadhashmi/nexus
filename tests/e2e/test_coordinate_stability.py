"""End-to-End Test for Graph Initial Highlighting and Coordinate Stability.

Verifies:
1. BUG 1 Fix: Complete incident topology highlighting on initial demo run (alert, threat IP, CVE, routes).
2. BUG 2 Fix: Zero coordinate drift (max drift < 0.001px) across all UI interactions (route buttons,
   legend filters, inspector selection, view mode toggles, forces drawer, containment, and rollback).
"""

import os
import time
import math
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("NEXUS_BASE_URL", "http://localhost:8080")


def test_initial_highlighting_and_coordinate_stability():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        
        # 1. Load application & Reset graph state
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_selector('#reset')
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#reset").click()
        page.locator("#decision-content").filter(has_text="Demo graph successfully restored").wait_for()

        # 2. Click "Run guided demo" (ALT-1042)
        page.wait_for_selector('#guided-demo')
        page.click('#guided-demo')
        page.wait_for_function("typeof cy !== 'undefined' && cy !== null && cy.nodes().length > 0")

        # 3. VERIFY BUG 1: Complete incident topology is highlighted on the very first run
        page.wait_for_function("cy.nodes('.path-selected-node').length > 0", timeout=5000)
        highlighted_nodes = page.evaluate("() => cy.nodes('.path-selected-node').map(n => n.id())")
        
        # Incident lateral paths, alert, threat ingress IP, and active CVE must all be highlighted
        expected_incident_nodes = [
            "U-ALEX", "LAPTOP-042", "DEV-SERVER-03", "DEV-SERVER-07",
            "JUMPBOX-01", "SVC-ACCT-09", "PROD-API", "CUSTOMER-DB",
            "SYNTH-VULN-2026-01", "IP-203-0-113-77", "ALT-1042"
        ]
        for node_id in expected_incident_nodes:
            assert node_id in highlighted_nodes, f"Incident node {node_id} was not highlighted on initial run!"
        
        # All nodes remain at 100% full brightness by default in All Routes view
        dimmed_nodes = page.evaluate("() => cy.nodes('.obsidian-dimmed').map(n => n.id())")
        assert len(dimmed_nodes) == 0, f"No nodes should be dimmed on initial run in All Routes view, got: {dimmed_nodes}"
        expected_bg_nodes = ["WEB-FRONTEND", "PAYMENTS-SVC", "MOBILE-APP", "IP-203-0-113-99"]
        for node_id in expected_bg_nodes:
            opacity = page.evaluate(f"() => cy.getElementById('{node_id}').style('opacity')")
            assert float(opacity) >= 0.9, f"Background node {node_id} should be full brightness (1.0), got {opacity}"

        # 4. Verify continuous live physics by default, then pause specifically for static button checks
        assert page.evaluate("() => !isPhysicsPaused && !!jiggleLoopId") is True, "Physics should be active by default"
        page.locator('#physics-pause-btn').click()
        time.sleep(0.3)
        assert page.evaluate("() => isPhysicsPaused") is True, "Physics should be paused after clicking Pause"

        # Record baseline positions during paused investigation
        initial_positions = page.evaluate("""() => {
            const pos = {};
            cy.nodes().forEach(n => {
                pos[n.id()] = { x: n.position('x'), y: n.position('y') };
            });
            return pos;
        }""")
        assert len(initial_positions) >= 15, f"Expected at least 15 nodes, got {len(initial_positions)}"

        def assert_positions_unchanged(action_name):
            current_positions = page.evaluate("""() => {
                const pos = {};
                cy.nodes().forEach(n => {
                    pos[n.id()] = { x: n.position('x'), y: n.position('y') };
                });
                return pos;
            }""")
            max_drift = 0.0
            drifting_nodes = []
            for node_id, init_pos in initial_positions.items():
                curr = current_positions.get(node_id)
                assert curr is not None, f"Node {node_id} disappeared after {action_name}"
                dist = math.hypot(curr['x'] - init_pos['x'], curr['y'] - init_pos['y'])
                if dist > max_drift:
                    max_drift = dist
                if dist > 0.001:
                    drifting_nodes.append((node_id, dist))
            assert max_drift < 0.001, f"Nodes moved after {action_name}! Max drift: {max_drift:.6f}px, Drifting: {drifting_nodes}"

        # 5. VERIFY BUG 2: Zero coordinate drift across all interaction types
        # A. Route 1 button
        page.locator('.path-tab-btn:has-text("Route 1")').click()
        time.sleep(0.3)
        assert_positions_unchanged("Click Route 1")

        # B. Route 2 button
        page.locator('.path-tab-btn:has-text("Route 2")').click()
        time.sleep(0.3)
        assert_positions_unchanged("Click Route 2")

        # C. Route 3 button
        page.locator('.path-tab-btn:has-text("Route 3")').click()
        time.sleep(0.3)
        assert_positions_unchanged("Click Route 3")

        # D. All Routes button
        page.locator('.path-tab-btn:has-text("All Routes")').click()
        time.sleep(0.3)
        assert_positions_unchanged("Click All Routes")

        # E. Legend Pill Filter (Server)
        page.locator('.legend-pill:has-text("Server")').click()
        time.sleep(0.3)
        assert_positions_unchanged("Click Legend Pill Server")

        # F. Reset Legend Pill Filter
        page.locator('.legend-pill:has-text("Server")').click()
        time.sleep(0.3)
        assert_positions_unchanged("Reset Legend Pill Server")

        # G. Select Node (Inspect DEV-SERVER-03)
        page.evaluate("() => window.inspectNode(cy.getElementById('DEV-SERVER-03'))")
        time.sleep(0.3)
        assert_positions_unchanged("Inspect Node DEV-SERVER-03")

        # H. Subway Node Badge Click
        page.evaluate("() => window.inspectNodeById('CUSTOMER-DB')")
        time.sleep(0.3)
        assert_positions_unchanged("Inspect Node By Id CUSTOMER-DB")

        # I. Toggle View Mode: Corridor
        page.locator('#view-corridor-btn').click()
        time.sleep(0.3)
        assert_positions_unchanged("Switch to Corridor View")

        # J. Toggle View Mode: Blast
        page.locator('#view-blast-btn').click()
        time.sleep(0.3)
        assert_positions_unchanged("Switch to Blast Radius View")

        # K. Toggle View Mode: Fabric
        page.locator('#view-fabric-btn').click()
        time.sleep(0.3)
        assert_positions_unchanged("Switch to Full Fabric View")

        # L. Toggle Forces Drawer
        page.locator('#forces-toggle-btn').click()
        time.sleep(0.2)
        page.locator('#forces-toggle-btn').click()
        time.sleep(0.2)
        assert_positions_unchanged("Toggle Forces Drawer")

        # M. Containment Action
        page.locator('#contain').click()
        page.locator('.mutation-alert').wait_for()
        time.sleep(0.5)
        assert_positions_unchanged("Execute Containment Action")

        # N. Rollback Action
        page.locator('#rollback').click()
        page.locator('#contain').wait_for()
        time.sleep(0.5)
        assert_positions_unchanged("Rollback Containment Action")

        # 6. Specifically turn physics back ON via Resume button and verify live continuous physics
        page.locator('#physics-pause-btn').click()
        time.sleep(0.3)
        resumed = page.evaluate("() => !isPhysicsPaused && !!jiggleLoopId")
        assert resumed is True, "Physics should resume after clicking Pause/Resume button"

        browser.close()
