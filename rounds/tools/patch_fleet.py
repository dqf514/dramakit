"""Spread the shots over the machines.

One ComfyUI uses one card. The fleet has several, each with its own
cards, and the shots are handed out to them round by round - so a node
that is only good at video never gets the stills, and two nodes make the
episode twice as fast.

The role of a node comes from the configuration: "t2i", "i2v", or empty
for anything.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\providers\\comfyui.py")
s = p.read_text(encoding="utf-8")

old = """def build_visual(cfg: ComfyUIConfig, root: Optional[Path] = None) -> Optional[BaseImageVideo]:
    if not cfg.enabled:
        return None
    return ComfyUIClient(cfg, root)"""
new = '''class FleetVisual(BaseImageVideo):
    """Several ComfyUI servers, one job at a time.

    The jobs are handed to the nodes that can do them, in turn. A node
    that is down is skipped, so the episode still goes through with
    whatever is up.
    """

    def __init__(self, members: list[tuple[BaseImageVideo, list[str], str]]):
        # (client, roles, name)
        self.members = members
        self._turn = 0

    def _pick(self, role: str) -> Optional[BaseImageVideo]:
        n = len(self.members)
        for i in range(n):
            client, roles, name = self.members[(self._turn + i) % n]
            if roles and role not in roles:
                continue
            if not client.ping():
                continue
            self._turn = (self._turn + i + 1) % n
            log.info("节点 %s 接下 %s 的活", name, role)
            return client
        return None

    def ping(self) -> bool:
        """True when at least one node answers."""
        for client, _roles, _name in self.members:
            try:
                if client.ping():
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    def generate_image(self, prompt: str, negative: str, **kw) -> str:
        client = self._pick("t2i")
        if client is None:
            raise ComfyUIError("没有可用的出图节点")
        return client.generate_image(prompt, negative, **kw)

    def generate_video(self, prompt: str, negative: str, **kw) -> str:
        client = self._pick("i2v")
        if client is None:
            raise ComfyUIError("没有可用的视频节点")
        return client.generate_video(prompt, negative, **kw)

    def upload_image(self, path) -> str:
        client = self._pick("t2i") or self.members[0][0]
        return client.upload_image(path)

    def upload_audio(self, path) -> str:
        client = self._pick("i2v") or self.members[0][0]
        return client.upload_audio(path)


def build_visual(cfg: ComfyUIConfig, root: Optional[Path] = None) -> Optional[BaseImageVideo]:
    """The visual provider: the local machine plus every configured node."""
    if not cfg.enabled:
        return None
    primary = ComfyUIClient(cfg, root)
    members: list[tuple[BaseImageVideo, list[str], str]] = [(primary, [], "local")]
    for spec in getattr(cfg, "nodes", None) or []:
        if not spec.enabled:
            continue
        node_cfg = cfg.model_copy(deep=True)
        node_cfg.base_url = spec.base_url
        node_cfg.auth = spec.auth
        node_cfg.auth_username = spec.auth_username
        node_cfg.auth_password = spec.auth_password
        node_cfg.auth_token = spec.auth_token
        node_cfg.extra_headers = dict(spec.extra_headers or {})
        node_cfg.verify_tls = spec.verify_tls
        members.append((ComfyUIClient(node_cfg, root), list(spec.roles or []),
                        spec.name))
    if len(members) == 1:
        return primary
    log.info("节点池: %s", ", ".join(f"{m[2]}{m[1] or ''}" for m in members))
    return FleetVisual(members)'''
assert old in s, "build_visual 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("comfyui.py 已改（节点池调度）")
