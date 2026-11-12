import tempfile
import unittest
from pathlib import Path

from project_research.assets import AssetDownloadError, validate_asset_filename, download_asset
from project_research.github import GitHubClient
from tests.helpers import repository


class FakeClient(GitHubClient):
    def __init__(self, content=b"artifact"):
        self.content = content
    def download_asset(self, url, destination, *, max_bytes):
        import hashlib
        data = self.content
        if len(data) > max_bytes:
            raise RuntimeError("limit")
        Path(destination).write_bytes(data)
        return hashlib.sha256(data).hexdigest(), len(data)


class AssetTests(unittest.TestCase):
    def test_filename_rejects_paths(self):
        self.assertEqual(validate_asset_filename("app.tar.gz"), "app.tar.gz")
        for name in ("../escape", "a/b", "a\\b", "C:evil"):
            with self.assertRaises(AssetDownloadError):
                validate_asset_filename(name)

    def test_download_writes_provenance_sidecar(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.bin"
            digest = hashlib.sha256(b"artifact").hexdigest()
            result = download_asset(FakeClient(), repository(),
                {"native_id": 9, "name": "artifact.bin", "digest": f"sha256:{digest}"},
                {"native_id": 7, "tag_name": "v1.2.0", "release_url": "https://github.com/octo/demo/releases/tag/v1.2.0"},
                target)
            self.assertEqual(target.read_bytes(), b"artifact")
            self.assertTrue(Path(str(target) + ".provenance.json").exists())
            self.assertTrue(result["publisher_digest_verified"])

    def test_provider_size_mismatch_does_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.bin"
            with self.assertRaises(AssetDownloadError):
                download_asset(FakeClient(), repository(),
                    {"native_id": 9, "name": "artifact.bin", "size": 99},
                    {"native_id": 7, "tag_name": "v1.2.0"}, target)
            self.assertFalse(target.exists())

    def test_digest_mismatch_does_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "artifact.bin"
            with self.assertRaises(AssetDownloadError):
                download_asset(FakeClient(), repository(),
                    {"native_id": 9, "name": "artifact.bin", "digest": "sha256:" + "0" * 64},
                    {"native_id": 7, "tag_name": "v1.2.0"}, target)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
