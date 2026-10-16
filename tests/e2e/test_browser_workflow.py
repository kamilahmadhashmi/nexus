"""Browser smoke test for the local NEXUS demo. Requires Compose + Playwright Chromium."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.getenv("NEXUS_BASE_URL", "http://localhost:8080")
SCREENSHOT_DIR = Path(os.getenv("NEXUS_SCREENSHOT_DIR", "artifacts/screenshots"))


def test_investigate_contain_rollback_reset_and_responsive_layout():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(f"{error}\n{error.stack}"))

        response = page.goto(BASE_URL, wait_until="networkidle")
        assert response and response.status == 200
        assert page.title() == "NEXUS — Graph-grounded response"
        assert page.locator("#alert option").count() == 3
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-home-desktop.png"), full_page=True)

        page.locator("#alert").select_option("ALT-1042")
        page.get_by_role("button", name="Investigate").click()
        page.get_by_text("mode: scripted").wait_for()
        page.get_by_text("RECOMMENDED:").wait_for()
        page.wait_for_function("typeof cy !== 'undefined' && cy.nodes().length > 0")
        page.get_by_role("button", name="Re-run physics").click()
        page.get_by_text("Physics settled · drag nodes to explore").wait_for()
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-investigation-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function("document.documentElement.scrollWidth <= window.innerWidth")
        assert page.locator("#matrix").evaluate("element => element.scrollWidth > element.clientWidth")
        page.screenshot(path=str(SCREENSHOT_DIR / "nexus-investigation-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})

        page.get_by_role("button", name="CONTAIN").click()
        page.get_by_text("After containment:").wait_for()
        assert "verified: true" in page.locator("#decision").inner_text()
        assert "Graph mutated:" in page.locator("#decision").inner_text()

        page.get_by_role("button", name="ROLLBACK").click()
        page.get_by_role("button", name="CONTAIN").wait_for()
        assert "Graph mutated:" not in page.locator("#decision").inner_text()

        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Reset demo graph").click()
        page.get_by_text("157 nodes restored.").wait_for()
        assert page.locator("#alert option").count() == 3

        assert page_errors == []
        browser.close()
