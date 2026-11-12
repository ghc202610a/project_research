import unittest

from project_research.selection import compare_versions, select_releases
from tests.helpers import release


class SelectionTests(unittest.TestCase):
    def test_component_aware_version_order(self):
        self.assertLess(compare_versions("v1.9.0", "v1.10.0"), 0)
        self.assertLess(compare_versions("2.0.0-rc.1", "2.0.0"), 0)
        self.assertEqual(compare_versions("1.2", "1.2.0"), 0)

    def test_date_bounds_are_inclusive_for_date_only_until(self):
        releases = [release(native_id=1, published="2024-03-01T12:00:00Z"),
                    release(native_id=2, tag="v1.3.0", published="2024-03-02T00:00:00Z")]
        result = select_releases(releases, since="2024-03-01", until="2024-03-01", all_releases=True)
        self.assertEqual([r.native_id for r in result], [1])

    def test_filters_prerelease_draft_and_version_bounds(self):
        stable = release(native_id=1, tag="v1.2.0")
        pre = release(native_id=2, tag="v1.3.0-rc.1", prerelease=True)
        draft_payload = release(native_id=3, tag="v1.4.0")
        from dataclasses import replace
        draft = replace(draft_payload, draft=True)
        result = select_releases([stable, pre, draft], min_version="1.2", max_version="1.3", all_releases=True)
        self.assertEqual([r.native_id for r in result], [1])
        result = select_releases([stable, pre, draft], include_prereleases=True, include_drafts=True, all_releases=True)
        self.assertEqual(len(result), 3)

    def test_last_n_returns_newest_chronologically(self):
        releases = [release(native_id=i, tag=f"v1.{i}.0", published=f"2024-03-{i:02d}T00:00:00Z") for i in range(1, 5)]
        self.assertEqual([r.native_id for r in select_releases(releases, last=2)], [3, 4])

    def test_default_prefers_latest_two_stable_major_lines(self):
        releases = [release(native_id=1, tag="v1.9.0", published="2023-01-01T00:00:00Z"),
                    release(native_id=2, tag="v2.0.0", published="2024-01-01T00:00:00Z"),
                    release(native_id=3, tag="v3.0.0", published="2025-01-01T00:00:00Z"),
                    release(native_id=4, tag="v3.1.0", published="2025-02-01T00:00:00Z")]
        self.assertEqual({r.native_id for r in select_releases(releases)}, {2, 3, 4})

    def test_invalid_bounds(self):
        with self.assertRaises(ValueError):
            select_releases([release()], since="not-a-date")
        with self.assertRaises(ValueError):
            select_releases([release()], min_version="2.0", max_version="1.0")


if __name__ == "__main__":
    unittest.main()
