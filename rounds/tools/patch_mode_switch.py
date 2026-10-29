"""The node has to be in the right mode before it takes a job.

The 3090 machine shares its cards between the LLM service and ComfyUI, one
at a time: the run mode is just the two containers being up or down. The
pipeline therefore tells the node to switch before the video phase, and to
switch back when it is done.
"""
from pathlib import Path

# 1) the config: the commands that put the node in the right mode
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    # This node's own weights: {"6": {"unet_name": "..."}} - the loader
    # nodes of the workflow. The 5080 takes the nvfp4 files, the 3090 the
    # int8/convrot ones.
    graph_overrides: dict = Field(default_factory=dict)"""
new = """    # This node's own weights: {"6": {"unet_name": "..."}} - the loader
    # nodes of the workflow. The 5080 takes the nvfp4 files, the 3090 the
    # int8/convrot ones.
    graph_overrides: dict = Field(default_factory=dict)
    # Shell commands run on the node before it takes a job, and after it is
    # done: the machine shares its cards between the LLM service and
    # ComfyUI, so one has to give way to the other.
    prepare: list[str] = Field(default_factory=list)
    restore: list[str] = Field(default_factory=list)"""
assert old in s, "config 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py 已改（模式切换命令）")

# 2) the pool: run them over ssh
p = Path(r"E:\\dramakit\\dramakit\\providers\\pool.py")
s = p.read_text(encoding="utf-8")
old = """    # ---------------------------------------------------------------- health
    def health(self) -> list[dict]:"""
new = '''    # ------------------------------------------------------------- run mode
    def prepare(self, role: str) -> None:
        """Put the nodes that need it into the right mode."""
        for node in self.nodes:
            cmds = list(getattr(node.spec, "prepare", None) or [])
            if not cmds:
                continue
            log.info("节点 %s 切到工作模式", node.name)
            self._run_remote(node, cmds)

    def restore(self, role: str) -> None:
        """Give the machine back to whatever it was doing before."""
        for node in self.nodes:
            cmds = list(getattr(node.spec, "restore", None) or [])
            if not cmds:
                continue
            log.info("节点 %s 切回原来的模式", node.name)
            self._run_remote(node, cmds)

    @staticmethod
    def _run_remote(node, cmds: list[str]) -> None:
        import subprocess
        from .nodes import _ssh_base
        spec = node.spec
        if not spec.ssh_host or not spec.ssh_user:
            return
        for c in cmds:
            try:
                r = subprocess.run(
                    _ssh_base(spec) + [f"{spec.ssh_user}@{spec.ssh_host}", c],
                    capture_output=True, text=True, timeout=600)
                if r.returncode:
                    log.warning("节点 %s 执行 `%s` 失败: %s", node.name, c,
                                (r.stderr or "")[-200:])
                else:
                    log.info("节点 %s: %s", node.name, (r.stdout or "").strip()[-160:])
            except Exception as e:  # noqa: BLE001
                log.warning("节点 %s 执行 `%s` 出错: %s", node.name, c, str(e)[:160])

    # ---------------------------------------------------------------- health
    def health(self) -> list[dict]:'''
assert old in s, "pool 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("pool.py 已改（模式切换）")
