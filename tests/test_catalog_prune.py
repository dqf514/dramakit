"""The catalog must not keep rows for projects that are gone.

A project can be deleted from the disk without the console knowing - by
hand, or by a tool.  Its rows would stay, and every one of them is a
picture that cannot be loaded and a search result that leads nowhere.
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, r"E:\dramakit")

from dramakit.catalog import Catalog  # noqa: E402


class CatalogPruneTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cat = Catalog(pathlib.Path(self.dir.name) / "catalog.db")

    def tearDown(self):
        self.dir.cleanup()

    def _add(self, project):
        self.cat.upsert(project=project, kind="project", ref="r",
                        title="t", text="x", path="project.json")

    def test_the_rows_of_a_project_that_is_gone_go(self):
        self._add("留下的")
        self._add("没了的")
        gone = self.cat.prune_missing({"留下的"})
        self.assertEqual(gone, ["没了的"])
        rows = self.cat.projects()
        self.assertEqual([r["project"] for r in rows], ["留下的"])

    def test_a_project_that_is_there_stays(self):
        self._add("在的")
        self.cat.prune_missing({"在的"})
        self.assertEqual(len(self.cat.projects()), 1)

    def test_clearing_one_project_leaves_the_others(self):
        self._add("甲")
        self._add("乙")
        self.cat.clear_project("甲")
        self.assertEqual([r["project"] for r in self.cat.projects()], ["乙"])


if __name__ == "__main__":
    unittest.main()
