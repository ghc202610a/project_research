import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from project_research.media import extract_image_urls, collect_release_images, _raster_extension, _validate_public_url


class MediaTests(unittest.TestCase):
    def test_extracts_markdown_and_html_images_without_duplicates(self):
        body = '![one](https://example.com/a.png) <img src="https://example.com/b.jpg"> ![again](https://example.com/a.png)'
        self.assertEqual(extract_image_urls(body), ["https://example.com/a.png", "https://example.com/b.jpg"])

    def test_raster_content_type_and_signature_must_match(self):
        self.assertEqual(_raster_extension("image/png", b"\x89PNG\r\n\x1a\nrest"), ".png")
        self.assertIsNone(_raster_extension("image/png", b"not a png"))
        self.assertIsNone(_raster_extension("image/svg+xml", b"<svg/>"))

    def test_blocks_private_addresses(self):
        with self.assertRaises(ValueError):
            _validate_public_url("http://127.0.0.1/image.png")

    def test_records_downloaded_media_under_hash_name(self):
        png = b"\x89PNG\r\n\x1a\nimage-data"
        with tempfile.TemporaryDirectory() as tmp, patch("project_research.media._fetch_image", return_value=("image/png", png)):
            results = collect_release_images("![image](https://example.com/image.png)", tmp, 7)
            self.assertEqual(results[0].status, "downloaded")
            self.assertTrue(Path(results[0].local_path).exists())
            self.assertEqual(Path(results[0].local_path).suffix, ".png")

    def test_existing_download_is_reused_without_network(self):
        png = b"\x89PNG\r\n\x1a\nimage-data"
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cached.png"
            path.write_bytes(png)
            cached = {"https://example.com/image.png": {"status": "downloaded", "local_path": str(path),
                      "content_type": "image/png", "size": len(png), "sha256": hashlib.sha256(png).hexdigest()}}
            with patch("project_research.media._fetch_image", side_effect=AssertionError("network should not be used")):
                results = collect_release_images("![image](https://example.com/image.png)", tmp, 7,
                                                  existing_media=cached)
            self.assertEqual(results[0].status, "cached")

    def test_corrupt_cached_file_is_not_reused(self):
        png = b"\x89PNG\r\n\x1a\nimage-data"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "media" / "namespace" / "release-7" / "cached.png"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"corrupt")
            cached = {"https://example.com/image.png": {"status": "downloaded", "local_path": str(path),
                      "content_type": "image/png", "size": len(png), "sha256": "0" * 64}}
            with patch("project_research.media._fetch_image", return_value=("image/png", png)) as fetch:
                results = collect_release_images("![image](https://example.com/image.png)", tmp, 7,
                                                  existing_media=cached)
            fetch.assert_called_once()
            self.assertEqual(results[0].status, "downloaded")
            self.assertEqual(Path(results[0].local_path).read_bytes(), png)
            self.assertFalse(path.exists())

    def test_size_limit_is_recorded_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp, patch("project_research.media._fetch_image", side_effect=OverflowError("too big")):
            results = collect_release_images("![image](https://example.com/image.png)", tmp, 7)
            self.assertEqual(results[0].status, "skipped-size-limit")


if __name__ == "__main__":
    unittest.main()
