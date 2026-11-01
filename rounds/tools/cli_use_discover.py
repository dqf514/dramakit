"""One list of places to look for the config.

cli._find_config held the candidate paths, and Config held the defaults
they lead to - so a script that wanted the console's settings had to know
about a private helper in another module, and one that did not got the
code defaults without being told. The search now lives on Config, and the
CLI asks it rather than keeping a second copy.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\cli.py")
s = p.read_text(encoding="utf-8", errors="replace")

old = '''def _find_config(path: Optional[str]) -> Optional[Path]:
    cands = []
    if path:
        cands.append(Path(path))
    cands += [Path(DEFAULT_CONFIG), Path("default.yaml"),
              Path(__file__).parent.parent / DEFAULT_CONFIG]
    for c in cands:
        if c.exists():
            return c
    return None'''

new = '''def _find_config(path: Optional[str]) -> Optional[Path]:
    # Config owns the list of places to look: the CLI and any script both
    # want the same file, and a second copy of the candidates is a second
    # thing to keep in step
    return Config.discover(path)'''

assert old in s, "_find_config 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("cli.py: _find_config 改为委托 Config.discover()")
