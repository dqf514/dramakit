"""Say the model ran out of budget, not that its answer was malformed.

complete() reads choices[0].message.content and, when that key is missing,
blames the response shape. But the response carries the reason: a reasoning
model given ten tokens spends them thinking, returns message with
reasoning_content and no content at all, and finish_reason says "length".
Hunting the parser for a shape that was never wrong is time spent on the
wrong problem - the shape is fine, the budget was too small.

So a missing content is diagnosed from what the response does say. When
the run was cut short, the error names the budget and the thinking that
ate it; only a genuinely unrecognised response is called unrecognised.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\providers\\llm.py")
s = p.read_text(encoding="utf-8", errors="replace")

old = '''        data = self._post(payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected LLM response shape: {str(data)[:300]}")'''

new = '''        data = self._post(payload)
        try:
            choice = data["choices"][0]
            message = choice["message"]
            text = message["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(_shape_error(data, budget, e)) from e
        if text is None:
            # A reasoning model can spend the whole budget thinking and hand
            # back reasoning_content with no content. finish_reason says so,
            # and reporting that as a malformed response sends the reader
            # looking for a parser bug that does not exist.
            raise RuntimeError(_shape_error(data, budget, None))'''

assert old in s, "complete() 的解析锚点没找到"
s = s.replace(old, new, 1)

# the diagnosis itself, and the budget it reports
helper = '''
def _shape_error(data: object, budget: int, exc: Optional[Exception]) -> str:
    """Why an LLM response could not be read, in the reader's terms.

    The endpoint is reachable when this is raised, so the useful answer is
    what the model actually did - and for a reasoning model the common
    answer is that it thought for the whole budget and had nothing left to
    say. That is a budget to raise, not a parser to fix.
    """
    if not isinstance(data, dict) or "choices" not in data:
        return f"Unexpected LLM response shape: {str(data)[:300]}"
    choices = data.get("choices") or []
    if not choices:
        return (f"模型没有返回任何选择（max_tokens={budget}）。"
                f"推理型模型会先把 token 花在思考上，把 max_tokens 调大再试。")
    message = (choices[0] or {}).get("message") or {}
    reason = (choices[0] or {}).get("finish_reason") or ""
    thinking = len(str(message.get("reasoning_content") or ""))
    if reason == "length" or (not message.get("content") and thinking):
        return (f"模型在 {budget} 个 token 内只做了推理（{thinking} 字），没有输出正文"
                f"（finish_reason={reason or 'length'}）。把 max_tokens 调大再试。")
    if exc is not None:
        return f"Unexpected LLM response shape: {str(data)[:300]}"
    return f"模型返回了空正文: {str(data)[:300]}"


'''

anchor = "class OpenAICompatLLM"
assert anchor in s, "找不到 OpenAICompatLLM"
s = s.replace(anchor, helper.lstrip("\n") + anchor, 1)

p.write_text(s, encoding="utf-8")
print("llm.py: token 不够导致的空正文，现在会说是预算问题")
