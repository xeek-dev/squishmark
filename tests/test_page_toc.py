"""Pages opt IN to the table of contents (issue #147).

Posts default to showing a TOC (opt-out); pages default to none and enable
it only with an explicit ``toc: true`` in frontmatter.
"""

import pytest

from squishmark.services.markdown import MarkdownService

BODY = "\n\n## First section\n\nText.\n\n## Second section\n\nMore text.\n"


@pytest.fixture
def markdown_service():
    return MarkdownService()


def test_page_toc_defaults_off(markdown_service):
    page = markdown_service.parse_page("pages/guide.md", "---\ntitle: Guide\n---" + BODY)
    assert page.toc == ""


def test_page_toc_opt_in(markdown_service):
    page = markdown_service.parse_page("pages/guide.md", "---\ntitle: Guide\ntoc: true\n---" + BODY)
    assert page.toc
    assert "first-section" in page.toc


def test_page_toc_explicit_false(markdown_service):
    page = markdown_service.parse_page("pages/guide.md", "---\ntitle: Guide\ntoc: false\n---" + BODY)
    assert page.toc == ""


def test_page_toc_opt_in_headingless_is_empty(markdown_service):
    page = markdown_service.parse_page("pages/guide.md", "---\ntitle: Guide\ntoc: true\n---\n\nJust a paragraph.\n")
    assert page.toc == ""
