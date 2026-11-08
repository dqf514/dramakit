"""The Chinese that is not the dialogue is taken out of the description.

The model ends its description with a Chinese paragraph of constraints,
and the sampler has no negative branch: every word of it goes into the
picture.  It is in the model's weights - deleting it from every file we
have does not stop it - so it is taken out of the answer.
"""
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.pipeline.h3text import english_only  # noqa: E402

BAD = ("[Shot 1] a woman on a bed, moonlight on silk. "
       "保持人物身份、脸部、发型与服装和第一帧完全一致；画面里不出现除第一帧已有"
       "文字以外的新文字，也不加字幕和水印；不出现多余人物、多余肢体或畸形的手；"
       "镜头不抖动、不跳帧、不慢动作。")

GOOD = ("[Shot 1] a woman on a bed, moonlight on silk. "
        "(S1) she speaks: <d>[zh-CN]那只是一个噩梦；</d> "
        "cool moonlight rims the silk against deep shadow.")


def test_the_chinese_constraints_are_taken_out():
    out = english_only(BAD)
    assert "保持人物身份" not in out
    assert "不出现多余人物" not in out
    assert "a woman on a bed" in out


def test_the_line_that_is_spoken_stays():
    out = english_only(GOOD)
    assert "<d>[zh-CN]那只是一个噩梦；</d>" in out
    assert "cool moonlight rims the silk" in out


def test_the_english_is_untouched():
    out = english_only(GOOD)
    assert "[Shot 1] a woman on a bed, moonlight on silk." in out
    assert "cool moonlight rims the silk against deep shadow." in out


if __name__ == "__main__":
    test_the_chinese_constraints_are_taken_out()
    test_the_line_that_is_spoken_stays()
    test_the_english_is_untouched()
    print("  三个都过了")
