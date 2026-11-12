import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from project_research.cli import main
from project_research.render import render_html, write_per_release_markdown
from project_research.storage import ReleaseStore
from tests.helpers import repository, release


class RenderAndCliTests(unittest.TestCase):
    def test_html_escapes_untrusted_release_body(self):
        repo = repository()
        item = release(body='<script>alert("x")</script>')
        rendered = render_html(repo, [item])
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_per_release_markdown_writes_index_and_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = write_per_release_markdown(tmp, repository(), [release(), release(native_id=8, tag="v1.3.0")])
            self.assertEqual(len(files), 3)
            self.assertTrue((Path(tmp) / "README.md").exists())

    def test_local_cli_list_export_search_and_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "db.sqlite3"
            repo = repository()
            item = release(body="Security fix for parser")
            from project_research.models import TagRecord
            with ReleaseStore(db) as store:
                store.save_releases(repo, [item], item.retrieved_at)
                store.save_tags(repo, [TagRecord("github", repo.key, "v1.2.0", "sha", None, None),
                                       TagRecord("github", repo.key, "v1.3.0", "sha2", None, None)], item.retrieved_at)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["list", "octo/demo", "--db", str(db), "--all"]), 0)
                self.assertEqual(main(["search", "security", "--db", str(db)]), 0)
                self.assertEqual(main(["rebuild-index", "--db", str(db)]), 0)
                self.assertEqual(main(["tags", "octo/demo", "--db", str(db)]), 0)
                self.assertEqual(main(["export", "octo/demo", "--db", str(db), "--format", "json", "--all", "-o", str(Path(tmp) / "out.json")]), 0)
            self.assertIn("1 release(s)", output.getvalue())
            self.assertIn("tag only", output.getvalue())
            self.assertTrue((Path(tmp) / "out.json").exists())


if __name__ == "__main__":
    unittest.main()
