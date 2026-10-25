"""ComfyUI node fleet: health check and model sync.

A node is any ComfyUI server that can render for us. Every node needs the
same model files our workflows reference, so the workflows double as the
manifest: scanning them for loader nodes tells us exactly which files to ship.

    dj nodes              list the fleet with health and missing models
    dj nodes check        self-check: connectivity / version / vram / models
    dj nodes sync NAME    copy the missing models over, with progress
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import httpx

from ..config import NodeConfig

# loader node class -> (models subfolder, input parameter)
MODEL_LOADERS: dict[str, tuple[str, str]] = {
    "CheckpointLoaderSimple": ("checkpoints", "ckpt_name"),
    "CheckpointLoader": ("checkpoints", "ckpt_name"),
    "UNETLoader": ("diffusion_models", "unet_name"),
    "CLIPLoader": ("text_encoders", "clip_name"),
    "CLIPVisionLoader": ("clip_vision", "clip_name"),
    "VAELoader": ("vae", "vae_name"),
    "LoraLoader": ("loras", "lora_name"),
    "LoraLoaderModelOnly": ("loras", "lora_name"),
    "AudioEncoderLoader": ("audio_encoders", "encoder_name"),
    "IPAdapterModelLoader": ("ipadapter", "model_name"),
}


@dataclass(frozen=True)
class ModelRef:
    """One model file a workflow needs."""
    folder: str
    filename: str
    path: Path

    @property
    def size(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    @property
    def rel(self) -> str:
        return f"{self.folder}/{self.filename}"


def workflow_models(workflows: list[str], root: Path,
                    models_root: Optional[Path] = None) -> list[ModelRef]:
    """Model files referenced by the given workflows (the manifest).

    The workflow JSON is the source of truth: any loader node pointing at
    "foo.safetensors" means that file has to exist on every rendering node.
    models_root is where the files live locally (the ComfyUI models dir).
    """
    mroot = models_root or (root / "models")
    out: list[ModelRef] = []
    seen: set[str] = set()
    for rel in workflows:
        if not rel:
            continue
        path = (root / rel)
        if not path.exists():
            continue
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for node in graph.values():
            if not isinstance(node, dict):
                continue
            spec = MODEL_LOADERS.get(str(node.get("class_type", "")))
            if not spec:
                continue
            folder, param = spec
            name = str((node.get("inputs") or {}).get(param) or "")
            if not name or name in seen:
                continue
            seen.add(name)
            out.append(ModelRef(folder=folder, filename=name,
                               path=mroot / folder / name))
    return out


@dataclass
class NodeHealth:
    """Self-check result for one node."""
    name: str
    base_url: str
    online: bool = False
    version: str = ""
    device: str = ""
    vram_total: int = 0
    vram_used: int = 0
    missing: list[str] = field(default_factory=list)
    installed: int = 0
    error: str = ""

    @property
    def vram_free(self) -> int:
        return max(0, self.vram_total - self.vram_used)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "base_url": self.base_url, "online": self.online,
            "version": self.version, "device": self.device,
            "vram_total": self.vram_total, "vram_used": self.vram_used,
            "vram_free": self.vram_free, "missing": list(self.missing),
            "installed": self.installed, "error": self.error,
        }


class NodeClient:
    """Minimal client for one ComfyUI server."""

    def __init__(self, spec: NodeConfig):
        self.spec = spec
        self.base = spec.base_url.rstrip("/")

    def _headers(self) -> dict:
        h = dict(self.spec.extra_headers or {})
        if self.spec.auth == "bearer" and self.spec.auth_token:
            h["Authorization"] = f"Bearer {self.spec.auth_token}"
        elif self.spec.auth == "basic" and self.spec.auth_username:
            import base64
            raw = f"{self.spec.auth_username}:{self.spec.auth_password}".encode()
            h["Authorization"] = "Basic " + base64.b64encode(raw).decode()
        return h

    def _get(self, path: str, timeout: float = 15.0):
        url = self.base + path
        with httpx.Client(timeout=timeout, trust_env=False, verify=self.spec.verify_tls) as c:
            return c.get(url, headers=self._headers())

    def ping(self) -> bool:
        try:
            return self._get("/system_stats", timeout=10).status_code == 200
        except Exception:  # noqa: BLE001
            return False

    def stats(self) -> dict:
        try:
            r = self._get("/system_stats", timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)[:200]}

    def installed_models(self) -> dict[str, set[str]]:
        """Files the node can load, per models subfolder.

        Read from the loader node combos in /object_info, so it reflects what
        ComfyUI itself can see.
        """
        try:
            r = self._get("/object_info", timeout=60)
            r.raise_for_status()
            info = r.json()
        except Exception:  # noqa: BLE001
            return {}
        out: dict[str, set[str]] = {}
        for cls, (folder, param) in MODEL_LOADERS.items():
            node = info.get(cls)
            if not isinstance(node, dict):
                continue
            spec = ((node.get("input") or {}).get("required") or {}).get(param)
            if isinstance(spec, list) and spec and isinstance(spec[0], list):
                names = {x for x in spec[0] if isinstance(x, str)}
                out.setdefault(folder, set()).update(names)
        return out


def check_node(spec: NodeConfig, refs: list[ModelRef]) -> NodeHealth:
    """Self-check one node: online, version, vram, missing models."""
    h = NodeHealth(name=spec.name, base_url=spec.base_url)
    client = NodeClient(spec)
    if not client.ping():
        h.error = "无法连接"
        return h
    h.online = True
    st = client.stats()
    sysinfo = st.get("system") or {}
    h.version = str(sysinfo.get("comfyui_version") or "")
    devices = st.get("devices") or []
    if devices:
        h.device = str(devices[0].get("name") or "")
        h.vram_total = int(devices[0].get("vram_total") or 0)
        h.vram_used = int(devices[0].get("vram_used") or 0)
    have = client.installed_models()
    h.installed = sum(len(v) for v in have.values())
    for ref in refs:
        names = have.get(ref.folder)
        if names is not None and ref.filename in names:
            continue
        h.missing.append(ref.rel)
    return h


# --------------------------------------------------------------------------- #
# model transfer
# --------------------------------------------------------------------------- #
@dataclass
class SyncReport:
    """Progress of a model sync."""
    node: str = ""
    phase: str = ""            # scanning | copying | done
    file: str = ""
    files_total: int = 0
    files_done: int = 0
    bytes_total: int = 0
    bytes_done: int = 0
    speed: float = 0.0         # bytes/s
    eta: float = 0.0           # seconds
    error: str = ""
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        pct = (self.bytes_done / self.bytes_total * 100) if self.bytes_total else 0.0
        return {
            "node": self.node, "phase": self.phase, "file": self.file,
            "files_total": self.files_total, "files_done": self.files_done,
            "bytes_total": self.bytes_total, "bytes_done": self.bytes_done,
            "percent": round(pct, 1), "speed": round(self.speed, 1024),
            "speed_mb": round(self.speed / 1024 / 1024, 2), "eta": round(self.eta),
            "error": self.error, "skipped": list(self.skipped),
            "failed": list(self.failed),
        }


def _copy_with_progress(src: Path, dst: Path, report: SyncReport,
                         on_update: Callable[[], None], chunk: int = 4 * 1024 * 1024,
                        base: int = 0) -> None:
    """Copy a file, reporting byte progress as it goes."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    t0 = time.time()
    done = 0
    with open(src, "rb") as fin, open(tmp, "wb") as fout:
        while True:
            buf = fin.read(chunk)
            if not buf:
                break
            fout.write(buf)
            done += len(buf)
            report.bytes_done = base + done
            elapsed = max(time.time() - t0, 0.001)
            report.speed = done / elapsed
            if report.bytes_total:
                report.eta = max(0.0, (report.bytes_total - report.bytes_done) / max(report.speed, 1))
            on_update()
    tmp.replace(dst)


