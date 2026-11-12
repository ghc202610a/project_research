import tempfile
import unittest
from pathlib import Path

from project_research.storage import ReleaseStore
from tests.helpers import repository, release


class StorageTests(unittest.TestCase):
    def test_upsert_preserves_distinct_raw_observations_and_searches(self):
        with tempfile.TemporaryDirectory() as tmp:
            with ReleaseStore(Path(tmp) / "test.sqlite3") as store:
                repo = repository()
                first = release(body="Fixes the widget parser")
                store.save_releases(repo, [first], "2024-03-02T00:00:00Z")
                self.assertEqual(store.observation_count(repo.key, first.native_id), 1)
                self.assertEqual(len(store.search("widget")), 1)
                store.save_releases(repo, [first], "2024-03-03T00:00:00Z")
                self.assertEqual(store.observation_count(repo.key, first.native_id), 1)
                self.assertEqual(len(store.list_releases(repo.key)), 1)

    def test_search_index_can_be_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with ReleaseStore(Path(tmp) / "test.sqlite3") as store:
                repo = repository()
                item = release(body="rebuildable index")
                store.save_releases(repo, [item], item.retrieved_at)
                store.connection.execute("DELETE FROM release_search")
                self.assertEqual(store.search("rebuildable"), [])
                self.assertEqual(store.rebuild_search_index(), 1)
                self.assertEqual(len(store.search("rebuildable")), 1)

    def test_tags_are_distinguished_from_published_releases(self):
        from project_research.models import TagRecord
        with tempfile.TemporaryDirectory() as tmp:
            with ReleaseStore(Path(tmp) / "test.sqlite3") as store:
                repo = repository()
                published = release(tag="v1.2.0")
                store.save_releases(repo, [published], published.retrieved_at)
                tags = [TagRecord("github", repo.key, "v1.2.0", "aaa", None, None),
                        TagRecord("github", repo.key, "v1.3.0", "bbb", None, None)]
                store.save_tags(repo, tags, "2024-03-02T00:00:00Z")
                rows = {row["name"]: row["has_release"] for row in store.list_tags(repo.key)}
                self.assertEqual(rows, {"v1.2.0": 1, "v1.3.0": 0})

    def test_changed_raw_payload_adds_observation(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as tmp:
            with ReleaseStore(Path(tmp) / "test.sqlite3") as store:
                repo = repository()
                first = release(body="Initial")
                changed = replace(first, body="Updated", raw={**first.raw, "body": "Updated"}, retrieved_at="2024-03-04T00:00:00Z")
                store.save_releases(repo, [first], first.retrieved_at)
                store.save_releases(repo, [changed], changed.retrieved_at)
                self.assertEqual(store.observation_count(repo.key, first.native_id), 2)
                self.assertIn("Updated", store.list_releases(repo.key)[0].body)


if __name__ == "__main__":
    unittest.main()
