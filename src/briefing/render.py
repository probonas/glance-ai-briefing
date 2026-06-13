"""HTML rendering using Glance's native CSS utility classes.

Uses only classes documented at:
https://github.com/glanceapp/glance/blob/main/docs/extensions.md
"""

from datetime import datetime


def render_html(stories: list[dict]) -> str:
    """Render curated stories as an HTML fragment using Glance native classes.

    Returns a <ul> with <li> per story matching Glance's existing
    RSS/feed widget structure. No <style> blocks — styling comes from
    Glance's built-in theme.
    """
    now = datetime.now().strftime("%a %d %b, %H:%M")
    items = ""
    for story in stories:
        headline = story.get("headline", "")
        source = story.get("source", "")
        url = story.get("url", "#")
        summary = story.get("summary", "")
        items += f"""
        <li>
            <a class="size-h3 color-primary-if-not-visited visited-indicator"
               href="{url}">{headline}</a>
            <ul class="list-horizontal-text">
                <li>{source}</li>
                <li>{summary}</li>
            </ul>
        </li>"""

    return f"""<div class="margin-bottom-10">
    <p class="size-h5 color-primary margin-bottom-10">&#10022; AI Briefing &mdash; {now}</p>
    <ul class="list list-gap-10 list-with-separator">{items}
    </ul>
</div>"""


def render_empty_state() -> str:
    """Return a subdued empty-state message when no stories are available."""
    return '<p class="color-subdue">No briefing available</p>'
