"""doctor should test the connection, not the model's patience.

It asked for one word in ten tokens. MiniMax-M3.1-Flash reasons before it
answers, so whether ten tokens is enough depends on how much it decides to
think - the same check passed and failed on consecutive runs. A self-check
that is flaky reports a broken thing when nothing is broken, and the
reader goes looking for a fault that is not there.

The budget is now one a reasoning model can answer inside, and the answer
is reported as what it is: a word back from a reachable model.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\cli.py")
s = p.read_text(encoding="utf-8", errors="replace")

old = '''        r = prov.llm.complete("You are a test.", "Reply with the single word: OK",
                              max_tokens=10)
        console.print(f"  LLM ({cfg.llm.model}) : [green]OK[/green] → {r.text.strip()[:20]!r}")'''

new = '''        # A reasoning model spends tokens thinking before it speaks, so a
        # budget this small sometimes leaves nothing to answer with - and a
        # self-check that passes or fails by luck is worse than no check.
        r = prov.llm.complete("You are a test.", "Reply with the single word: OK",
                              max_tokens=512)
        console.print(f"  LLM ({cfg.llm.model}) : [green]OK[/green] → {r.text.strip()[:20]!r}")'''

assert old in s, "doctor 的 LLM 检查锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("cli.py: doctor 的 LLM 检查给足 token，不再时好时坏")
