"""Does the error say what actually went wrong?

_shape_error is what a reader sees when a response cannot be parsed, and
its job is to point at the cause. These are the four shapes the endpoint
really returns, taken from live responses, so the wording is checked
against reality rather than against what the code hoped for.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.providers.llm import _shape_error

# the response MiniMax actually gave at max_tokens=10
ran_out = {
    "id": "0736",
    "choices": [{"finish_reason": "length", "index": 0,
                 "message": {"role": "assistant",
                             "reasoning_content": "We need answer single word OK. Need comply"}}],
    "usage": {"completion_tokens": 10},
}

out = []
for label, data, budget, exc in [
    ("预算被推理吃光（真实响应）", ran_out, 10, KeyError("content")),
    ("choices 为空", {"choices": []}, 10, IndexError()),
    ("响应根本不是 dict", "not a dict", 10, TypeError()),
    ("空正文、没截断", {"choices": [{"message": {"content": ""}}]}, 256, None),
]:
    out.append(f"=== {label} ===")
    out.append("  " + _shape_error(data, budget, exc))
    out.append("")

from pathlib import Path
Path(r"C:\Users\David\AppData\Local\Temp\opencode\msg.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
