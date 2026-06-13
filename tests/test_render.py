from briefing.render import render_html, render_empty_state


def test_render_html_uses_glance_native_classes():
    """Output uses Glance CSS utility classes, not custom <style> blocks."""
    stories = [
        {
            "headline": "Breaking News",
            "source": "BBC News",
            "url": "https://example.com/article",
            "summary": "Something important happened today",
        },
    ]
    html = render_html(stories)

    # Uses Glance's native CSS classes
    assert "color-primary-if-not-visited" in html
    assert "visited-indicator" in html
    assert "size-h3" in html
    assert "list-horizontal-text" in html
    assert "list-with-separator" in html

    # Does NOT include custom <style> blocks
    assert "<style>" not in html

    # Contains the story content
    assert "Breaking News" in html
    assert "BBC News" in html
    assert "https://example.com/article" in html
    assert "Something important happened today" in html


def test_render_html_multiple_stories():
    """Renders all stories in the list."""
    stories = [
        {"headline": "A", "source": "X", "url": "#", "summary": "One"},
        {"headline": "B", "source": "Y", "url": "#", "summary": "Two"},
        {"headline": "C", "source": "Z", "url": "#", "summary": "Three"},
    ]
    html = render_html(stories)

    assert html.count("color-primary-if-not-visited") == 3
    assert "A" in html
    assert "B" in html
    assert "C" in html


def test_render_empty_state():
    """Empty state returns HTML with a subdued message, no errors."""
    html = render_empty_state()
    assert "No briefing available" in html
    assert "color-subdue" in html


def test_render_html_handles_missing_summary():
    """Story without a summary field renders without crashing."""
    stories = [
        {"headline": "H", "source": "S", "url": "#", "summary": ""},
    ]
    html = render_html(stories)
    assert "H" in html


def test_render_html_escapes_no_style_block():
    """Confirm no <style> tag leaks through even with weird input."""
    stories = [
        {"headline": "<script>alert(1)</script>", "source": "X", "url": "#", "summary": "ok"},
    ]
    html = render_html(stories)
    assert "<style>" not in html
