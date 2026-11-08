"""A split that does not split anything is not a split.

A line longer than the limit on its own used to send the split round
in circles: the second half was given all of the lines, the loop came
straight back to it, and each time the description grew by three
characters - until the machine ran out of memory in the middle of a
scene.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.models import Line, LineKind, Scene, Shot, ShotType
from dramakit.pipeline.storyboard import _split_long_shots, _strip_prefix


def _scene(line_texts, action="她在窗前，看着外面。"):
    sc = Scene(id="sc1", index=1, location="房间", time_of_day="日")
    for i, t in enumerate(line_texts, 1):
        sc.lines.append(Line(id="ln%d" % i, kind=LineKind.DIALOGUE,
                             speaker="薛青萝", text=t, emotion="平静"))
    sc.shots = [Shot(id="sh1", index=0, shot_type=ShotType.MEDIUM,
                     angle="斜侧", camera_move="固定", height="平视",
                     lens="标准", duration=10.0, action=action,
                     characters=["薛青萝"], line_indices=list(range(1, len(line_texts) + 1)))]
    return sc


def test_a_long_line_does_not_send_the_split_round_in_circles():
    # 60 characters is longer than one shot can hold
    long_line = "这句话很长很长，长到一句台词念完镜头就已经转不动了" * 2
    sc = _scene([long_line, "另一句。"])
    added = _split_long_shots(sc)
    assert added < 10, added
    assert len(sc.shots) < 10, len(sc.shots)
    for sh in sc.shots:
        assert len(sh.action or "") < 200, len(sh.action or "")


def test_the_description_does_not_pile_up_the_connector():
    sc = _scene(["这一句很长了，长到一句话念完要十几秒，后面还跟着一句。",
                 "后面那一句也不短，同样要念上好一阵子才说得完。"])
    _split_long_shots(sc)
    for sh in sc.shots:
        assert (sh.action or "").count("接上：") <= 1, sh.action


def test_the_connector_is_taken_off_before_one_is_put_on():
    assert _strip_prefix("接上：接上：她转过身") == "她转过身"
    assert _strip_prefix("她转过身") == "她转过身"


def test_the_split_keeps_every_line():
    sc = _scene(["第一句。", "第二句。", "第三句。", "第四句。"])
    _split_long_shots(sc)
    kept = []
    for sh in sc.shots:
        kept += list(sh.line_indices or [])
    assert sorted(kept) == [1, 2, 3, 4], kept


if __name__ == "__main__":
    test_a_long_line_does_not_send_the_split_round_in_circles()
    test_the_description_does_not_pile_up_the_connector()
    test_the_connector_is_taken_off_before_one_is_put_on()
    test_the_split_keeps_every_line()
    print("  四个都过了")
