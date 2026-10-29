"""Hand the jobs out one at a time.

Four jobs started together all read the same busy count and all went to
the same node. Taking a node and counting it has to happen together, under
a lock, or the race is exactly what it was.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\providers\\pool.py")
s = p.read_text(encoding="utf-8")

old = """    def __init__(self, nodes: list[_Node]):
        self.nodes = nodes
        # jobs we have sent and not yet got back
        self._inflight: dict[str, int] = {}

    # ------------------------------------------------------------- selection
    def candidates(self, role: str) -> list[_Node]:
        \"\"\"Nodes that can take this role, least busy first.\"\"\"
        ok = [n for n in self.nodes if n.takes(role)]
        return sorted(ok, key=lambda n: (self.busy(n), n.name))

    def busy(self, node: _Node) -> int:
        \"\"\"How much this node has on: what it says plus what we sent it.\"\"\"
        return node.depth() + self._inflight.get(node.name, 0)"""
new = """    def __init__(self, nodes: list[_Node]):
        self.nodes = nodes
        # jobs we have sent and not yet got back
        self._inflight: dict[str, int] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------- selection
    def candidates(self, role: str) -> list[_Node]:
        \"\"\"Nodes that can take this role, least busy first.\"\"\"
        ok = [n for n in self.nodes if n.takes(role)]
        return sorted(ok, key=lambda n: (self.busy(n), n.name))

    def busy(self, node: _Node) -> int:
        \"\"\"How much this node has on: what it says plus what we sent it.\"\"\"
        return node.depth() + self._inflight.get(node.name, 0)

    def _take(self, role: str, skip: set[str]) -> Optional[_Node]:
        \"\"\"Pick the least busy node and count the job on it, together.\"\"\"
        ok = [n for n in self.nodes if n.takes(role) and n.name not in skip]
        if not ok:
            return None
        node = min(ok, key=lambda n: (self.busy(n), n.name))
        self._inflight[node.name] = self._inflight.get(node.name, 0) + 1
        return node"""
assert old in s, "init 锚点没找到"
s = s.replace(old, new, 1)

old = """    def _dispatch(self, role: str, fn) -> str:
        tried: list[str] = []
        last: Optional[Exception] = None
        for node in self.candidates(role):
            tried.append(node.name)
            # the job counts as busy from the moment it is sent, not from
            # the moment the node says so
            self._inflight[node.name] = self._inflight.get(node.name, 0) + 1
            try:
                return fn(node.client)
            except Exception as e:  # noqa: BLE001
                last = e
                log.warning("节点 %s 渲染失败，转移: %s", node.name, str(e)[:160])
                node.forget_queue()
            finally:
                self._inflight[node.name] = max(
                    0, self._inflight.get(node.name, 0) - 1)
        raise ComfyUIError(
            f"没有可用的渲染节点（任务={role}，尝试过 {', '.join(tried) or '无'}）"
            + (f"：{last}" if last else ""))"""
new = """    def _dispatch(self, role: str, fn) -> str:
        tried: list[str] = []
        last: Optional[Exception] = None
        while True:
            with self._lock:
                node = self._take(role, set(tried))
            if node is None:
                break
            tried.append(node.name)
            try:
                return fn(node.client)
            except Exception as e:  # noqa: BLE001
                last = e
                log.warning("节点 %s 渲染失败，转移: %s", node.name, str(e)[:160])
                node.forget_queue()
            finally:
                with self._lock:
                    self._inflight[node.name] = max(
                        0, self._inflight.get(node.name, 0) - 1)
        raise ComfyUIError(
            f"没有可用的渲染节点（任务={role}，尝试过 {', '.join(tried) or '无'}）"
            + (f"：{last}" if last else ""))"""
assert old in s, "dispatch 锚点没找到"
s = s.replace(old, new, 1)

if "\nimport threading" not in s:
    s = s.replace("import time", "import threading\nimport time", 1)

p.write_text(s, encoding="utf-8")
print("pool.py 已改（原子地挑节点）")
