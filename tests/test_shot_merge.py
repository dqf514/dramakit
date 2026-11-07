"""Two shots that are the same picture are one shot.

The model copies the shot before it when it wants a new line to have
its own moment.  A cut to the same picture is not a cut.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.models import Scene, Shot, ShotType  # noqa: E402
from dramakit.pipeline.shots import merge_duplicate_shots  # noqa: E402


def _shot(action, st=ShotType.MEDIUM, angle="斜侧", height="平视",
          move="固定", lines=None, beats=None, dur=8.0):
    return Shot(id="sh-%s" % action[:4], index=0, shot_type=st,
                camera_move=move, angle=angle, height=height,
                duration=dur, action=action, characters=["夏一朵"],
                line_indices=list(lines or []), beats=list(beats or []))


def test_the_same_picture_twice_becomes_one():
    sc = Scene(id="sc1", index=1, location="房间", time_of_day="日")
    sc.shots = [
        _shot("夏一朵站在窗前，抬手挡住眼睛", lines=[1], beats=[1]),
        _shot("夏一朵站在窗前，抬手挡住眼睛", lines=[2]),
    ]
    n = merge_duplicate_shots(sc)
    assert n == 1
    assert len(sc.shots) == 1
    assert sc.shots[0].line_indices == [1, 2]


def test_a_connector_in_front_is_still_the_same_picture():
    sc = Scene(id="sc1", index=1, location="房间", time_of_day="日")
    sc.shots = [
        _shot("夏一朵双手抱头蹲下，肩膀发抖", lines=[1]),
        _shot("接上：夏一朵双手抱头蹲下，肩膀发抖", lines=[2]),
    ]
    assert merge_duplicate_shots(sc) == 1
    assert len(sc.shots) == 1


def test_a_different_picture_is_left_alone():
    sc = Scene(id="sc1", index=1, location="房间", time_of_day="日")
    sc.shots = [
        _shot("夏一朵站在窗前", lines=[1]),
        _shot("镜中那张陌生的脸", st=ShotType.EXTREME_CLOSE, lines=[2]),
    ]
    assert merge_duplicate_shots(sc) == 0
    assert len(sc.shots) == 2


def test_the_same_words_in_another_framing_are_two_shots():
    sc = Scene(id="sc1", index=1, location="房间", time_of_day="日")
    sc.shots = [
        _shot("夏一朵站在窗前", angle="斜侧", lines=[1]),
        _shot("夏一朵站在窗前", angle="正侧", lines=[2]),
    ]
    assert merge_duplicate_shots(sc) == 0
    assert len(sc.shots) == 2


def test_the_shots_are_numbered_again_after_a_merge():
    sc = Scene(id="sc1", index=1, location="房间", time_of_day="日")
    sc.shots = [
        _shot("夏一朵站在窗前", lines=[1]),
        _shot("夏一朵站在窗前", lines=[2]),
        _shot("镜中的脸", st=ShotType.EXTREME_CLOSE, lines=[3]),
    ]
    merge_duplicate_shots(sc)
    assert [s.index for s in sc.shots] == [0, 1]


if __name__ == "__main__":
    test_the_same_picture_twice_becomes_one()
    test_a_connector_in_front_is_still_the_same_picture()
    test_a_different_picture_is_left_alone()
    test_the_same_words_in_another_framing_are_two_shots()
    test_the_shots_are_numbered_again_after_a_merge()
    print("  五个都过了")
