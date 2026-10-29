"""Spread the jobs evenly over the nodes.

The pool measured how busy a node was by asking it, and the answer was
cached for three seconds - so the four jobs that started together all read
the same depth and all went to the same node. The pool knows how many jobs
it has sent and not yet got back: that count is exact and immediate.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\providers\\pool.py")
s = p.read_text(encoding="utf-8")

old = """    def __init__(self, nodes: list[_Node]):
        self.nodes = nodes

    # ------------------------------------------------------------- selection
    def candidates(self, role: str) -> list[_Node]:
        \"\"\"Nodes that can take this role, least busy first.\"\"\"
        ok = [n for n in self.nodes if n.takes(role)]
        return sorted(ok, key=lambda n: (n.depth(), n.name))"""
new = """    def __init__(self, nodes: list[_Node]):
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
assert old in s, "candidates 锚点没找到"
s = s.replace(old, new, 1)

old = """    def _dispatch(self, role: str, fn) -> str:
        tried: list[str] = []
        last: Optional[Exception] = None
        for node in self.candidates(role):
            tried.append(node.name)
            try:
                return fn(node.client)
            except Exception as e:  # noqa: BLE001
                last = e
                log.warning("节点 %s 渲染失败，转移: %s", node.name, str(e)[:160])
                node.forget_queue()"""
new = """    def _dispatch(self, role: str, fn) -> str:
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
                    0, self._inflight.get(node.name, 0) - 1)"""
assert old in s, "dispatch 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("pool.py 已改（按在途任务均分）")
