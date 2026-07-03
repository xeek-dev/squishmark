"""Server-side post search: tokenization, indexing, and scoring.

Pure and synchronous so the scoring logic is directly unit-testable
(mirrors ``build_series_context`` in services/content.py). Draft gating is
the caller's responsibility: index the post list appropriate for the
audience (``get_all_posts(include_drafts=...)``); the scorer itself never
filters drafts.
"""

import datetime
import difflib
import re
from dataclasses import dataclass

from pydantic import BaseModel

from squishmark.models.content import Post
from squishmark.services.container import Services
from squishmark.services.content import get_cached_posts

MIN_QUERY_LENGTH = 2
DEFAULT_LIMIT = 8

# Audience-separated cache keys. The "all" index includes drafts and must
# only ever be read for admin requests — sharing one key would leak draft
# titles/excerpts to anonymous visitors. /search responses themselves are
# never cached for the same reason.
SEARCH_INDEX_PUBLISHED_KEY = "search:index:published"
SEARCH_INDEX_ALL_KEY = "search:index:all"

_WORD_RE = re.compile(r"[a-z0-9]+")

# Markdown noise stripped from post bodies before tokenization, so URLs,
# HTML tags, and link targets don't pollute the index ("http"/"png" must
# not match every post). Code-block *text* is deliberately kept searchable
# — readers search for function names and commands that only appear in
# code. Image regex runs before link regex ("![...](...)" contains link
# syntax); bare-URL regex runs last, after link targets are already gone.
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_REF_DEF_RE = re.compile(r"^[ \t]*\[[^\]]+\]:\s+\S+.*$", re.MULTILINE)
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_BARE_URL_RE = re.compile(r"(?:https?://|www\.)\S+")

# Presence-based weights per (field, tier): exact, prefix, fuzzy. Exact
# beats prefix beats fuzzy within a field; title beats tags beats
# description beats body across fields. No term frequency: long bodies
# must not outrank a title hit. Weights alone cannot make every fuzzy hit
# rank below every real hit across fields (a fuzzy title would outscore an
# exact body), so query_index additionally sorts posts that needed any
# fuzzy match behind posts matched entirely by exact/prefix; these weights
# only order posts within the same class.
_WEIGHTS = {
    "title": (12, 8, 6),
    "tags": (10, 6, 4),
    "description": (5, 3, 2),
    "body": (2, 1, 1),
}

# Fuzzy tier thresholds. Tokens shorter than 4 chars are excluded: a
# single edit rewrites too much of a short token and false positives
# dominate (e.g. "cat" would match "car").
FUZZY_MIN_TOKEN_LENGTH = 4
FUZZY_RATIO_THRESHOLD = 0.8


def tokenize(text: str) -> set[str]:
    """Lowercase and split text into a set of word tokens.

    Splits on anything outside [a-z0-9], so hyphenated and punctuated
    terms match their parts ("blue-tech" -> {"blue", "tech"}).
    """
    return set(_WORD_RE.findall(text.lower()))


