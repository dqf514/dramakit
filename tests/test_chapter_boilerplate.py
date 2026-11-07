"""The front matter of a downloaded book is not a chapter.

Every book that comes from a download site opens with the site's own
page: a declaration, the words "all chapters", a line of dashes.  It
used to become the first episode, and the first episode of the drama
was a copyright notice.
"""
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.utils.text import split_chapters  # noqa: E402

FRONT = """声明：本书为八零电子BOOK的用户自网络收集整理制作,仅供预览交流学习使用,版权归原作者和出版社所有。如果喜欢,请支持正版。以下作品内容之版权与本站无任何关系。
---------------------------用户上传之内容开始---------------------------

------------

全部章节

------------

第1章 梦境

    从梦中醒来，汗水打湿鬓发。

    金丹位置似乎都在隐隐作痛。

第2章 闯祸

    「盈盈，从今以后你就住在这里。」
"""

TAIL = """
---------------------------用户上传之内容结束---------------------------
声明：本书为八零电子BOOK的用户自网络收集整理制作,仅供预览交流学习使用,版权归原作者和出版社所有。
"""


def test_the_front_matter_is_not_a_chapter():
    chapters = split_chapters(FRONT)
    assert len(chapters) == 2, [c["title"] for c in chapters]
    assert "梦境" in chapters[0]["title"]


def test_the_tail_is_not_in_the_last_chapter():
    chapters = split_chapters(FRONT + TAIL)
    assert "声明" not in chapters[-1]["body"]
    assert "用户上传" not in chapters[-1]["body"]


def test_a_real_prologue_is_still_kept():
    text = ("这是一段很长的序言。" * 60) + "\n第1章 梦境\n\n    正文。\n" * 1
    chapters = split_chapters(text)
    assert len(chapters) == 2
    assert chapters[0]["title"] == "开篇"


def test_a_book_with_no_headings_is_one_block():
    chapters = split_chapters("就是一段没有章节的正文。" * 20)
    assert len(chapters) == 1
    assert chapters[0]["body"]


if __name__ == "__main__":
    test_the_front_matter_is_not_a_chapter()
    test_the_tail_is_not_in_the_last_chapter()
    test_a_real_prologue_is_still_kept()
    test_a_book_with_no_headings_is_one_block()
    print("  四个都过了")
