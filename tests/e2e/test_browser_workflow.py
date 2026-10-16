"""Browser smoke and interactive physics test for the local NEXUS demo. Requires Compose + Playwright Chromium."""

import os
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
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-home-desktop.png"), full_page=True)

        # 2. Select scenario & run investigation
        page.locator("#alert").select_option("ALT-1042")
        page.locator("#go").click()
        
        # Verify scripted trace badge and recommended action banner
        page.locator("#mode-badge").filter(has_text="SCRIPTED TRACE").wait_for()
        page.locator(".action-header").filter(has_text="Recommended Response Policy").wait_for()
        page.wait_for_function("typeof cy !== 'undefined' && cy.nodes().length > 0")

        # 3. Verify Obsidian Force-Directed Physics Toolbar & Drawer
        page.locator("#physics-status").filter(has_text="Obsidian Force-Directed Physics Active").wait_for()
        page.locator("#fit-btn").click()

        # Toggle Forces control drawer
        page.locator("#forces-toggle-btn").click()
        expect(page.locator("#forces-drawer")).to_be_visible()
        page.locator("#forces-toggle-btn").click()
        expect(page.locator("#forces-drawer")).to_be_hidden()

        # Test Physics Pause / Resume toggle
        page.locator("#physics-pause-btn").click()
        expect(page.locator("#pause-btn-text")).to_have_text("Resume")
        page.locator("#physics-pause-btn").click()
        expect(page.locator("#pause-btn-text")).to_have_text("Pause")

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
        assert "VERIFIED MATCH" in page.locator("#decision-content").inner_text()
        assert "Live Mutation Active:" in page.locator("#decision-content").inner_text()

        # 7. Rollback Containment
        page.locator("#rollback").click()
        page.locator("#contain").wait_for()
        assert "Live Mutation Active:" not in page.locator("#decision-content").inner_text()

        # 8. Reset Demo Graph
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#reset").click()
        page.locator("#decision-content").filter(has_text="Demo graph successfully restored").wait_for()
        assert page.locator("#alert option").count() == 3

        # Verify no console or unhandled page errors occurred
        assert page_errors == []
        browser.close()