def _scp_with_progress(src: Path, spec: NodeConfig, remote_path: str,
                       report: SyncReport, on_update: Callable[[], None],
                       base: int = 0) -> None:
    """Copy a file to a remote host with scp, polling the remote size."""
    target = f"{spec.ssh_user}@{spec.ssh_host}:{remote_path}"
    cmd = ["scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
    if spec.ssh_key:
        cmd += ["-i", str(Path(spec.ssh_key).expanduser())]
    cmd += [str(src), target]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t0 = time.time()
    remote_size = 0
    while proc.poll() is None:
        time.sleep(1.0)
        try:
            stat = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
                + (["-i", str(Path(spec.ssh_key).expanduser())] if spec.ssh_key else [])
                + [f"{spec.ssh_user}@{spec.ssh_host}",
                   f"stat -c %s {remote_path} 2>/dev/null || echo 0"],
                capture_output=True, text=True, timeout=20)
            remote_size = int((stat.stdout or "0").strip() or 0)
        except Exception:  # noqa: BLE001
            remote_size = 0
        report.bytes_done = base + remote_size
        elapsed = max(time.time() - t0, 0.001)
        report.speed = remote_size / elapsed
        if report.bytes_total:
            report.eta = max(0.0, (report.bytes_total - remote_size) / max(report.speed, 1))
        on_update()
    if proc.returncode != 0:
        err = (proc.stderr.read() or b"").decode("utf-8", "replace")[:300]
        raise RuntimeError(f"scp 失败: {err}")


