"""Verification script for the upgraded NEXUS Cyber Threat Intelligence Graph Centerpiece."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.getenv("NEXUS_BASE_URL", "http://localhost:8080")
SCREENSHOT_DIR = Path(os.getenv("NEXUS_SCREENSHOT_DIR", "artifacts/screenshots"))


def test_cyber_graph_centerpiece():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 960}, device_scale_factor=1)
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(f"{error}\n{error.stack}"))

        # 1. Reset to pristine state
        page.goto(BASE_URL, wait_until="networkidle")
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#reset").click()
        page.locator("#decision-content").filter(has_text="Demo graph successfully restored").wait_for()

        # 2. Run guided demo (ALT-1042)
        page.locator("#guided-demo").click()
        page.locator(".action-header").filter(has_text="Recommended Response Policy").wait_for()
        page.wait_for_function("typeof cy !== 'undefined' && cy.nodes().length >= 10")

        # 3. Verify multi-layer cyber topology nodes
        node_kinds = page.evaluate("Array.from(new Set(cy.nodes().map(n => n.data('kind'))))")
        print("Detected node kinds in graph:", node_kinds)
        assert "IPAddress" in node_kinds
        assert "Vulnerability" in node_kinds
        assert "DataStore" in node_kinds
        assert "Server" in node_kinds
        assert "Person" in node_kinds
        assert "Device" in node_kinds

        # 4. Test View Modes (Corridor, Fabric, Blast)
        page.locator("#view-corridor-btn").click()
        expect(page.locator("#view-corridor-btn")).to_have_class("view-mode-btn active")
        page.wait_for_timeout(400)
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-view-mode-corridor.png"))

        page.locator("#view-blast-btn").click()
        expect(page.locator("#view-blast-btn")).to_have_class("view-mode-btn active")
        page.wait_for_timeout(400)
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-view-mode-blast-radius.png"))

        page.locator("#view-fabric-btn").click()
        expect(page.locator("#view-fabric-btn")).to_have_class("view-mode-btn active")
        page.wait_for_timeout(400)

        # 5. Test Live Search
        page.locator("#entity-search").fill("SYNTH-VULN")
        page.locator("#entity-search").press("Enter")
        page.wait_for_timeout(400)
        expect(page.locator("#node-inspector")).to_be_visible()
        expect(page.locator("#inspect-title")).to_contain_text("SYNTH-VULN-2026-01")
        expect(page.locator("#inspect-mitre-row")).to_be_visible()
        expect(page.locator("#inspect-mitre")).to_contain_text("Privilege Escalation")
        expect(page.locator("#inspect-props")).to_contain_text("CVSS Score")
        expect(page.locator("#inspect-props")).to_contain_text("10.0")
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-node-inspector-vulnerability.png"))

        # Clear search
        page.locator("#entity-search").fill("")
        page.locator("#entity-search").press("Enter")

        # 6. Test Edge Tap Inspection
        edge_id = page.evaluate("cy.edges()[0].id()")
        page.evaluate(f"window.inspectEdge(cy.getElementById('{edge_id}'))")
        expect(page.locator("#node-inspector")).to_be_visible()
        expect(page.locator("#inspect-kind")).to_contain_text("Relationship Edge")
        expect(page.locator("#inspect-props")).to_contain_text("Vector")

        # 7. Test On-Demand Dynamic Expansion on DEV-SERVER-03
        page.evaluate("window.inspectNode(cy.getElementById('DEV-SERVER-03'))")
        initial_nodes_count = page.evaluate("cy.nodes().length")
        page.locator("#inspect-expand-btn").click()
        page.wait_for_timeout(600)
        post_expand_count = page.evaluate("cy.nodes().length")
        assert post_expand_count >= initial_nodes_count

        # 8. Capture Full Centerpiece Hero Screenshot
        page.locator("#inspect-close").click()
        page.locator("#view-fabric-btn").click()
        page.locator("#fit-canvas-btn").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-cyber-centerpiece-graph-full.png"), full_page=True)

        assert page_errors == []
        browser.close()
        print("Cyber threat intelligence graph centerpiece verification PASSED successfully!")
