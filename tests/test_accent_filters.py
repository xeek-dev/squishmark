"""Tests for the accent_first_word Jinja2 filter."""

from squishmark.services.theme.filters import accent_first_word


class TestAccentFirstWord:
    def test_single_word_camelcase_splits_on_last_interior_cap(self):
        # "SquishMark" -> accent "Squish" + plain "Mark" (two-tone like the navbar).
        assert str(accent_first_word("SquishMark")) == '<span class="accent">Squish</span>Mark'

    def test_single_word_lowercase_accents_whole_word(self):
        assert str(accent_first_word("squishmark")) == '<span class="accent">squishmark</span>'

    def test_multi_word_title_unchanged(self):
        assert str(accent_first_word("My Blog")) == '<span class="accent">My</span> Blog'

    def test_empty_string_returns_empty_markup(self):
        assert str(accent_first_word("")) == ""


def test_space_rule_wins_over_capitals():
    """A spaced title splits on the space only; CamelCase in the first word
    is left intact (the rules are mutually exclusive)."""
    assert str(accent_first_word("SquishMark Blog")) == '<span class="accent">SquishMark</span> Blog'


def test_html_in_title_is_escaped():
    """Markup bypasses autoescaping, so the filter must escape the parts."""
    result = str(accent_first_word("<script>x</script> Blog"))
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