def sync_models(spec: NodeConfig, refs: list[ModelRef], report: SyncReport,
                on_update: Callable[[], None]) -> None:
    """Copy the models a node is missing, reporting progress.

    Two transports:
      shared - the node's models dir is mounted locally; copy into it
      scp    - copy over ssh to the node's models dir
    The source is always the local file referenced by the manifest.
    """
    report.node = spec.name
    report.phase = "scanning"
    on_update()
    todo: list[ModelRef] = []
    for ref in refs:
        if not ref.path.exists():
            report.failed.append(f"{ref.rel} (本地缺失: {ref.path})")
            continue
        todo.append(ref)
    report.files_total = len(todo)
    report.bytes_total = sum(r.size for r in todo)
    report.phase = "copying"
    on_update()
    for ref in todo:
        report.file = ref.rel
        on_update()
        base = report.bytes_done
        try:
            if spec.transfer == "scp":
                remote = f"{spec.remote_models.rstrip('/')}/{ref.folder}/{ref.filename}"
                _scp_with_progress(ref.path, spec, remote, report, on_update, base=base)
            else:
                dst = Path(spec.local_models) / ref.folder / ref.filename
                _copy_with_progress(ref.path, dst, report, on_update, base=base)
            report.files_done += 1
            report.bytes_done = max(report.bytes_done, base + ref.size)
        except Exception as e:  # noqa: BLE001
            report.failed.append(f"{ref.rel}: {str(e)[:120]}")
    report.phase = "done"
    on_update()


def nodes_from_config(cfg) -> list[NodeConfig]:
    """The fleet: the primary ComfyUI plus any extra configured nodes."""
    out: list[NodeConfig] = []
    primary = NodeConfig(name="local", base_url=cfg.comfyui.base_url,
                         auth=cfg.comfyui.auth if cfg.comfyui.auth in
                         ("none", "basic", "bearer") else "none",
                         auth_username=cfg.comfyui.auth_username,
                         auth_password=cfg.comfyui.auth_password,
                         auth_token=cfg.comfyui.auth_token,
                         extra_headers=cfg.comfyui.extra_headers,
                         verify_tls=cfg.comfyui.verify_tls)
    out.append(primary)
    out.extend(cfg.comfyui.nodes or [])
    return out


def models_root(cfg, root: Path) -> Path:
    """Where the model files live locally (the ComfyUI models dir)."""
    configured = (getattr(cfg.comfyui, "models_dir", "") or "").strip()
    return Path(configured) if configured else (root / "models")


def manifest(cfg, root: Path) -> list[ModelRef]:
    """The model files every rendering node needs, from the workflows."""
    c = cfg.comfyui
    return workflow_models(
        [c.t2i_workflow, c.i2v_workflow, c.upscale_workflow, c.flf_workflow],
        root, models_root(cfg, root))
