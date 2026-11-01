"""Does the console know about seasons?

The pipeline now builds a project one season at a time, so the console has
to show that: which chapters each season took, what each produced, and
where the next one should start. This checks the server route and the
page for the wiring, without launching either.
"""
from pathlib import Path

srv = Path(r"E:\dramakit\dramakit\web\server.py").read_text(encoding="utf-8")
htm = Path(r"E:\dramakit\dramakit\web\static\index.html").read_text(encoding="utf-8")

print("=== server ===")
for probe in ('"/api/seasons"', "_api_seasons", '"season": body.get',
              "next_chapter", "chapters_done", "current_season"):
    print(f"  {probe:<24} {probe in srv}")

print()
print("=== page ===")
for probe in ("api/seasons", "season", "canon", "chapterSeason",
              "第几季", "seasonCard", "loadSeasons"):
    print(f"  {probe:<24} {htm in htm and probe in htm}  ({htm.count(probe)})")
