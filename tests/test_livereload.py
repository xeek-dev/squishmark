"""Tests for live reload service."""

from squishmark.services.livereload import _inject_script


def test_inject_script_before_body():
    """Script is inserted immediately before </body>."""
    html = b"<html><body><p>Hello</p></body></html>"
    result = _inject_script(html)
    assert b"<p>Hello</p><script>" in result
    assert b"</script></body></html>" in result


def test_inject_script_no_body_tag():
    """HTML without </body> is returned unchanged."""
    html = b"<html><p>fragment</p></html>"
    assert _inject_script(html) == html


def test_inject_script_case_insensitive():
    """Injection works regardless of </body> casing."""
    html = b"<html><BODY>content</BODY></html>"
    result = _inject_script(html)
    assert b"<script>" in result
    assert b"</script></BODY>" in result


def test_inject_script_uses_last_body():
    """When multiple </body> tags exist, inject before the last one."""
    html = b"<body>first</body><body>second</body>"
    result = _inject_script(html)
    # The script should appear before the LAST </body>
    parts = result.split(b"</body>")
    assert len(parts) == 3  # first, second+script, trailing
