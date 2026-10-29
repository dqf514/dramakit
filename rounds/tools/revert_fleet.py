"""Undo the duplicate pool: the codebase already has one."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\providers\\comfyui.py")
s = p.read_text(encoding="utf-8")

if "class FleetVisual(BaseImageVideo):" in s:
    i = s.index("class FleetVisual(BaseImageVideo):")
    j = s.index("def build_visual(cfg: ComfyUIConfig")
    s = s[:i] + s[j:]

old = '''def build_visual(cfg: ComfyUIConfig, root: Optional[Path] = None) -> Optional[BaseImageVideo]:
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
new = '''def build_visual(cfg: ComfyUIConfig, root: Optional[Path] = None) -> Optional[BaseImageVideo]:
    if not cfg.enabled:
        return None
    return ComfyUIClient(cfg, root)'''
if old in s:
    s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("已撤掉重复的节点池实现")
