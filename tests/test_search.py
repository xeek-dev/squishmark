"""Tests for the search service (tokenization, indexing, scoring).

Self-contained pure-function tests against services/search.py, mirroring
the style of tests/test_series.py.
"""

import datetime

from squishmark.models.content import Post
from squishmark.services.search import (
    DEFAULT_LIMIT,
    build_search_index,
    search_index,
    search_posts,
    tokenize,
)


def _post(
    slug: str,
    *,
    title: str | None = None,
    tags: list[str] | None = None,
    description: str = "",
    content: str = "",
    date: datetime.date | None = None,
    draft: bool = False,
) -> Post:
    return Post(
        slug=slug,
        title=title if title is not None else slug.replace("-", " ").title(),
        tags=tags or [],
        description=description,
        content=content,
        date=date,
        draft=draft,
    )


class TestTokenize:
    def test_lowercases(self):
        assert tokenize("Hello WORLD") == {"hello", "world"}

    def test_splits_punctuation_and_hyphens(self):
        assert tokenize("blue-tech: a post!") == {"blue", "tech", "a", "post"}

    def test_keeps_digits(self):
        assert tokenize("python 3.14") == {"python", "3", "14"}

    def test_empty_string(self):
        assert tokenize("") == set()

    def test_punctuation_only(self):
        assert tokenize("--- !!! ...") == set()


class TestFieldWeighting:
    def test_title_outranks_tags_outranks_description_outranks_body(self):
        posts = [
            _post("in-body", content="gumbo recipe steps"),
            _post("in-title", title="Gumbo Night"),
            _post("in-description", description="a gumbo story"),
            _post("in-tags", tags=["gumbo"]),
        ]
        results = search_posts("gumbo", posts)
        assert [r.url for r in results] == [
            "/posts/in-title",
            "/posts/in-tags",
            "/posts/in-description",
            "/posts/in-body",
        ]

    def test_exact_outranks_prefix_in_same_field(self):
        posts = [
            _post("prefix-hit", title="Gumbology Studies"),
            _post("exact-hit", title="Gumbo Recipe"),
        ]
        results = search_posts("gumbo", posts)
        assert [r.url for r in results] == ["/posts/exact-hit", "/posts/prefix-hit"]


class TestPrefixMatching:
    def test_prefix_matches(self):
        posts = [_post("python-post", title="Python Tips")]
        assert len(search_posts("pyth", posts)) == 1

    def test_mid_word_substring_does_not_match(self):
        posts = [_post("python-post", title="Python Tips")]
        assert search_posts("ython", posts) == []


class TestMultiTokenAnd:
    def test_all_tokens_must_match(self):
        posts = [_post("gumbo-post", title="Gumbo Recipe", content="cooking at midnight")]
        assert len(search_posts("gumbo midnight", posts)) == 1
        assert search_posts("gumbo zeppelin", posts) == []

    def test_tokens_may_match_different_fields(self):
        posts = [_post("mixed", title="Gumbo", tags=["cooking"])]
        assert len(search_posts("gumbo cooking", posts)) == 1


class TestRankingTieBreaks:
    def test_equal_scores_order_by_date_desc_dateless_last(self):
        posts = [
            _post("old", title="Gumbo", date=datetime.date(2026, 1, 1)),
            _post("dateless", title="Gumbo"),
            _post("new", title="Gumbo", date=datetime.date(2026, 3, 1)),
        ]
        results = search_posts("gumbo", posts)
        assert [r.url for r in results] == ["/posts/new", "/posts/old", "/posts/dateless"]


class TestLimit:
    def _many(self, n: int) -> list[Post]:
        return [_post(f"post-{i}", title=f"Gumbo {i}", date=datetime.date(2026, 1, 1 + i)) for i in range(n)]

    def test_default_limit(self):
        assert len(search_posts("gumbo", self._many(12))) == DEFAULT_LIMIT

    def test_explicit_limit(self):
        assert len(search_posts("gumbo", self._many(12), limit=3)) == 3


class TestDraftPassthrough:
    def test_scorer_does_not_filter_drafts(self):
        """Draft gating is the caller's job; the scorer returns drafts flagged."""
        posts = [_post("secret", title="Gumbo Secrets", draft=True)]
        results = search_posts("gumbo", posts)
        assert len(results) == 1
        assert results[0].draft is True


class TestShortQueries:
    def test_empty_query(self):
        assert search_posts("", [_post("a", title="Gumbo")]) == []

    def test_one_char_query(self):
        assert search_posts("g", [_post("a", title="Gumbo")]) == []

    def test_whitespace_query(self):
        assert search_posts("   ", [_post("a", title="Gumbo")]) == []


class TestResultShape:
    def test_fields_carried_through(self):
        post = _post(
            "shaped",
            title="Gumbo Guide",
            tags=["cooking", "aliens"],
            description="A short excerpt.",
            content="body text",
            date=datetime.date(2026, 2, 15),
        )
        result = search_posts("gumbo", [post])[0]
        assert result.url == "/posts/shaped"
        assert result.title == "Gumbo Guide"
        assert result.tags == ["cooking", "aliens"]
        assert result.excerpt == "A short excerpt."
        assert result.date == datetime.date(2026, 2, 15)
        assert result.draft is False

    def test_search_index_matches_search_posts(self):
        posts = [_post("a", title="Gumbo")]
        index = build_search_index(posts)
        assert search_index("gumbo", index) == search_posts("gumbo", posts)
