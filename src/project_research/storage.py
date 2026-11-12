"""SQLite persistence for canonical release records, raw observations, and FTS."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import hashlib
import json
import os
import sqlite3

from .models import RepositoryRef, ReleaseRecord, TagRecord, canonical_json

SCHEMA_VERSION = 1


def default_database_path() -> Path:
    root = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return root / "project-research" / "releases.sqlite3"


class ReleaseStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ReleaseStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            with self.connection:
                yield
        except Exception:
            raise

    def _initialize(self) -> None:
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS repositories (
                repository_key TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                host TEXT NOT NULL,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                native_id INTEGER,
                html_url TEXT,
                last_synced_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tags (
                repository_key TEXT NOT NULL REFERENCES repositories(repository_key) ON DELETE CASCADE,
                name TEXT NOT NULL,
                commit_sha TEXT,
                zipball_url TEXT,
                tarball_url TEXT,
                retrieved_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                PRIMARY KEY(repository_key, name)
            );
            CREATE TABLE IF NOT EXISTS releases (
                repository_key TEXT NOT NULL REFERENCES repositories(repository_key) ON DELETE CASCADE,
                native_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                name TEXT,
                body TEXT,
                target_commitish TEXT,
                draft INTEGER NOT NULL,
                prerelease INTEGER NOT NULL,
                created_at TEXT,
                published_at TEXT,
                html_url TEXT,
                author_login TEXT,
                retrieved_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                raw_sha256 TEXT NOT NULL,
                PRIMARY KEY (repository_key, native_id)
            );
            CREATE TABLE IF NOT EXISTS release_observations (
                observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_key TEXT NOT NULL,
                release_native_id INTEGER NOT NULL,
                retrieved_at TEXT NOT NULL,
                raw_sha256 TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                UNIQUE(repository_key, release_native_id, raw_sha256),
                FOREIGN KEY(repository_key, release_native_id)
                    REFERENCES releases(repository_key, native_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS assets (
                repository_key TEXT NOT NULL,
                release_native_id INTEGER NOT NULL,
                native_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                label TEXT,
                content_type TEXT,
                size INTEGER,
                state TEXT,
                download_count INTEGER,
                created_at TEXT,
                updated_at TEXT,
                browser_download_url TEXT,
                digest TEXT,
                raw_json TEXT NOT NULL,
                PRIMARY KEY(repository_key, release_native_id, native_id),
                FOREIGN KEY(repository_key, release_native_id)
                    REFERENCES releases(repository_key, native_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS release_media (
                repository_key TEXT NOT NULL,
                release_native_id INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                status TEXT NOT NULL,
                local_path TEXT,
                content_type TEXT,
                size INTEGER,
                sha256 TEXT,
                detail TEXT,
                retrieved_at TEXT NOT NULL,
                PRIMARY KEY(repository_key, release_native_id, source_url),
                FOREIGN KEY(repository_key, release_native_id)
                    REFERENCES releases(repository_key, native_id) ON DELETE CASCADE
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS release_search USING fts5(
                repository_key UNINDEXED,
                native_id UNINDEXED,
                tag_name,
                name,
                body,
                html_url
            );
            CREATE INDEX IF NOT EXISTS idx_releases_date
                ON releases(repository_key, published_at, created_at);
            CREATE INDEX IF NOT EXISTS idx_assets_name
                ON assets(repository_key, name);
        """)
        row = self.connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        if row is None:
            self.connection.execute("INSERT INTO metadata(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        elif int(row["value"]) != SCHEMA_VERSION:
            raise RuntimeError(f"unsupported database schema version {row['value']}; expected {SCHEMA_VERSION}")

    def upsert_repository(self, repository: RepositoryRef, synced_at: str) -> None:
        self.connection.execute("""
            INSERT INTO repositories(repository_key,provider,host,owner,name,native_id,html_url,last_synced_at)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(repository_key) DO UPDATE SET
              native_id=excluded.native_id, html_url=excluded.html_url, last_synced_at=excluded.last_synced_at
        """, (repository.key, repository.provider, repository.host, repository.owner,
              repository.name, repository.native_id, repository.html_url, synced_at))

    def save_releases(self, repository: RepositoryRef, releases: list[ReleaseRecord], synced_at: str) -> None:
        with self.transaction():
            self.upsert_repository(repository, synced_at)
            for release in releases:
                raw_json = canonical_json(release.raw)
                raw_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
                self.connection.execute("""
                    INSERT INTO releases(repository_key,native_id,tag_name,name,body,target_commitish,draft,
                      prerelease,created_at,published_at,html_url,author_login,retrieved_at,raw_json,raw_sha256)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(repository_key,native_id) DO UPDATE SET
                      tag_name=excluded.tag_name,name=excluded.name,body=excluded.body,
                      target_commitish=excluded.target_commitish,draft=excluded.draft,
                      prerelease=excluded.prerelease,created_at=excluded.created_at,
                      published_at=excluded.published_at,html_url=excluded.html_url,
                      author_login=excluded.author_login,retrieved_at=excluded.retrieved_at,
                      raw_json=excluded.raw_json,raw_sha256=excluded.raw_sha256
                """, (release.repository_key, release.native_id, release.tag_name, release.name,
                      release.body, release.target_commitish, int(release.draft), int(release.prerelease),
                      release.created_at, release.published_at, release.html_url, release.author_login,
                      release.retrieved_at, raw_json, raw_hash))
                self.connection.execute("""
                    INSERT OR IGNORE INTO release_observations(repository_key,release_native_id,retrieved_at,raw_sha256,raw_json)
                    VALUES(?,?,?,?,?)
                """, (release.repository_key, release.native_id, release.retrieved_at, raw_hash, raw_json))
                self.connection.execute("DELETE FROM assets WHERE repository_key=? AND release_native_id=?",
                                         (release.repository_key, release.native_id))
                for asset in release.assets:
                    self.connection.execute("""
                        INSERT INTO assets(repository_key,release_native_id,native_id,name,label,content_type,size,state,
                          download_count,created_at,updated_at,browser_download_url,digest,raw_json)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (release.repository_key, release.native_id, asset.native_id, asset.name, asset.label,
                          asset.content_type, asset.size, asset.state, asset.download_count, asset.created_at,
                          asset.updated_at, asset.browser_download_url, asset.digest, canonical_json(asset.raw)))
                self.connection.execute("DELETE FROM release_search WHERE repository_key=? AND native_id=?",
                                         (release.repository_key, str(release.native_id)))
                self.connection.execute("""
                    INSERT INTO release_search(repository_key,native_id,tag_name,name,body,html_url)
                    VALUES(?,?,?,?,?,?)
                """, (release.repository_key, str(release.native_id), release.tag_name,
                      release.name or "", release.body or "", release.html_url or ""))

    def save_tags(self, repository: RepositoryRef, tags: list[TagRecord], synced_at: str) -> None:
        with self.transaction():
            self.upsert_repository(repository, synced_at)
            for tag in tags:
                self.connection.execute("""
                    INSERT INTO tags(repository_key,name,commit_sha,zipball_url,tarball_url,retrieved_at,raw_json)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(repository_key,name) DO UPDATE SET
                      commit_sha=excluded.commit_sha,zipball_url=excluded.zipball_url,
                      tarball_url=excluded.tarball_url,retrieved_at=excluded.retrieved_at,raw_json=excluded.raw_json
                """, (tag.repository_key, tag.name, tag.commit_sha, tag.zipball_url,
                      tag.tarball_url, tag.retrieved_at, canonical_json(tag.raw)))

    def list_tags(self, repository_key: str) -> list[dict[str, object]]:
        rows = self.connection.execute("""
            SELECT t.*, CASE WHEN EXISTS (
                SELECT 1 FROM releases r WHERE r.repository_key=t.repository_key AND r.tag_name=t.name AND r.draft=0
            ) THEN 1 ELSE 0 END AS has_release
            FROM tags t WHERE t.repository_key=? ORDER BY t.name
        """, (repository_key,)).fetchall()
        return [dict(row) for row in rows]

    def list_releases(self, repository_key: str) -> list[ReleaseRecord]:
        from .models import ReleaseAsset
        rows = self.connection.execute("SELECT * FROM releases WHERE repository_key=?", (repository_key,)).fetchall()
        result: list[ReleaseRecord] = []
        for row in rows:
            asset_rows = self.connection.execute("SELECT * FROM assets WHERE repository_key=? AND release_native_id=? ORDER BY name",
                                                  (repository_key, row["native_id"])).fetchall()
            assets = tuple(ReleaseAsset(
                provider="github", native_id=a["native_id"], name=a["name"], label=a["label"],
                content_type=a["content_type"], size=a["size"], state=a["state"],
                download_count=a["download_count"], created_at=a["created_at"], updated_at=a["updated_at"],
                browser_download_url=a["browser_download_url"], digest=a["digest"], raw=json.loads(a["raw_json"])
            ) for a in asset_rows)
            result.append(ReleaseRecord(
                provider="github", repository_key=row["repository_key"], native_id=row["native_id"],
                tag_name=row["tag_name"], name=row["name"], body=row["body"],
                target_commitish=row["target_commitish"], draft=bool(row["draft"]), prerelease=bool(row["prerelease"]),
                created_at=row["created_at"], published_at=row["published_at"], html_url=row["html_url"],
                author_login=row["author_login"], assets=assets, retrieved_at=row["retrieved_at"],
                raw=json.loads(row["raw_json"])
            ))
        return result

    def find_repository(self, repository_key: str) -> RepositoryRef | None:
        row = self.connection.execute("SELECT * FROM repositories WHERE repository_key=?", (repository_key,)).fetchone()
        if row is None:
            return None
        return RepositoryRef(row["provider"], row["host"], row["owner"], row["name"], row["native_id"], row["html_url"])

    def rebuild_search_index(self, repository_key: str | None = None) -> int:
        with self.transaction():
            if repository_key is None:
                self.connection.execute("DELETE FROM release_search")
                self.connection.execute("""
                    INSERT INTO release_search(repository_key,native_id,tag_name,name,body,html_url)
                    SELECT repository_key,CAST(native_id AS TEXT),tag_name,COALESCE(name,''),COALESCE(body,''),COALESCE(html_url,'')
                    FROM releases
                """)
                row = self.connection.execute("SELECT count(*) AS n FROM release_search").fetchone()
            else:
                self.connection.execute("DELETE FROM release_search WHERE repository_key=?", (repository_key,))
                self.connection.execute("""
                    INSERT INTO release_search(repository_key,native_id,tag_name,name,body,html_url)
                    SELECT repository_key,CAST(native_id AS TEXT),tag_name,COALESCE(name,''),COALESCE(body,''),COALESCE(html_url,'')
                    FROM releases WHERE repository_key=?
                """, (repository_key,))
                row = self.connection.execute("SELECT count(*) AS n FROM release_search WHERE repository_key=?", (repository_key,)).fetchone()
            return int(row["n"])

    def search(self, query: str, repository_key: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        if not query.strip():
            raise ValueError("search query must not be empty")
        if limit < 1:
            raise ValueError("search limit must be at least 1")
        sql = """
            SELECT repository_key,native_id,tag_name,name,body,html_url,bm25(release_search) AS rank
            FROM release_search WHERE release_search MATCH ?
        """
        params: list[object] = [query]
        if repository_key:
            sql += " AND repository_key=?"
            params.append(repository_key)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        try:
            rows = self.connection.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            raise ValueError(f"invalid full-text search query: {exc}") from exc
        return [dict(row) for row in rows]

    def find_asset(self, repository_key: str, selector: str) -> list[sqlite3.Row]:
        if selector.isdecimal():
            return self.connection.execute("""
                SELECT a.*,r.tag_name,r.html_url AS release_url,r.published_at
                FROM assets a JOIN releases r ON r.repository_key=a.repository_key AND r.native_id=a.release_native_id
                WHERE a.repository_key=? AND a.native_id=? ORDER BY r.published_at DESC
            """, (repository_key, int(selector))).fetchall()
        return self.connection.execute("""
            SELECT a.*,r.tag_name,r.html_url AS release_url,r.published_at
            FROM assets a JOIN releases r ON r.repository_key=a.repository_key AND r.native_id=a.release_native_id
            WHERE a.repository_key=? AND a.name=? ORDER BY r.published_at DESC
        """, (repository_key, selector)).fetchall()

    def record_media(self, repository_key: str, release_id: int, results, retrieved_at: str) -> None:
        with self.transaction():
            for item in results:
                self.connection.execute("""
                    INSERT INTO release_media(repository_key,release_native_id,source_url,status,local_path,
                      content_type,size,sha256,detail,retrieved_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(repository_key,release_native_id,source_url) DO UPDATE SET
                      status=excluded.status,local_path=excluded.local_path,content_type=excluded.content_type,
                      size=excluded.size,sha256=excluded.sha256,detail=excluded.detail,retrieved_at=excluded.retrieved_at
                """, (repository_key, release_id, item.source_url, item.status, item.local_path,
                      item.content_type, item.size, item.sha256, item.detail, retrieved_at))

    def list_media(self, repository_key: str, release_id: int | None = None) -> list[dict[str, object]]:
        sql = "SELECT * FROM release_media WHERE repository_key=?"
        params: list[object] = [repository_key]
        if release_id is not None:
            sql += " AND release_native_id=?"
            params.append(release_id)
        sql += " ORDER BY release_native_id,source_url"
        return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def observation_count(self, repository_key: str, release_id: int) -> int:
        row = self.connection.execute("SELECT count(*) AS n FROM release_observations WHERE repository_key=? AND release_native_id=?",
                                      (repository_key, release_id)).fetchone()
        return int(row["n"])
