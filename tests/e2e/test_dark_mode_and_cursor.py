import os
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8080"


def test_theme_toggle_persistence_and_zero_drift():
    os.makedirs("tests/e2e/screenshots", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_selector("#theme-toggle-btn")

        # 1. Verify initial light theme
        initial_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        btn_text = page.locator("#theme-toggle-text").inner_text()
        btn_icon = page.locator("#theme-toggle-icon").inner_text()
        print(f"\nInitial state -> data-theme: {initial_theme}, text: {btn_text}")
        assert initial_theme is None or initial_theme == "", f"Unexpected initial theme: {initial_theme}"
        assert btn_text.upper() == "DARK", f"Expected text Dark, got {btn_text}"
        assert btn_icon in ["🌙", "\U0001f319"], f"Expected moon icon, got {repr(btn_icon)}"

        # 2. Run guided demo to populate Cytoscape graph
        page.click("#guided-demo")
        page.wait_for_function("typeof cy !== 'undefined' && cy !== null && cy.nodes().length > 0")
        page.wait_for_timeout(1000)

        initial_positions = page.evaluate(
            "() => cy.nodes().map(n => ({ id: n.id(), x: n.position('x'), y: n.position('y') }))"
        )
        print(f"Populated graph with {len(initial_positions)} nodes")

        # 3. Toggle to Dark Mode
        page.click("#theme-toggle-btn")
        page.wait_for_timeout(300)

        dark_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        dark_btn_text = page.locator("#theme-toggle-text").inner_text()
        dark_btn_icon = page.locator("#theme-toggle-icon").inner_text()
        local_storage_theme = page.evaluate("() => localStorage.getItem('nexus-theme')")
        print(
            f"After toggle 1 -> data-theme: {dark_theme}, text: {dark_btn_text}, localStorage: {local_storage_theme}"
        )
        assert dark_theme == "dark", f"Expected dark theme, got {dark_theme}"
        assert dark_btn_text.upper() == "LIGHT", f"Expected text Light, got {dark_btn_text}"
        assert dark_btn_icon in ["☀️", "\u2600\ufe0f", "\u2600"], f"Expected sun icon, got {repr(dark_btn_icon)}"
        assert local_storage_theme == "dark", f"Expected localStorage dark, got {local_storage_theme}"

        # Check node position drift after dark mode toggle
        dark_positions = page.evaluate(
            "() => cy.nodes().map(n => ({ id: n.id(), x: n.position('x'), y: n.position('y') }))"
        )
        max_drift = 0.0
        for p_init, p_dark in zip(initial_positions, dark_positions):
            dx = abs(p_init["x"] - p_dark["x"])
            dy = abs(p_init["y"] - p_dark["y"])
            max_drift = max(max_drift, dx, dy)
        print(f"Max node coordinate drift on Dark Mode switch: {max_drift:.6f}px")
        assert max_drift < 0.001, f"Node coordinate drift too high: {max_drift}px"

        # Take dark mode screenshot
        page.screenshot(path="tests/e2e/screenshots/dark_mode_demo.png")

        # 4. Toggle back to Light Mode
        page.click("#theme-toggle-btn")
        page.wait_for_timeout(300)

        light_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        light_btn_text = page.locator("#theme-toggle-text").inner_text()
        light_btn_icon = page.locator("#theme-toggle-icon").inner_text()
        local_storage_theme2 = page.evaluate("() => localStorage.getItem('nexus-theme')")
        print(
            f"After toggle 2 -> data-theme: {light_theme}, text: {light_btn_text}, localStorage: {local_storage_theme2}"
        )
        assert light_theme is None or light_theme == "", f"Expected light theme, got {light_theme}"
        assert light_btn_text.upper() == "DARK", f"Expected text Dark, got {light_btn_text}"
        assert light_btn_icon in ["🌙", "\U0001f319"], f"Expected moon icon, got {repr(light_btn_icon)}"

        # Check node position drift after light mode toggle
        light_positions = page.evaluate(
            "() => cy.nodes().map(n => ({ id: n.id(), x: n.position('x'), y: n.position('y') }))"
        )
        max_drift2 = 0.0
        for p_init, p_light in zip(initial_positions, light_positions):
            dx = abs(p_init["x"] - p_light["x"])
            dy = abs(p_init["y"] - p_light["y"])
            max_drift2 = max(max_drift2, dx, dy)
        print(f"Max node coordinate drift on Light Mode switch: {max_drift2:.6f}px")
        assert max_drift2 < 0.001, f"Node coordinate drift too high: {max_drift2}px"

        # Take light mode screenshot
        page.screenshot(path="tests/e2e/screenshots/light_mode_demo.png")

        # 5. Verify non-laggy cursor follower
        cursor_follower = page.locator("#memphis-cursor-follower")
        assert cursor_follower.count() == 1, "Cursor follower element missing"
        page.mouse.move(300, 300)
        page.wait_for_timeout(200)
        display = cursor_follower.evaluate("el => window.getComputedStyle(el).display")
        print(f"Cursor follower display after mousemove: {display}")
        assert display == "block", f"Cursor follower should be display: block, got {display}"

        # 6. Responsive header margin verification across viewports
        viewports = [1100, 1280, 1440, 1600]
        for w in viewports:
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(100)
            btn_box = page.locator("#theme-toggle-btn").bounding_box()
            right_margin = w - (btn_box["x"] + btn_box["width"])
            print(f"Viewport {w}px -> Theme toggle right margin: {right_margin:.1f}px")
            assert right_margin >= 18, f"Viewport {w}px theme toggle right margin too small: {right_margin}px"

        browser.close()
