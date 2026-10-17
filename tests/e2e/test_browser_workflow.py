"""Browser smoke and interactive physics test for the local NEXUS demo. Requires Compose + Playwright Chromium."""

import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


BASE_URL = os.getenv("NEXUS_BASE_URL", "http://localhost:8080")
SCREENSHOT_DIR = Path(os.getenv("NEXUS_SCREENSHOT_DIR", "artifacts/screenshots"))


def test_investigate_contain_rollback_reset_and_responsive_layout():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(f"{error}\n{error.stack}"))

        # 1. Home page load
        response = page.goto(BASE_URL, wait_until="networkidle")
        assert response and response.status == 200
        assert "NEXUS" in page.title()
        assert page.locator("#alert option").count() == 3
        expect(page.locator("#mode")).to_have_value("mock")
        expect(page.locator("#guided-demo")).to_contain_text("Run guided demo")
        expect(page.locator(".demo-guide")).to_contain_text("no model key required")
        assert page.locator("#matrix-card").evaluate("el => el.getBoundingClientRect().width") > page.locator("#decision-card").evaluate("el => el.getBoundingClientRect().width")
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-home-desktop.png"), full_page=True)

        # 2. Run the one-click guided investigation
        page.locator("#guided-demo").click()
        
        # Verify scripted mode, graph evidence, and a readable recommendation
        page.locator("#mode-badge").filter(has_text="SCRIPTED · NO MODEL").wait_for()
        page.locator(".action-header").filter(has_text="Recommended Response Policy").wait_for()
        expect(page.locator(".evidence-panel").first).to_contain_text("lowest-impact Pareto option")
        expect(page.locator(".evidence-panel").first).to_contain_text("not a probability")
        evidence_details = page.locator(".evidence-panel details")
        expect(evidence_details.locator("summary")).to_contain_text("Inspect graph evidence")
        evidence_details.locator("summary").click()
        expect(evidence_details).to_contain_text("U-ALEX")
        expect(evidence_details).to_contain_text("CUSTOMER-DB")
        page.wait_for_function("typeof cy !== 'undefined' && cy.nodes().length > 0")

        # 3. Verify Obsidian Force-Directed Physics Toolbar & Drawer
        page.locator("#physics-status").filter(has_text="Obsidian Force-Directed Physics Active").wait_for()
        page.wait_for_function("typeof physicsNodeMap !== 'undefined' && physicsNodeMap.size > 0")
        before_motion = page.evaluate("cy.nodes().map(n => n.position())")
        page.wait_for_timeout(600)
        after_motion = page.evaluate("cy.nodes().map(n => n.position())")
        assert any(((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5 > 0.2 for a, b in zip(before_motion, after_motion))
        page.locator("#relayout-btn").click()
        page.wait_for_function("jiggleLoopId !== null && physicsNodeMap.size > 0")
        after_layout = page.evaluate("cy.nodes().map(n => n.position())")
        page.wait_for_timeout(500)
        after_relayout_motion = page.evaluate("cy.nodes().map(n => n.position())")
        assert any(((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5 > 0.2 for a, b in zip(after_layout, after_relayout_motion))
        page.locator("#fit-btn").click()

        # Toggle Forces control drawer
        page.locator("#forces-toggle-btn").click()
        expect(page.locator("#forces-drawer")).to_be_visible()
        page.locator("#forces-toggle-btn").click()
        expect(page.locator("#forces-drawer")).to_be_hidden()

        # Test Physics Pause / Resume toggle
        page.locator("#physics-pause-btn").click()
        expect(page.locator("#pause-btn-text")).to_have_text("Resume")
        paused_positions = page.evaluate("cy.nodes().map(n => n.position())")
        page.wait_for_timeout(300)
        assert page.evaluate("cy.nodes().map(n => n.position())") == paused_positions
        page.locator("#physics-pause-btn").click()
        expect(page.locator("#pause-btn-text")).to_have_text("Pause")
        page.wait_for_timeout(500)
        resumed_positions = page.evaluate("cy.nodes().map(n => n.position())")
        assert any(((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5 > 0.2 for a, b in zip(paused_positions, resumed_positions))

        # Test Attack Path Spotlight toggle
        page.locator("#path-spotlight-btn").click()
        expect(page.locator("#path-spotlight-btn")).to_have_class("secondary active")
        page.locator("#path-spotlight-btn").click()
        expect(page.locator("#path-spotlight-btn")).not_to_have_class("secondary active")

        # 4. Test Node Selection & Floating Inspector
        page.evaluate("if (typeof window.inspectNode === 'function' && typeof cy !== 'undefined' && cy.nodes().length > 0) { window.inspectNode(cy.nodes()[0]); }")
        expect(page.locator("#node-inspector")).to_be_visible()
        expect(page.locator("#inspect-title")).not_to_be_empty()
        expect(page.locator("#inspect-id")).not_to_be_empty()
        
        # Test Node Pinning via Inspector button
        initial_pin_text = page.locator("#inspect-lock-btn").inner_text()
        page.locator("#inspect-lock-btn").click()
        expect(page.locator("#inspect-lock-btn")).not_to_have_text(initial_pin_text)
        page.locator("#inspect-lock-btn").click()  # Unpin
        page.locator("#inspect-close").click()
        expect(page.locator("#node-inspector")).to_be_hidden()

        # Save investigation screenshot
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-investigation-desktop.png"), full_page=True)

        # 5. Mobile responsive check
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function("document.documentElement.scrollWidth <= window.innerWidth")
        assert page.locator("#matrix-container").evaluate("element => element.scrollWidth >= element.clientWidth")
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-investigation-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})

        # 6. Execute Containment
        page.locator("#contain").click()
        page.locator(".mutation-alert").wait_for()
        assert "matches the simulated result" in page.locator(".action-notice").inner_text()
        assert "Containment is active on the synthetic graph" in page.locator("#decision-content").inner_text()

        # 7. Rollback Containment
        page.locator("#rollback").click()
        page.locator("#contain").wait_for()
        assert "Containment is active on the synthetic graph" not in page.locator("#decision-content").inner_text()
        expect(page.locator(".action-notice")).to_contain_text("Rollback complete")

        # 8. Reset Demo Graph
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#reset").click()
        page.locator("#decision-content").filter(has_text="Demo graph successfully restored").wait_for()
        assert page.locator("#alert option").count() == 3

        # Verify no console or unhandled page errors occurred
        assert page_errors == []
        browser.close()


def test_sandbox_diff_preview_and_live_cypher_repl():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(f"{error}\n{error.stack}"))

        page.goto(BASE_URL, wait_until="networkidle")

        # 1. Run investigation to populate matrix
        page.locator("#guided-demo").click()
        page.locator(".action-header").filter(has_text="Recommended Response Policy").wait_for()
        page.wait_for_function("typeof cy !== 'undefined' && cy.nodes().length > 0")

        # 2. Test Sandbox Diff Preview on Hover
        first_row = page.locator("#matrix-container tbody tr").first
        expect(first_row).to_be_visible()
        first_row.hover()
        expect(page.locator("#sandbox-preview-hud")).to_be_visible()
        expect(page.locator("#sb-hud-action-name")).not_to_be_empty()
        expect(page.locator("#sb-hud-risk")).to_contain_text("/100")

        # Verify Cytoscape diff class
        has_diff_elements = page.evaluate("cy.elements('.sandbox-target, .sandbox-severed, .sandbox-dimmed').length > 0")
        assert has_diff_elements is True

        # Test Lock / Toggle on Click
        first_row.click()
        expect(first_row).to_have_class(re.compile(r"previewing-active"))
        first_row.click()
        expect(first_row).not_to_have_class(re.compile(r"previewing-active"))

        # Hover targeted action row (row 1: isolate_device LAPTOP-042)
        targeted_row = page.locator("#matrix-container tbody tr").nth(1)
        targeted_row.hover()
        expect(page.locator("#sandbox-preview-hud")).to_be_visible()
        expect(page.locator("#sb-hud-target")).to_contain_text("LAPTOP-042")
        has_severed = page.evaluate("cy.elements('.sandbox-target, .sandbox-severed').length > 0")
        assert has_severed is True

        # 3. Test Live FalkorDB Cypher REPL
        page.locator("#cypher-toggle-btn").click()
        expect(page.locator("#cypher-card")).to_be_visible()

        # Click pre-loaded query chip: Crown Jewels
        crown_jewels_chip = page.locator(".cypher-chip").filter(has_text="Crown Jewels")
        crown_jewels_chip.click()

        # Wait for Cypher results table
        page.locator("#cypher-result-container table").wait_for()
        rows_count = page.locator("#cypher-result-container table tbody tr").count()
        assert rows_count > 0
        expect(page.locator("#cypher-latency-pill")).to_contain_text("ms")
        expect(page.locator("#cypher-result-container")).to_contain_text("CUSTOMER-DB")

        # Test Custom Cypher Query Execution
        page.locator("#cypher-input").fill("MATCH (u:Person) RETURN u.name, u.role LIMIT 5")
        page.locator("#run-cypher-btn").click()
        page.locator("#cypher-result-container table").wait_for()
        expect(page.locator("#cypher-result-container")).to_contain_text("U-BG-00")

        # Screenshot the 11/10 additions
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-cypher-repl-sandbox-diff.png"), full_page=True)

        assert page_errors == []
        browser.close()

