"""Finding the config should not be something each caller reimplements.

Config.load(None) returns the code's own defaults - Ollama on localhost,
for instance - and says nothing about it. The search for the real file
lived in cli._find_config, so a script that wanted the settings the
console uses had to know that, and one that did not know called Config()
and quietly got defaults pointing at services that are not running. That
is how a diagnostic got "connection refused" from a model that was
reachable the whole time.

So the search is a method on Config: an explicit path, the working
directory's config, then the repository's own copy. cli keeps one list of
candidates rather than a second copy of it.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8", errors="replace")

if "def discover(" in s:
    print("config.py: 已有 discover，跳过")
    raise SystemExit(0)

old_load = '''    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        """Load YAML config (deep-merged over defaults). Missing file => defaults.

        Keys whose value is null (e.g. a dict with only commented-out entries)
        are dropped so the model defaults apply instead of failing validation.
        """
        data: dict = {}
        if path and Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        return cls(**_drop_nulls(data))'''

new_load = '''    # where the config file lives, in the order worth trying
    CANDIDATES = ("config/default.yaml", "default.yaml",
                  Path(__file__).resolve().parent.parent / "config" / "default.yaml")

    @classmethod
    def discover(cls, path: str | Path | None = None) -> Optional[Path]:
        """The config file to read: an explicit path, then the usual places.

        Returns None when there is none, which is a real answer - the code
        defaults are then in force, and they are defaults rather than the
        project's settings.
        """
        for cand in ([Path(path)] if path else []) + \
                [Path(c) if not isinstance(c, Path) else c for c in cls.CANDIDATES]:
            try:
                if cand.exists():
                    return cand
            except OSError:  # a path that cannot be stat'd is not the config
                continue
        return None

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        """Load YAML config (deep-merged over defaults). Missing file => defaults.

        Keys whose value is null (e.g. a dict with only commented-out entries)
        are dropped so the model defaults apply instead of failing validation.

        Called with no path this returns the code's defaults, not the
        project's settings; use discover() to find the file first, or
        load(cls.discover()) to get what the console is actually using.
        """
        data: dict = {}
        if path and Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        return cls(**_drop_nulls(data))'''

assert old_load in s, "Config.load 锚点没找到"
s = s.replace(old_load, new_load, 1)

p.write_text(s, encoding="utf-8")
print("config.py: 加了 Config.discover()，配置文件搜索有了唯一一份")
