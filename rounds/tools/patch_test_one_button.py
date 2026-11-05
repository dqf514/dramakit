"""Rewrite the chapter-card test for the one-button workbench.

There were four ways to start the work and one of them only ticked the
steps off.  There is one button now, and the chapter list is a scope
switch instead of two more buttons.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\tests\test_maturity.py")
text = PATH.read_text(encoding="utf-8")

old_start = "    def test_chapter_card_offers_both_scopes_and_they_reach_the_api(self):"
old_end = "    def test_every_page_is_reachable_and_the_bottom_bar_stays_short(self):"
i = text.index(old_start)
j = text.index(old_end)

new = '''    def test_one_button_starts_the_work_and_the_scope_says_what_it_is(self):
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        # There were four ways to start, and one of them only ticked the
        # steps off.  There is one button now, and it runs the steps that
        # are picked.
        self.assertIn('id="runGo"', text)
        self.assertNotIn('data-act="run-all"', text)
        self.assertNotIn('data-chap="season"', text)
        self.assertNotIn('data-chap="script"', text)
        self.assertNotIn("async function chooseChapters(", text)
        self.assertNotIn("async function startSeason(", text)
        # the chapters are the scope of the run, and the switch says which
        self.assertIn('id="chapScope"', text)
        self.assertIn("body.chapters=chosen", text)
        self.assertIn("body.season=window.__nextSeason||1", text)
        # and the button next to it says what the run is about
        self.assertIn("function drawChapScope()", text)
        self.assertIn('id="runScope"', text)
        # the tick list still has its helpers
        self.assertIn('data-chap="mode"', text)
        self.assertIn('else if(a==="mode") toggleChapMode();', text)
        self.assertIn('data-chap="all"', text)
        self.assertIn('data-chap="none"', text)

'''

PATH.write_text(text[:i] + new + text[j:], encoding="utf-8")
print("测试改好了")