def strip_markdown_noise(text: str) -> str:
    """Reduce markdown to its searchable text.

    Keeps link text and image alt text but drops their URL targets,
    reference-link definitions, HTML tags, and bare URLs. Markdown
    punctuation (``#``, ``*``, backticks) needs no handling — the
    tokenizer already splits it away.
    """
    text = _MD_IMAGE_RE.sub(r"\1", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _MD_REF_DEF_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    return _BARE_URL_RE.sub(" ", text)


class SearchResult(BaseModel):
    """One search hit, shaped for the /search JSON response."""

    title: str
    url: str
    date: datetime.date | None
    tags: list[str]
    excerpt: str
    draft: bool


@dataclass(frozen=True)
class IndexedPost:
    """A post pre-tokenized per field, with its result payload prebuilt."""

    result: SearchResult
    title_tokens: frozenset[str]
    tag_tokens: frozenset[str]
    description_tokens: frozenset[str]
    body_tokens: frozenset[str]


def build_search_index(posts: list[Post]) -> list[IndexedPost]:
    """Tokenize posts once so per-query scoring is set lookups only."""
    index: list[IndexedPost] = []
    for post in posts:
        index.append(
            IndexedPost(
                result=SearchResult(
                    title=post.title,
                    url=post.url,
                    date=post.date,
                    tags=post.tags,
                    excerpt=post.description,
                    draft=post.draft,
                ),
                title_tokens=frozenset(tokenize(post.title)),
                tag_tokens=frozenset(tokenize(" ".join(post.tags))),
                description_tokens=frozenset(tokenize(post.description)),
                body_tokens=frozenset(tokenize(strip_markdown_noise(post.content))),
            )
        )
    return index


def _fuzzy_matches(query_token: str, field_tokens: frozenset[str]) -> bool:
    """True when any field token is within FUZZY_RATIO_THRESHOLD of the query token."""
    if len(query_token) < FUZZY_MIN_TOKEN_LENGTH:
        return False
    # seq2 is the cached side of SequenceMatcher, so fix the query token
    # there and swap candidates through seq1. real_quick_ratio is a cheap
    # upper bound that skips most candidates before the O(n*m) ratio call.
    matcher = difflib.SequenceMatcher(None, "", query_token)
    for token in field_tokens:
        matcher.set_seq1(token)
        if matcher.real_quick_ratio() >= FUZZY_RATIO_THRESHOLD and matcher.ratio() >= FUZZY_RATIO_THRESHOLD:
            return True
    return False


def _field_score(query_token: str, field_tokens: frozenset[str], exact_weight: int, prefix_weight: int) -> int:
    """Score one query token against one field: exact tier wins over prefix."""
    if query_token in field_tokens:
        return exact_weight
    if any(token.startswith(query_token) for token in field_tokens):
        return prefix_weight
    return 0


def _score_post(query_tokens: list[str], indexed: IndexedPost) -> tuple[int, bool]:
    """Sum field scores per query token; total 0 when any token matches nothing (AND).

    Fuzzy is a pure fallback: it is only evaluated for a token with no
    exact/prefix match in any field, so fuzzy hits never perturb ordering
    among real-match posts and cost nothing on queries with real hits.
    Returns (total, used_fuzzy); used_fuzzy is True when any token needed
    the fallback.
    """
    fields = (
        (indexed.title_tokens, *_WEIGHTS["title"]),
        (indexed.tag_tokens, *_WEIGHTS["tags"]),
        (indexed.description_tokens, *_WEIGHTS["description"]),
        (indexed.body_tokens, *_WEIGHTS["body"]),
    )
    total = 0
    used_fuzzy = False
    for query_token in query_tokens:
        token_score = sum(
            _field_score(query_token, field_tokens, exact, prefix) for field_tokens, exact, prefix, _ in fields
        )
        if token_score == 0:
            token_score = sum(
                fuzzy for field_tokens, _, _, fuzzy in fields if _fuzzy_matches(query_token, field_tokens)
            )
            if token_score == 0:
                return 0, False
            used_fuzzy = True
        total += token_score
    return total, used_fuzzy


def query_index(query: str, index: list[IndexedPost], limit: int = DEFAULT_LIMIT) -> list[SearchResult]:
    """Rank indexed posts against the query; top ``limit`` results.

    Every query token must match somewhere (exact, prefix, or fuzzy) for a
    post to qualify. Posts needing any fuzzy match rank behind posts
    matched entirely by exact/prefix. Ties break by date descending,
    dateless posts last.
    """
    if len(query.strip()) < MIN_QUERY_LENGTH:
        return []
    query_tokens = sorted(tokenize(query))
    if not query_tokens:
        return []

    scored: list[tuple[int, bool, IndexedPost]] = []
    for indexed in index:
        score, used_fuzzy = _score_post(query_tokens, indexed)
        if score > 0:
            scored.append((score, used_fuzzy, indexed))
    scored.sort(
        key=lambda item: (
            item[1],
            -item[0],
            item[2].result.date is None,
            -(item[2].result.date.toordinal() if item[2].result.date else 0),
        ),
    )
    return [indexed.result for _, _, indexed in scored[:limit]]


def search_posts(query: str, posts: list[Post], limit: int = DEFAULT_LIMIT) -> list[SearchResult]:
    """Convenience: build an index and search it in one call."""
    return query_index(query, build_search_index(posts), limit)


async def get_search_index(services: Services, include_drafts: bool) -> list[IndexedPost]:
    """Return the cached index for the audience, building it on miss.

    Building is the expensive part (tokenizing every post body), so one miss
    indexes everything once with drafts included and caches both audience
    variants: the published index is just the drafts filtered out. Both inherit
    the cache's TTL and are invalidated by the webhook's cache.clear() like
    every other derived blob. The parsed posts come from the shared cached
    content layer (get_cached_posts), so they are parsed at most once per TTL.
    """
    cache = services.cache
    key = SEARCH_INDEX_ALL_KEY if include_drafts else SEARCH_INDEX_PUBLISHED_KEY
    cached = await cache.get(key)
    if cached is not None:
        return cached

    posts = await get_cached_posts(services, include_drafts=True)

    all_index = build_search_index(posts)
    published_index = [indexed for indexed in all_index if not indexed.result.draft]
    await cache.set(SEARCH_INDEX_ALL_KEY, all_index)
    await cache.set(SEARCH_INDEX_PUBLISHED_KEY, published_index)
    return all_index if include_drafts else published_index


async def warm_search_indexes(services: Services) -> None:
    """Pre-build both audience index variants (used by the webhook warm).

    One call suffices: an index miss builds and caches both variants.
    """
    await get_search_index(services, include_drafts=True)
