"""Two lanes write the same project, so writing it has to be one at a time.

The stages are going to overlap: the machine that writes prompts and the
machine that draws pictures will both be finishing work and both will want
to save. save() writes a file by writing a temporary one and renaming it,
and two threads doing that at once is how a project.json ends up as a
half-written mix of both lanes' state.

The lock is on the write, not on the work. Lanes still run together; only
the moment the file changes is serialised, which is the moment that has to
be.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
s = p.read_text(encoding="utf-8")

if "_save_lock" in s:
    print("base.py: 保存锁已存在，跳过")
    raise SystemExit(0)

old_init = '''        # set when someone asks the run to stop. Stages that loop over
        # many episodes or many calls ask between items, so a stop lands
        # in seconds rather than at the end of the batch.
        self._stop = None'''
new_init = '''        # set when someone asks the run to stop. Stages that loop over
        # many episodes or many calls ask between items, so a stop lands
        # in seconds rather than at the end of the batch.
        self._stop = None
        # Two lanes write the project - the one that writes prompts and
        # the one that draws - and save() replaces the file by renaming a
        # temporary one over it. Two threads doing that at once is how a
        # project.json becomes a half-written mix of both.
        self._save_lock = threading.Lock()'''
assert old_init in s, "Context.__init__ 锚点没找到"
s = s.replace(old_init, new_init, 1)

old_save = '''    def save(self) -> None:
        self.store.save(self.project)'''
new_save = '''    def save(self) -> None:
        # serialised on the write, not on the work: the lanes still run
        # together, only the moment the file changes takes turns
        with self._save_lock:
            self.store.save(self.project)'''
assert old_save in s, "save 锚点没找到"
s = s.replace(old_save, new_save, 1)

# threading is needed
if "\nimport threading" not in s:
    s = s.replace("import logging\n", "import logging\nimport threading\n", 1)

p.write_text(s, encoding="utf-8")
print("base.py: save() 加了锁，两条道可以同时写")
