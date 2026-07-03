"""Shared fixtures for HTTP integration tests.

These exercise the real ``create_app()`` (lifespan, SessionMiddleware, the
custom HTML 404 handler) via ``TestClient`` used as a context manager. The
GitHub content layer is replaced with an in-memory :class:`FakeGitHubService`
so no network access is required.

The autouse :func:`_reset_environment` fixture is the linchpin: it clears the
settings cache and, for the HTTP integration modules, injects a
:class:`FakeGitHubService` into the lifespan-built service container by patching
the container's ``create_github_service`` factory.
"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

import squishmark.services.container as container_module
from squishmark.config import get_settings
from squishmark.main import create_app
from squishmark.services.github import GitHubBinaryFile, GitHubFile


class FakeGitHubService:
    """Dict-backed stand-in for :class:`~squishmark.services.github.GitHubService`.

    Matches the real public coroutine signatures so it can be dropped into the
    service container in place of the real GitHub service. ``list_directory``
    derives a directory's children from the keys of ``files`` (and
    ``binary_files``) by prefix match, mirroring how the real service lists a
    GitHub/local directory.
    """

    def __init__(
        self,
        files: dict[str, str] | None = None,
        binary_files: dict[str, bytes] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.files: dict[str, str] = dict(files or {})
        self.binary_files: dict[str, bytes] = dict(binary_files or {})
        self.config: dict[str, Any] | None = config

    async def get_file(self, path: str, ref: str = "main", use_cache: bool = True) -> GitHubFile | None:
        content = self.files.get(path)
        if content is None:
            return None
        return GitHubFile(path=path, content=content)

    async def get_binary_file(self, path: str, ref: str = "main", use_cache: bool = True) -> GitHubBinaryFile | None:
        content = self.binary_files.get(path)
        if content is None:
            return None
        return GitHubBinaryFile(path=path, content=content, content_type=_content_type_for(path))

    async def list_directory(self, path: str, ref: str = "main", use_cache: bool = True) -> list[str]:
        prefix = f"{path.rstrip('/')}/"
        children: set[str] = set()
        for key in (*self.files, *self.binary_files):
            if key.startswith(prefix):
                remainder = key[len(prefix) :]
                # Only direct children (no nested subdirectories), matching the
                # real service which lists a single directory level.
                if "/" not in remainder:
                    children.add(key)
        return sorted(children)

    async def get_config(self, use_cache: bool = True) -> dict[str, Any] | None:
        return self.config

    async def close(self) -> None:
        return None


_CONTENT_TYPES = {
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".css": "text/css",
    ".js": "application/javascript",
}


def _content_type_for(path: str) -> str:
    for ext, ctype in _CONTENT_TYPES.items():
        if path.lower().endswith(ext):
            return ctype
    return "application/octet-stream"


# --- Default content -------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "site": {
        "title": "Test Blog",
        "url": "https://test.example.com",
        "description": "A blog for integration tests",
        "author": "Test Author",
    },
    "theme": {"name": "default"},
    "posts": {"per_page": 2},
}


def _post_body(title: str, *, draft: bool = False) -> str:
    draft_line = "draft: true\n" if draft else ""
    return f"---\ntitle: {title}\n{draft_line}---\n\n# {title}\n\nBody text for {title}.\n"


def _page_body(title: str, *, visibility: str = "public") -> str:
    return f"---\ntitle: {title}\nvisibility: {visibility}\n---\n\n# {title}\n\nPage body.\n"


def default_files() -> dict[str, str]:
    """Default published/draft posts (enough to paginate) plus pages.

    Filenames carry ``YYYY-MM-DD-`` prefixes so slugs strip the date and dates
    sort newest-first. ``per_page=2`` plus five published posts yields three
    pages for anonymous users.
    """
    return {
        "posts/2026-01-05-post-five.md": _post_body("Post Five"),
        "posts/2026-01-04-post-four.md": _post_body("Post Four"),
        "posts/2026-01-03-post-three.md": _post_body("Post Three"),
        "posts/2026-01-02-post-two.md": _post_body("Post Two"),
        "posts/2026-01-01-post-one.md": _post_body("Post One"),
        "posts/2026-01-06-secret-draft.md": _post_body("Secret Draft", draft=True),
        "pages/about.md": _page_body("About"),
        "pages/secret.md": _page_body("Secret", visibility="hidden"),
    }


def default_binary_files() -> dict[str, bytes]:
    """A favicon so :class:`FaviconDetector` and ``/favicon.ico`` resolve."""
    # 1x1 transparent PNG.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6360000002000154a24f230000000049454e44ae426082"
    )
    return {"static/favicon.png": png}


# --- Content factory -------------------------------------------------------


@pytest.fixture
def make_content() -> Callable[..., FakeGitHubService]:
    """Factory producing a :class:`FakeGitHubService` with overridable content.

    Defaults to the standard fixture content; pass ``files``/``binary_files``/
    ``config`` to replace any slice for a given test.
    """

    def _factory(
        files: dict[str, str] | None = None,
        binary_files: dict[str, bytes] | None = None,
        config: dict[str, Any] | None = None,
    ) -> FakeGitHubService:
        return FakeGitHubService(
            files=default_files() if files is None else files,
            binary_files=default_binary_files() if binary_files is None else binary_files,
            config=DEFAULT_CONFIG if config is None else config,
        )

    return _factory


# --- Autouse environment reset --------------------------------------------


_INTEGRATION_MODULES = (
    "test_routes_posts",
    "test_routes_pages",
    "test_routes_admin",
    "test_routes_webhooks",
    "test_routes_search",
)


@pytest.fixture(autouse=True)
def _reset_environment(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    make_content: Callable[..., FakeGitHubService],
) -> Iterator[FakeGitHubService | None]:
    """Per-test isolation of settings and (for integration modules) the fake.

    For the HTTP integration modules this pins the environment the real
    ``create_app()`` reads (file-based SQLite — ``:memory:`` loses tables across
    the separate connections SQLAlchemy's async pool opens — plus secret/admin/
    webhook config) and injects a default fake GitHub service into the
    lifespan-built container by patching ``create_github_service``.

    The env-pinning is scoped to this PR's integration modules so it never
    pollutes ``os.environ`` for the pre-existing suites — several of which build
    a bare ``Settings()`` and assert on environment-derived defaults.
    """
    is_integration = request.module.__name__.rsplit(".", 1)[-1] in _INTEGRATION_MODULES

    if is_integration:
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("ADMIN_USERS", "admin-user")
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-webhook-secret")
        monkeypatch.setenv("GITHUB_CONTENT_REPO", "testowner/testcontent")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("DEV_SKIP_AUTH", "false")

    get_settings.cache_clear()

    fake: FakeGitHubService | None = None
    if is_integration:
        fake = make_content()
        monkeypatch.setattr(container_module, "create_github_service", lambda settings, cache: fake)

    yield fake

    get_settings.cache_clear()


# --- Clients ---------------------------------------------------------------

_SEED_ROUTE = "/_test/seed-session"


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Anonymous client over the real ``create_app()`` with lifespan active."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_client() -> Iterator[TestClient]:
    """Client whose session is seeded with an admin user.

    A test-only ``/_test/seed-session`` route writes ``request.session["user"]``;
    TestClient's cookie jar then carries the signed session cookie on every
    subsequent request. Pattern proven in ``test_csrf_integration.py``.

    Uses an ``https`` base URL: with ``DEBUG=false`` the real app sets
    ``SessionMiddleware(https_only=True)``, so the session cookie is only sent
    back over a secure scheme.
    """
    app = create_app()

    from fastapi import Request

    @app.get(_SEED_ROUTE)
    async def _seed(request: Request) -> dict:
        request.session["user"] = {"login": "admin-user"}
        return {"ok": True}

    with TestClient(app, base_url="https://testserver") as test_client:
        resp = test_client.get(_SEED_ROUTE)
        assert resp.status_code == 200, resp.text
        yield test_client


@pytest.fixture
def seeded_client() -> Iterator[Callable[[dict[str, Any]], TestClient]]:
    """Factory yielding an https TestClient whose session is seeded with
    arbitrary data (e.g. a non-admin ``user``).

    Each call builds a fresh app/client; all created clients are closed at
    teardown. Used for the "wrong user → 403" admin case.
    """
    clients: list[TestClient] = []

    def _make(session_data: dict[str, Any]) -> TestClient:
        app = create_app()

        from fastapi import Request

        @app.get(_SEED_ROUTE)
        async def _seed(request: Request) -> dict:
            for key, value in session_data.items():
                request.session[key] = value
            return {"ok": True}

        test_client = TestClient(app, base_url="https://testserver")
        test_client.__enter__()
        # Track immediately so teardown closes the client even if seeding fails.
        clients.append(test_client)
        resp = test_client.get(_SEED_ROUTE)
        assert resp.status_code == 200, resp.text
        return test_client

    yield _make

    for test_client in clients:
        test_client.__exit__(None, None, None)


@pytest.fixture
def csrf_token() -> Callable[[TestClient], str]:
    """Return a helper that fetches the CSRF token for an admin client."""

    def _get(authed_client: TestClient) -> str:
        resp = authed_client.get("/admin/csrf")
        assert resp.status_code == 200, resp.text
        return resp.json()["csrf_token"]

    return _get
