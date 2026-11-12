import json
import unittest

from project_research.github import GitHubClient, GitHubError, HttpResponse, resolve_repository, _GitHubAssetRedirectHandler, _GitHubAPIRedirectHandler
from urllib.request import Request
from tests.helpers import repository, release_payload


class GitHubTests(unittest.TestCase):
    def test_resolve_owner_repo_and_nested_urls(self):
        self.assertEqual(resolve_repository("octo/demo").full_name, "octo/demo")
        self.assertEqual(resolve_repository("https://github.com/octo/demo/releases/tag/v1").full_name, "octo/demo")
        self.assertEqual(resolve_repository("github.com/octo/demo.git").name, "demo")

    def test_rejects_other_hosts_and_missing_repository(self):
        with self.assertRaises(ValueError):
            resolve_repository("https://example.com/octo/demo")
        with self.assertRaises(ValueError):
            resolve_repository("https://github.com/octo")
        with self.assertRaises(ValueError):
            resolve_repository("octo?query/demo")
        with self.assertRaises(ValueError):
            resolve_repository("https://user@github.com/octo/demo")
        with self.assertRaises(ValueError):
            resolve_repository("https://github.com:8443/octo/demo")

    def test_pagination(self):
        calls = []
        def transport(url, headers, timeout):
            calls.append(url)
            if "&page=1" in url:
                return HttpResponse(200, {"link": '<https://api.github.com/repos/octo/demo/releases?per_page=100&page=2>; rel="next"'},
                                    json.dumps([release_payload(1)]).encode())
            return HttpResponse(200, {}, json.dumps([release_payload(2, "v1.1.0")]).encode())
        client = GitHubClient(transport=transport, sleep=lambda _: None)
        records = client.list_releases(repository())
        self.assertEqual([item.native_id for item in records], [1, 2])
        self.assertEqual(len(calls), 2)

    def test_rate_limit_retry(self):
        calls = []
        def transport(url, headers, timeout):
            calls.append(url)
            if len(calls) == 1:
                return HttpResponse(403, {"x-ratelimit-remaining": "0", "retry-after": "0"}, b'{"message":"API rate limit exceeded"}')
            return HttpResponse(200, {}, b'{"ok":true}')
        client = GitHubClient(transport=transport, sleep=lambda _: None)
        payload, _ = client.get_json("https://api.github.com/example")
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(len(calls), 2)

    def test_api_redirect_must_remain_on_api_origin(self):
        request = Request("https://api.github.com/repos/octo/demo", headers={"Authorization": "Bearer secret"})
        handler = _GitHubAPIRedirectHandler()
        with self.assertRaises(GitHubError):
            handler.redirect_request(request, None, 302, "Found", {}, "https://attacker.example/collect")
        redirected = handler.redirect_request(request, None, 301, "Moved", {}, "https://api.github.com/repos/octo/demo-new")
        self.assertEqual(redirected.get_header("Authorization"), "Bearer secret")

    def test_asset_redirect_strips_authorization_across_hosts(self):
        request = Request("https://api.github.com/repos/octo/demo/releases/assets/1",
                          headers={"Authorization": "Bearer secret", "Accept": "application/octet-stream"})
        redirected = _GitHubAssetRedirectHandler().redirect_request(
            request, None, 302, "Found", {}, "https://objects.githubusercontent.com/asset")
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertEqual(redirected.get_header("Accept"), "application/octet-stream")

    def test_rejects_unsafe_pagination_target(self):
        def transport(url, headers, timeout):
            return HttpResponse(200, {"link": '<https://evil.example/steal>; rel="next"'}, b'[]')
        client = GitHubClient(transport=transport)
        with self.assertRaises(GitHubError):
            client.list_releases(repository())

    def test_tag_collection_normalizes_commit_sha(self):
        calls = []
        def transport(url, headers, timeout):
            calls.append(url)
            payload = [{"name": "v1.0.0", "commit": {"sha": "abc123"},
                        "zipball_url": "https://api.github.com/zip", "tarball_url": "https://api.github.com/tar"}]
            return HttpResponse(200, {}, json.dumps(payload).encode())
        client = GitHubClient(transport=transport)
        tags = client.list_tags(repository())
        self.assertEqual(tags[0].name, "v1.0.0")
        self.assertEqual(tags[0].commit_sha, "abc123")
        self.assertIn("/tags?", calls[0])

    def test_auth_error_does_not_expose_token(self):
        def transport(url, headers, timeout):
            return HttpResponse(401, {}, b'{"message":"Bad credentials"}')
        client = GitHubClient(token="secret-value", transport=transport)
        with self.assertRaises(GitHubError) as caught:
            client.get_json("https://api.github.com/example")
        self.assertNotIn("secret-value", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
