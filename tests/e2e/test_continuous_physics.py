import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8080"


def test_continuous_physics_keeps_running_unless_specifically_paused():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_selector("#guided-demo")
        page.click("#guided-demo")
        page.wait_for_function("typeof cy !== 'undefined' && cy !== null && cy.nodes().length > 0")

        # 1. Verify physics loop stays continuously active over seconds without freezing
        for sec in range(1, 5):
            time.sleep(1)
            state = page.evaluate("() => ({ jiggle: !!jiggleLoopId, paused: isPhysicsPaused })")
            print(f"Time {sec}s -> Physics actively simulating: {state['jiggle']}, Paused: {state['paused']}")
            assert state["jiggle"] is True, f"Physics loop unexpectedly stopped at {sec}s"
            assert state["paused"] is False, f"Physics should remain unpaused by default at {sec}s"

        # 2. Verify dragging node triggers live elastic reaction
        node_pos_before = page.evaluate("() => cy.getElementById('U-ALEX').position()")
        print(f"Before drag -> U-ALEX: {node_pos_before}")

        # Drag node U-ALEX
        page.evaluate("""() => {
            const node = cy.getElementById('U-ALEX');
            node.emit('grab');
            node.position({ x: node.position('x') + 100, y: node.position('y') + 50 });
            node.emit('drag');
        }""")
        time.sleep(0.3)

        node_pos_during = page.evaluate("() => cy.getElementById('U-ALEX').position()")
        print(f"During drag -> U-ALEX: {node_pos_during}")
        assert abs(node_pos_during["x"] - node_pos_before["x"]) > 40, "Node did not move on drag"

        page.evaluate("""() => {
            const node = cy.getElementById('U-ALEX');
            node.emit('free');
        }""")
        time.sleep(0.5)

        # 3. Specifically turn physics OFF via the Pause button
        pause_btn = page.locator("#physics-pause-btn")
        pause_btn.click()
        time.sleep(0.3)

        paused_state = page.evaluate(
            "() => ({ paused: isPhysicsPaused, text: document.getElementById('pause-btn-text').innerText })"
        )
        print(f"After Pause click -> Paused: {paused_state['paused']}, Button text: {paused_state['text']}")
        assert paused_state["paused"] is True, "Physics should be paused after clicking Pause"
        assert paused_state["text"].upper() == "RESUME", f"Button should say Resume, got {paused_state['text']}"

        # In paused state, node positions are completely static
        p_paused1 = page.evaluate("() => cy.nodes().map(n => ({ id: n.id(), x: n.position('x'), y: n.position('y') }))")
        time.sleep(1.0)
        p_paused2 = page.evaluate("() => cy.nodes().map(n => ({ id: n.id(), x: n.position('x'), y: n.position('y') }))")
        paused_drift = max(abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]) for a, b in zip(p_paused1, p_paused2))
        print(f"Drift during Paused state over 1s: {paused_drift:.6f}px")
        assert paused_drift < 0.001, f"Nodes drifted while paused: {paused_drift}px"

        # 4. Turn physics back ON via Resume button
        pause_btn.click()
        time.sleep(0.3)

        resumed_state = page.evaluate(
            "() => ({ paused: isPhysicsPaused, text: document.getElementById('pause-btn-text').innerText })"
        )
        print(f"After Resume click -> Paused: {resumed_state['paused']}, Button text: {resumed_state['text']}")
        assert resumed_state["paused"] is False, "Physics should be active after clicking Resume"
        assert resumed_state["text"].upper() == "PAUSE", f"Button should say Pause, got {resumed_state['text']}"

        # 5. Verify physics continues running indefinitely
        time.sleep(1.0)
        final_state = page.evaluate("() => ({ jiggle: !!jiggleLoopId, paused: isPhysicsPaused })")
        print(f"Final check -> Physics actively simulating: {final_state['jiggle']}, Paused: {final_state['paused']}")
        assert final_state["jiggle"] is True
        assert final_state["paused"] is False

        browser.close()
