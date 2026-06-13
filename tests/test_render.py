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


def test_render_html_with_config_dict():
    """Accepts optional config dict with timezone for timestamp rendering."""
    stories = [
        {"headline": "Test Story", "source": "Src", "url": "#", "summary": "Sum"},
    ]
    config = {"timezone": "America/New_York"}
    html = render_html(stories, config)
    assert "AI Briefing" in html
    assert "color-primary-if-not-visited" in html
    assert "Test Story" in html


def test_render_html_without_config_backward_compat():
    """Calling render_html without config still works (backward compat)."""
    stories = [
        {"headline": "Backward", "source": "Compat", "url": "#", "summary": "Works"},
    ]
    html = render_html(stories)
    assert "AI Briefing" in html
    assert "color-primary-if-not-visited" in html
    assert "Backward" in html


def test_render_html_timezone_shifts_hour():
    """Timezone config shifts the displayed hour correctly."""
    from datetime import datetime, timezone
    import briefing.render

    fixed = datetime(2026, 6, 13, 8, 0, 0, tzinfo=timezone.utc)

    class _FakeDatetime:
        """Replaces briefing.render.datetime so .now() returns a fixed time."""
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz) if tz else fixed

    original = briefing.render.datetime
    briefing.render.datetime = _FakeDatetime
    try:
        stories = [{"headline": "H", "source": "S", "url": "#", "summary": "S"}]

        html_utc = render_html(stories)
        assert "08:00 UTC" in html_utc

        html_athens = render_html(stories, {"timezone": "Europe/Athens"})
        assert "11:00 EEST" in html_athens

        html_ny = render_html(stories, {"timezone": "America/New_York"})
        assert "04:00" in html_ny
        assert "EDT" in html_ny or "EST" in html_ny
    finally:
        briefing.render.datetime = original
