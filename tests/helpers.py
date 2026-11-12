from project_research.models import RepositoryRef, normalize_github_release


def repository():
    return RepositoryRef("github", "github.com", "octo", "demo", 42, "https://github.com/octo/demo")


def release_payload(native_id=7, tag="v1.2.0", body="A useful feature", published="2024-03-01T12:00:00Z", assets=None, prerelease=False, draft=False):
    return {
        "id": native_id,
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": body,
        "target_commitish": "main",
        "draft": draft,
        "prerelease": prerelease,
        "created_at": "2024-03-01T10:00:00Z",
        "published_at": published,
        "html_url": f"https://github.com/octo/demo/releases/tag/{tag}",
        "author": {"login": "octo"},
        "assets": assets or [],
    }


def release(**kwargs):
    return normalize_github_release(release_payload(**kwargs), repository(), "2024-03-02T00:00:00Z")
