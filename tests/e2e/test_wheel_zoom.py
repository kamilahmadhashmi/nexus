import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8080"


def test_attack_path_topology_scroll_wheel_zoom():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. Load application & populate Attack Path Traversal Topology
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_selector("#guided-demo")
        page.click("#guided-demo")
        page.wait_for_function("typeof cy !== 'undefined' && cy !== null && cy.nodes().length > 0")
        page.wait_for_function("isPhysicsSettled === true || jiggleLoopId === null", timeout=6000)
        page.wait_for_timeout(400)

        initial_zoom = page.evaluate("() => cy.zoom()")
        initial_scroll_y = page.evaluate("() => window.scrollY")
        user_zooming = page.evaluate("() => cy.userZoomingEnabled()")
        min_zoom = page.evaluate("() => cy.minZoom()")
        max_zoom = page.evaluate("() => cy.maxZoom()")

        print(f"\nInitial State -> Zoom: {initial_zoom:.4f}, scrollY: {initial_scroll_y}, userZooming: {user_zooming}")
        assert user_zooming is True, "userZoomingEnabled must be true"
        assert min_zoom == 0.2, f"Expected minZoom 0.2, got {min_zoom}"
        assert max_zoom == 3.5, f"Expected maxZoom 3.5, got {max_zoom}"

        initial_positions = page.evaluate(
            "() => cy.nodes().map(n => ({ id: n.id(), x: n.position('x'), y: n.position('y') }))"
        )

        # 2. Position cursor directly over the Attack Path Traversal Topology canvas
        cy_box = page.locator("#cy").bounding_box()
        assert cy_box is not None, "Cytoscape container #cy not found"
        cx = cy_box["x"] + cy_box["width"] / 2
        cy_y = cy_box["y"] + cy_box["height"] / 2
        page.mouse.move(cx, cy_y)

        # 3. Test Scroll Wheel ZOOM IN (4 steps)
        curr_zoom = initial_zoom
        for step in range(1, 5):
            page.mouse.wheel(0, -100)
            page.wait_for_timeout(100)
            new_zoom = page.evaluate("() => cy.zoom()")
            scroll_y = page.evaluate("() => window.scrollY")
            ratio = new_zoom / curr_zoom

            print(f"Zoom IN Step {step} -> Zoom: {new_zoom:.4f} (ratio: {ratio:.3f}x), scrollY: {scroll_y}")
            # Each step should zoom in with acceptable sensitivity (~1.10x to 1.20x per notch)
            assert new_zoom > curr_zoom, f"Step {step}: Zoom did not increase ({new_zoom} <= {curr_zoom})"
            assert 1.10 <= ratio <= 1.25, f"Step {step}: Zoom sensitivity unacceptable ({ratio:.3f}x)"
            assert scroll_y == initial_scroll_y, f"Step {step}: Scroll leaked to window ({scroll_y} != {initial_scroll_y})"
            curr_zoom = new_zoom

        # 4. Test Scroll Wheel ZOOM OUT (4 steps)
        for step in range(1, 5):
            page.mouse.wheel(0, 100)
            page.wait_for_timeout(100)
            new_zoom = page.evaluate("() => cy.zoom()")
            scroll_y = page.evaluate("() => window.scrollY")
            ratio = new_zoom / curr_zoom

            print(f"Zoom OUT Step {step} -> Zoom: {new_zoom:.4f} (ratio: {ratio:.3f}x), scrollY: {scroll_y}")
            # Each step should zoom out with acceptable sensitivity (~0.80x to 0.92x per notch)
            assert new_zoom < curr_zoom, f"Step {step}: Zoom did not decrease ({new_zoom} >= {curr_zoom})"
            assert 0.80 <= ratio <= 0.92, f"Step {step}: Zoom sensitivity unacceptable ({ratio:.3f}x)"
            assert scroll_y == initial_scroll_y, f"Step {step}: Scroll leaked to window ({scroll_y} != {initial_scroll_y})"
            curr_zoom = new_zoom

        # 5. Verify Node Coordinate Stability (model coordinates must not drift during zoom)
        after_positions = page.evaluate(
            "() => cy.nodes().map(n => ({ id: n.id(), x: n.position('x'), y: n.position('y') }))"
        )
        max_drift = 0.0
        for p_init, p_after in zip(initial_positions, after_positions):
            dx = abs(p_init["x"] - p_after["x"])
            dy = abs(p_init["y"] - p_after["y"])
            max_drift = max(max_drift, dx, dy)

        print(f"Max model coordinate drift after wheel zooming: {max_drift:.6f}px")
        assert max_drift < 0.001, f"Model coordinates drifted during zoom: {max_drift}px"

        browser.close()
