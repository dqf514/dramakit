"""A re-analysis must not erase what the project already made.

Three things went wrong together, and the third is the one that costs.

The analysis had no skip guard, so a resume re-ran it - and it read the
same three chapters, so it could only produce a slightly different cast.
The merge that follows builds new characters carrying voice and role and
nothing else: the voice samples recorded at 定妆, the reference pictures
already drawn, the anchor that keeps a face the same, all dropped from the
model while the files sat on disk. A later stage then saw characters with
no pictures and drew them again - into a folder for the wrong season,
because pointing at a season that already owns these chapters was not
something seed_season thought to do.

So the analysis skips when it has already run for this season; the merge
carries everything that was already decided; and a season is chosen by
what owns the chapters, not by whichever number is next. A character that
the analysis no longer mentions keeps its history too - a scene it does
not appear in is not a reason for it to stop existing.
"""
from pathlib import Path

# ---------------------------------------- 1. analyze knows it has run ----
a = Path(r"E:\\dramakit\\dramakit\\pipeline\\analyze.py")
s = a.read_text(encoding="utf-8")

old_head = '''def run(ctx: Context) -> dict:
    season = ctx.seed_season(ctx.season_chapters()
                             or list(ctx.project.meta.chosen_chapters or []))
    text, chapters = _season_text(ctx)'''
new_head = '''def run(ctx: Context) -> dict:
    season = ctx.seed_season(ctx.season_chapters()
                             or list(ctx.project.meta.chosen_chapters or []))
    # A resume must not read the same chapters again. The analysis is the
    # one stage whose output is a decision - who is in the cast, what they
    # look like - and running it twice on the same pages is a second
    # opinion nobody asked for, which then overwrites the first.
    if season is not None and season.stage_status.get("analyze") == "done" \\
            and (ctx.project.characters or ctx.project.locations):
        ctx.log.info("analyze: 第%d季已分析过，跳过（%d 角色）",
                     season.index, len(ctx.project.characters))
        return {"skipped": True, "season": season.index,
                "characters": len(ctx.project.characters),
                "locations": len(ctx.project.locations)}
    text, chapters = _season_text(ctx)'''
assert old_head in s, "analyze.run 锚点没找到"
s = s.replace(old_head, new_head, 1)
a.write_text(s, encoding="utf-8")
print("analyze.py: 已分析过的季不再重跑")

# --------------------------------- 2. the merge keeps what was decided ---
old_keep = '''        old = prev.get(name)
        if old is not None:
            # voice and identity are what make them the same person
            c.voice_id = old.voice_id
            c.voice_pitch = old.voice_pitch
            c.voice_rate = old.voice_rate
            if not c.role or c.role == "配角":
                c.role = old.role
            if old.locked:
                # a locked look is not analysis's to change
                c.locked = True
                apply_look(c, {k: getattr(old, k) for k in LOOK_FIELDS})
        else:'''
new_keep = '''        old = prev.get(name)
        if old is not None:
            # Voice and identity are what make them the same person, and
            # so is everything already decided about them: the recording
            # made at 定妆, the pictures already drawn, the anchor that
            # keeps the face the same. The files stay on disk either way,
            # but a field left empty makes the next stage see a character
            # with no pictures and draw them again.
            c.voice_id = old.voice_id
            c.voice_pitch = old.voice_pitch
            c.voice_rate = old.voice_rate
            c.voice_ref = old.voice_ref
            c.ref_images = list(old.ref_images or [])
            c.ref_sheet = old.ref_sheet
            c.ref_image = old.ref_image
            c.anchor_prompt = old.anchor_prompt
            c.negative_prompt = old.negative_prompt
            c.consistency = old.consistency
            c.lora = old.lora
            c.locked = old.locked
            if not c.role or c.role == "配角":
                c.role = old.role
            if not c.appearance:
                c.appearance = old.appearance
            if not c.visual_prompt:
                c.visual_prompt = old.visual_prompt
        else:'''
assert old_keep in s, "_merge_characters 的合并块锚点没找到"
s = s.replace(old_keep, new_keep, 1)
a.write_text(s, encoding="utf-8")
print("analyze.py: 合并保留声音/参考图/锚点/锁定")

# ------------------------- 3. a known character stays in the cast --------
old_tail = '''        else:
            # a name the canon knows but this season's pages did not return
            c.voice_id = canon.voices.get(name, "")
        out.append(c)
    return out'''
new_tail = '''        else:
            # a name the canon knows but this season's pages did not return
            c.voice_id = canon.voices.get(name, "")
        out.append(c)

    # A character the analysis no longer mentions is still in the story.
    # The pages this season read may not have reached them, and dropping
    # them would take their voice, their pictures and their anchor with
    # them - the next stage would then draw the same person again.
    for name, old in prev.items():
        if any(c.name == name for c in out):
            continue
        out.append(old)
        ctx.log.info("analyze: %s 这季没出现，保留其设定", name)
    return out'''
assert old_tail in s, "_merge_characters 的结尾锚点没找到"
s = s.replace(old_tail, new_tail, 1)
a.write_text(s, encoding="utf-8")
print("analyze.py: 没出现的角色保留")

# --------------------- 4. a season is chosen by what owns the chapters ---
b = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
t = b.read_text(encoding="utf-8")
old_seed = '''        # A stage asking to build a season but not pointed at one means
        # the next season: that is what the book is waiting for.
        if not self.season_index:
            self.use_season(self.project.current_season)'''
new_seed = '''        # A stage asking about a season but not pointed at one means the
        # season that already owns these chapters - a resume continues the
        # season it started, and only an untouched book begins the next.
        if not self.season_index:
            want = set(chapters or [])
            for existing in (self.project.seasons or []):
                if want and want <= set(existing.chapters or []):
                    self.use_season(existing.index)
                    break
            else:
                self.use_season(self.project.current_season)'''
assert old_seed in t, "seed_season 锚点没找到"
b.write_text(t.replace(old_seed, new_seed, 1), encoding="utf-8")
print("base.py: 按已拥有这些章的季来选，不跳到下一季")
