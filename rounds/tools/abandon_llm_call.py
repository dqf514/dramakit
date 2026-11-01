"""A model call can be abandoned, so a stop does not wait for it.

A stage that loops checks between items and stops in a breath. A stage
that makes one long call - analyze reads a whole season's chapters,
character dresses every face - has no such seam: the run holds the call
to the end, which is a minute or more, and then writes the stage up as
finished rather than refused. The user asked to stop and got a stage that
claimed to have completed.

The client that makes the call is the one place that can let go sooner.
When a run has bound a stop, the request is issued in a worker and the
caller waits on the event as well as on the answer: the moment the stop
is raised, the call returns - the request carries on at the provider and
is paid for, but the run moves now instead of in a minute.

The exception is raised lazily. providers cannot import the pipeline at
module level - the pipeline imports the providers - so the name is looked
up when it is needed rather than when the file is read.
"""
from pathlib import Path

# ------------------------------------------------ 1. 客户端认 stop 事件 --
llm = Path(r"E:\\dramakit\\dramakit\\providers\\llm.py")
s = llm.read_text(encoding="utf-8")

if "stop_event" not in s:
    old_init = '''    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.base_url = cfg.base_url.rstrip("/")'''
    new_init = '''    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        # Set when a run is running and someone asks it to stop. It is
        # consulted between attempts and around the request itself, so a
        # call that would hold a stage for a minute lets go at once.
        self.stop_event = None
        self.base_url = cfg.base_url.rstrip("/")'''
    assert old_init in s, "客户端 __init__ 锚点没找到"
    s = s.replace(old_init, new_init, 1)

    old_post = '''    def _post(self, payload: dict) -> dict:
        attempts = max(1, self.cfg.max_retries + 1)'''
    new_post = '''    def _abandoned(self) -> bool:
        """Raise if the run was asked to stop while this call was in flight."""
        from ..pipeline.base import RunStopped
        if self.stop_event is not None and self.stop_event.is_set():
            raise RunStopped()

    def _post(self, payload: dict) -> dict:
        # A stop must land now, not when the request happens to finish.
        # The call is issued in a worker and the caller waits on the event
        # as well as the answer; the request carries on at the provider
        # and is paid for either way, but the run moves on immediately.
        if self.stop_event is not None:
            box: dict = {}

            def _work():
                try:
                    box["res"] = self._post_retrying(payload)
                except BaseException as e:  # noqa: BLE001
                    box["err"] = e

            th = threading.Thread(target=_work, daemon=True)
            th.start()
            while th.is_alive():
                if self.stop_event.wait(0.25):
                    self._abandoned()
                th.join(0.25)
            self._abandoned()
            if "err" in box:
                raise box["err"]
            return box["res"]
        return self._post_retrying(payload)

    def _post_retrying(self, payload: dict) -> dict:
        attempts = max(1, self.cfg.max_retries + 1)'''
    assert old_post in s, "_post 锚点没找到"
    s = s.replace(old_post, new_post, 1)

    # and give up between attempts too
    old_retry = '''            with attempt:
                return self._post_once(payload)'''
    new_retry = '''            with attempt:
                self._abandoned()
                return self._post_once(payload)'''
    assert old_retry in s, "重试锚点没找到"
    s = s.replace(old_retry, new_retry, 1)

    # threading is needed
    if "\nimport threading" not in s:
        s = s.replace("import time", "import threading\nimport time", 1) \
            if "\nimport time" in s else \
            s.replace("import json", "import json\nimport threading", 1)

    llm.write_text(s, encoding="utf-8")
    print("llm.py: 模型调用可以被放弃")
else:
    print("llm.py: 已有 stop_event")

# ------------------------------------- 2. Providers 把事件发给各客户端 --
pr = Path(r"E:\\dramakit\\dramakit\\providers\\__init__.py")
t = pr.read_text(encoding="utf-8")

if "def bind_stop" not in t:
    old_ctor = '''        self._music: Optional[BaseMusic] = None'''
    new_ctor = '''        self._music: Optional[BaseMusic] = None
        # every client is told when a run is asked to stop, so a long
        # model call lets go at once instead of at its end
        self._stop = None'''
    assert old_ctor in t, "Providers.__init__ 锚点没找到"
    t = t.replace(old_ctor, new_ctor, 1)

    anchor = "    def llm_for(self, stage: str) -> BaseLLM:"
    assert anchor in t, "llm_for 锚点没找到"
    add = '''    def bind_stop(self, event) -> None:
        """Tell every client, present and future, that a stop can happen."""
        self._stop = event
        for client in [self._llm, *self._llm_roles.values()]:
            if client is not None:
                client.stop_event = event

''' + anchor
    t = t.replace(anchor, add, 1)

    # a client built later is told too
    t = t.replace(
        '''                self._llm_roles[stage] = build_llm(self.cfg.resolve_llm(stage))
            return self._llm_roles[stage]''',
        '''                client = build_llm(self.cfg.resolve_llm(stage))
                client.stop_event = self._stop
                self._llm_roles[stage] = client
            return self._llm_roles[stage]''', 1)

    pr.write_text(t, encoding="utf-8")
    print("providers: bind_stop 会通知已建和将建的客户端")
else:
    print("providers: bind_stop 已存在")

# ------------------------------------------- 3. Context 绑定时转发 ------
b = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
u = b.read_text(encoding="utf-8")

old_bind = '''    def bind_stop(self, event) -> None:
        """Hand the run the thing that can stop it."""
        self._stop = event'''
new_bind = '''    def bind_stop(self, event) -> None:
        """Hand the run the thing that can stop it.

        The providers are told too: a stage that makes one long model call
        has nothing to check between items, and only the client making the
        call can let go of it early.
        """
        self._stop = event
        try:
            self.providers.bind_stop(event)
        except AttributeError:  # a stub provider in a test
            pass'''
assert old_bind in u, "Context.bind_stop 锚点没找到"
b.write_text(u.replace(old_bind, new_bind, 1), encoding="utf-8")
print("base.py: 绑定停止时也通知 providers")
