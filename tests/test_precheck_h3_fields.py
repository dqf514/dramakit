"""The precheck has to agree with the compose.

Two things it got wrong, and both of them blocked a finished episode:
the sound comes with the picture when H3 makes it, and the prompt in
that case is the reference format, which has no label on the
description.
"""
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.pipeline.precheck import _h3_missing  # noqa: E402

R2V = """subject_definitions:
<Picture 2> is the character sheet of Xue Qingluo.

summary:
[reference generation + audio reference] The target video is a single shot.

overall_soundscape: N/A

non_diegetic_music: N/A
"""

THREE = ("integrated_multimodal_description: [Shot 1] a woman in white\n\n"
         "overall_soundscape: N/A\n\nnon_diegetic_music: N/A")


def test_the_reference_format_does_not_need_the_label():
    assert _h3_missing(R2V) == [], _h3_missing(R2V)


def test_the_three_field_format_needs_all_three():
    assert _h3_missing(THREE) == []


def test_a_missing_sound_field_is_still_caught():
    broken = R2V.replace("overall_soundscape: N/A", "")
    assert _h3_missing(broken) == ["overall_soundscape"]


def test_an_empty_prompt_is_all_three():
    assert _h3_missing("") == ["integrated_multimodal_description",
                                "overall_soundscape", "non_diegetic_music"]


if __name__ == "__main__":
    test_the_reference_format_does_not_need_the_label()
    test_the_three_field_format_needs_all_three()
    test_a_missing_sound_field_is_still_caught()
    test_an_empty_prompt_is_all_three()
    print("  四个都过了")
