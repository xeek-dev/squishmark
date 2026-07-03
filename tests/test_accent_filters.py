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
