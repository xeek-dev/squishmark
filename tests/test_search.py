"""Tests for the search service (tokenization, indexing, scoring).

Self-contained pure-function tests against services/search.py, mirroring
the style of tests/test_series.py.
"""

import datetime

from squishmark.models.content import Post
from squishmark.services.search import (
    DEFAULT_LIMIT,
    build_search_index,
    query_index,
    search_posts,
    strip_markdown_noise,
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
        # "frig" sits inside "refrigerator" but is neither a prefix of it
        # nor within the fuzzy ratio threshold (0.5), so it must not match.
        posts = [_post("fridge-post", title="Refrigerator Repair")]
        assert search_posts("frig", posts) == []


class TestFuzzyMatching:
    def test_single_char_typo_matches(self):
        posts = [_post("gumbo-post", title="Gumbo Recipe")]
        results = search_posts("gumob", posts)
        assert [r.url for r in results] == ["/posts/gumbo-post"]

    def test_missing_char_typo_matches(self):
        posts = [_post("space-post", title="Intergalactic Travel")]
        assert len(search_posts("intergalatic", posts)) == 1

    def test_near_prefix_typo_matches_via_fuzzy(self):
        # "ython" is not a prefix of "python" but is one edit away
        # (ratio 0.909), so the fuzzy tier picks it up.
        posts = [_post("python-post", title="Python Tips")]
        assert len(search_posts("ython", posts)) == 1

    def test_ratio_exactly_at_threshold_matches(self):
        # ratio("gumbz", "gumbo") == 0.8, the inclusive threshold.
        posts = [_post("gumbo-post", title="Gumbo Recipe")]
        assert len(search_posts("gumbz", posts)) == 1

    def test_ratio_below_threshold_does_not_match(self):
        # ratio("gumb", "gump") == 0.75, just under the threshold.
        posts = [_post("gump-post", title="Gump Tales")]
        assert search_posts("gumb", posts) == []

    def test_short_query_token_never_fuzzy_matches(self):
        # ratio("tew", "stew") == 0.857, above the threshold, but tokens
        # under 4 chars are excluded from the fuzzy tier.
        posts = [_post("stew-post", title="Stew Night")]
        assert search_posts("tew", posts) == []

    def test_fuzzy_ranks_below_exact_and_prefix_in_same_field(self):
        posts = [
            _post("fuzzy-hit", title="Gumbz Files"),
            _post("prefix-hit", title="Gumbology Studies"),
            _post("exact-hit", title="Gumbo Recipe"),
        ]
        results = search_posts("gumbo", posts)
        assert [r.url for r in results] == [
            "/posts/exact-hit",
            "/posts/prefix-hit",
            "/posts/fuzzy-hit",
        ]

    def test_fuzzy_never_outranks_real_match_across_fields(self):
        # A fuzzy title hit carries more weight than an exact body hit,
        # but posts needing fuzzy still sort behind real matches.
        posts = [
            _post("fuzzy-title", title="Gumbz"),
            _post("exact-body", title="Cooking Notes", content="gumbo simmering all day"),
        ]
        results = search_posts("gumbo", posts)
        assert [r.url for r in results] == ["/posts/exact-body", "/posts/fuzzy-title"]

    def test_fuzzy_token_counts_toward_and_semantics(self):
        posts = [_post("gumbo-post", title="Gumbo Recipe", content="cooking at midnight")]
        assert len(search_posts("gumob midnight", posts)) == 1
        assert search_posts("gumob zeppelin", posts) == []


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

    def test_query_index_matches_search_posts(self):
        posts = [_post("a", title="Gumbo")]
        index = build_search_index(posts)
        assert query_index("gumbo", index) == search_posts("gumbo", posts)


class TestBodyMarkdownStripping:
    def test_link_url_not_indexed_but_link_text_is(self):
        posts = [_post("linked", content="Read [the gumbo guide](https://example.com/gumbo-guide.html) today")]
        assert len(search_posts("guide", posts)) == 1
        assert search_posts("example", posts) == []
        assert search_posts("https", posts) == []

    def test_image_url_not_indexed_but_alt_text_is(self):
        posts = [_post("pic", content="![gumbo pot photo](/static/images/pot-final.png)")]
        assert len(search_posts("photo", posts)) == 1
        assert search_posts("png", posts) == []
        assert search_posts("static", posts) == []

    def test_bare_url_not_indexed(self):
        posts = [_post("bare", content="See https://gumbo-archive.example.org/recipes for more")]
        assert search_posts("archive", posts) == []
        assert search_posts("recipes", posts) == []

    def test_reference_link_definition_not_indexed(self):
        posts = [_post("ref", content="Try the stew[1]\n\n[1]: https://example.com/stew-details\n")]
        assert search_posts("details", posts) == []
        assert len(search_posts("stew", posts)) == 1

    def test_html_tags_not_indexed_but_their_text_is(self):
        posts = [_post("html", content='<div class="callout">gumbo tips inside</div>')]
        assert len(search_posts("tips", posts)) == 1
        assert search_posts("callout", posts) == []
        assert search_posts("div", posts) == []

    def test_code_block_text_stays_searchable(self):
        posts = [_post("code", content="```python\ndef make_roux(flour):\n    return flour\n```")]
        assert len(search_posts("roux", posts)) == 1
        assert len(search_posts("flour", posts)) == 1

    def test_strip_preserves_plain_prose(self):
        assert strip_markdown_noise("plain gumbo prose") == "plain gumbo prose"

    def test_title_and_description_not_stripped(self):
        """Stripping applies to the body only; other fields index as-is."""
        posts = [_post("t", title="The https survival guide", description="all about png files")]
        assert len(search_posts("https", posts)) == 1
        assert len(search_posts("png", posts)) == 1
