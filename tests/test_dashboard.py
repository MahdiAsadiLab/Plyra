"""Opens the generated HTML report in a real headless browser (Chromium via Playwright).

Skipped automatically when Playwright or its browser is not installed.
To enable:  pip install playwright   then   playwright install chromium
"""

import json
import re
import tempfile
import unittest
from pathlib import Path

from helpers import scholars_mate_game  # also sets up sys.path

from models import summarize
from reports import build_html

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as _p:
        _p.chromium.launch().close()
    HAVE_BROWSER = True
except Exception:  # not installed, or no browser downloaded
    HAVE_BROWSER = False

SCREENSHOT = None  # set to a path to save a screenshot while testing


@unittest.skipUnless(HAVE_BROWSER, "Playwright/Chromium is not available")
class DashboardBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        info, results = scholars_mate_game()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "report.html"
        cls.path.write_text(build_html(info, results, summarize(results)), encoding="utf-8")
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.tmp.cleanup()

    def open_page(self, width=1400, height=1000, javascript=True):
        context = self.browser.new_context(viewport={"width": width, "height": height}, java_script_enabled=javascript)
        page = context.new_page()
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)
        page.on("request", lambda r: self.errors.append("network request: " + r.url) if not r.url.startswith("file:") else None)
        page.goto(self.path.as_uri())
        return page

    def test_starts_without_errors_and_draws_a_board(self):
        page = self.open_page()
        self.assertEqual(page.get_attribute("html", "data-chesslens"), "ready")
        self.assertEqual(page.locator("#board .sq").count(), 64)
        self.assertEqual(page.locator("#board .piece").count(), 32)   # starting position
        self.assertEqual(self.errors, [])

    def test_clicking_a_move_updates_board_details_and_list(self):
        page = self.open_page()
        page.click("tr.mv[data-ply='4']")      # 2... Nc6
        self.assertIn("After Move 2... Nc6", page.inner_text("#board-caption"))
        self.assertTrue(page.locator("[data-square='c6'] .piece").count() == 1)
        self.assertEqual(page.locator("[data-square='b8'] .piece").count(), 0)
        self.assertEqual(page.locator("#board .sq.hl").count(), 2)       # played move highlighted
        self.assertIn("Nc6", page.inner_text("#details-body"))
        self.assertIn("Why this label", page.inner_text("#details-body"))
        self.assertEqual(page.locator("tr.mv.sel").count(), 1)

    def test_keyboard_navigation_and_buttons(self):
        page = self.open_page()
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        self.assertIn("Move 1... e5", page.inner_text("#board-caption"))
        page.keyboard.press("ArrowLeft")
        self.assertIn("Move 1 e4", page.inner_text("#board-caption"))
        page.click("#btn-last")
        self.assertIn("Qxf7#", page.inner_text("#board-caption"))
        page.click("#btn-first")
        self.assertIn("Starting position", page.inner_text("#board-caption"))
        self.assertEqual(self.errors, [])

    def test_before_mode_shows_the_best_move_arrow(self):
        page = self.open_page()
        page.click("tr.mv[data-ply='2']")      # 1... e5, engine preferred c5
        page.click("#btn-mode")
        self.assertIn("Before", page.inner_text("#board-caption"))
        self.assertEqual(page.locator("#arrows line").count(), 2)       # played (dashed) + best
        self.assertEqual(page.locator("#board .sq.hl").count(), 0)
        page.click("tr.mv[data-ply='1']")      # played == best: only one arrow
        self.assertEqual(page.locator("#arrows line").count(), 1)

    def test_flip_changes_orientation_without_changing_the_position(self):
        page = self.open_page()
        page.click("tr.mv[data-ply='3']")
        first_before = page.locator("#board .sq").first.get_attribute("data-square")
        piece_before = page.locator("[data-square='c4'] .piece").count()
        page.click("#btn-flip")
        self.assertEqual(first_before, "a8")
        self.assertEqual(page.locator("#board .sq").first.get_attribute("data-square"), "h1")
        self.assertEqual(page.locator("[data-square='c4'] .piece").count(), piece_before)

    def test_filters_keep_the_selection(self):
        page = self.open_page()
        page.click("tr.mv[data-ply='4']")
        page.select_option("#filter-side", "White")
        self.assertEqual(page.locator("tr.mv:not(.hidden)").count(), 4)
        self.assertEqual(page.locator("tr.mv.sel").count(), 1)           # the selected Black move is still selected
        self.assertIn("After Move 2... Nc6", page.inner_text("#board-caption"))
        page.select_option("#filter-side", "both")
        page.click("#filter-errors")
        shown = page.locator("tr.mv:not(.hidden)").count()
        self.assertLess(shown, 7)
        page.click("#filter-errors")
        page.select_option("#filter-label", "Blunder")
        self.assertEqual(page.locator("tr.mv:not(.hidden)").count(), page.locator("tr.mv").filter(has_text="Blunder").count())

    def test_graph_click_selects_a_move(self):
        page = self.open_page()
        box = page.locator("#graph").bounding_box()
        page.mouse.click(box["x"] + box["width"] * 0.95, box["y"] + box["height"] * 0.5)
        self.assertIn("Qxf7#", page.inner_text("#board-caption"))
        self.assertEqual(page.locator("#graph-cursor").evaluate("e => getComputedStyle(e).display"), "block")

    def test_works_on_a_phone_sized_screen(self):
        page = self.open_page(width=390, height=844)
        self.assertEqual(page.get_attribute("html", "data-chesslens"), "ready")
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        self.assertLessEqual(overflow, 1)                                  # no sideways scrolling
        page.click("tr.mv[data-ply='5']")
        self.assertIn("Qh5", page.inner_text("#board-caption"))

    def test_without_javascript_the_static_parts_still_work(self):
        page = self.open_page(javascript=False)
        self.assertTrue(page.locator("#board-fallback").is_visible())
        self.assertEqual(page.locator("tr.mv").count(), 7)
        self.assertTrue(page.locator("#graph").is_visible())
        self.assertIn("White accuracy", page.inner_text("body"))

    def test_html_in_data_is_not_executed(self):
        info, results = scholars_mate_game()
        info.headers["White"] = "<img src=x onerror=window.pwned=1>"
        results[0].annotations.append("</script><script>window.pwned=1</script>")
        results[0].explanation.append("<b onmouseover=window.pwned=1>x</b>")
        path = Path(self.tmp.name) / "evil.html"
        path.write_text(build_html(info, results, summarize(results)), encoding="utf-8")
        context = self.browser.new_context()
        page = context.new_page()
        page.goto(path.as_uri())
        page.click("tr.mv[data-ply='1']")
        self.assertIsNone(page.evaluate("window.pwned"))
        self.assertEqual(page.get_attribute("html", "data-chesslens"), "ready")
        self.assertIn("<img src=x onerror=window.pwned=1>", page.inner_text("h1"))  # shown as text
        self.assertIn("</script><script>", page.inner_text("#details-body"))

    def test_long_game_stays_usable(self):
        from helpers import cp, make_result
        info, _ = scholars_mate_game()
        results = [make_result(cp(30), color="White" if i % 2 == 0 else "Black", move_number=i // 2 + 1, ply=i + 1,
                               fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                               fen_after="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
                   for i in range(240)]
        path = Path(self.tmp.name) / "long.html"
        path.write_text(build_html(info, results, summarize(results)), encoding="utf-8")
        context = self.browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        page.goto(path.as_uri())
        self.assertEqual(page.locator("tr.mv").count(), 240)
        page.click("#btn-last")
        self.assertEqual(page.locator("tr.mv.sel").count(), 1)
        self.assertEqual(page.get_attribute("html", "data-chesslens"), "ready")

    def test_screenshot_for_review(self):
        page = self.open_page()
        page.click("tr.mv[data-ply='6']")
        page.click("#btn-mode")
        out = Path("/tmp/chesslens_dashboard.png")
        if out.parent.exists():
            page.screenshot(path=str(out), full_page=True)
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
