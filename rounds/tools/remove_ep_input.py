"""The episode-count field goes: the system already knows how many episodes.

The field was written to the project and never read by anything - segment
sizes the episodes from the text itself.  So the question was noise that
made the user do arithmetic the machine had already done.  It is gone, and
the button says what it actually does.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

old = """         <span class="grow"></span>
         <label class="mini muted">生成</label>
         <input type="number" id="epWanted" value="1" min="1" max="50"
                style="width:52px" title="生成几集">
         <label class="mini muted">集</label>
       </div>
       <button class="btn go" style="width:100%;margin-bottom:6px"
               onclick="chooseChapters()">按选中章节开始</button>"""

new = """         <span class="grow"></span>
         <span class="mini muted" id="epWantedNote">集数由系统按时长自动分</span>
       </div>
       <button class="btn go" style="width:100%;margin-bottom:6px"
               onclick="chooseChapters()">▶ 开始制作选中的章节</button>"""

assert old in s, "章节卡锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("index.html: 去掉了集数输入，按钮改成「▶ 开始制作选中的章节」")
