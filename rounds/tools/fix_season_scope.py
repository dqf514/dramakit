"""A whole-project run must not be scoped to a season that does not exist.

Context took season_index from current_season, which is one past the last
season on record - the season the next run would begin. So a project that
had ever had a season filtered every episode by a season number nobody
was in: target_episodes() came back empty, the script stage walked nothing,
and the run reported success in five seconds over a hundred and fifty
episodes. A stage that does nothing and says it is done is worse than one
that fails, because it wastes the day before anyone notices.

A season is now something a run opts into. use_season() points at one,
and only then are episodes filtered by it; a plain run sees every
episode, which is what it always meant. seed_season() still begins the
next season when a stage asks to build one.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
s = p.read_text(encoding="utf-8")

if "self.season_scoped" in s:
    print("base.py: 已修正，跳过")
    raise SystemExit(0)

# 1. the default is "not scoped", and scoping is a decision
old_init = '''        # the season being made.  Every stage works on this season's
        # chapters and episodes only - a long book is produced a season at
        # a time, and a rerun of season 3 must not touch season 1.
        self.season_index: int = self.project.current_season'''
new_init = '''        # The season being made, if a run is making one. Zero means none:
        # a plain run is not scoped to a season, and filtering its episodes
        # by the next season number - which is what current_season is - would
        # leave it with nothing to do while reporting success.
        self.season_index: int = 0
        self.season_scoped: bool = False'''
assert old_init in s, "Context.__init__ 锚点没找到"
s = s.replace(old_init, new_init, 1)

# 2. pointing at a season is what scopes the run
old_use = '''    def use_season(self, index: int) -> None:'''
new_use = '''    def use_season(self, index: int) -> None:
        """Work on one season: its chapters, its episodes, its looks."""'''
assert old_use in s, "use_season 锚点没找到"
s = s.replace(old_use, new_use, 1)

old_body = '''        self.season_index = index'''
new_body = '''        self.season_index = index
        self.season_scoped = bool(index)'''
assert old_body in s, "use_season 的赋值锚点没找到"
s = s.replace(old_body, new_body, 1)

# 3. only a scoped run filters its episodes
old_filter = '''        eps = self.project.episodes
        if self.season_index:
            eps = [e for e in eps if getattr(e, "season", 1) == self.season_index]'''
new_filter = '''        eps = self.project.episodes
        if self.season_scoped and self.season_index:
            eps = [e for e in eps if getattr(e, "season", 1) == self.season_index]'''
assert old_filter in s, "target_episodes 过滤锚点没找到"
s = s.replace(old_filter, new_filter, 1)

# 4. a stage that asks to begin a season gets the next one, not zero
old_seed = '''    def seed_season(self, chapters: list[int]) -> "Season":
        """Create this season if it does not exist yet, claiming chapters."""
        s = self.season'''
new_seed = '''    def seed_season(self, chapters: list[int]) -> "Season":
        """Create this season if it does not exist yet, claiming chapters."""
        # A stage asking to build a season but not pointed at one means
        # the next season: that is what the book is waiting for.
        if not self.season_index:
            self.use_season(self.project.current_season)
        s = self.season'''
assert old_seed in s, "seed_season 锚点没找到"
s = s.replace(old_seed, new_seed, 1)

p.write_text(s, encoding="utf-8")
print("base.py: 整项目跑不再被过滤成空，只有明确指定季才按季过滤")
