from dev_digest.model import FeedEntry
from dev_digest.utility.tools import canonicalize_url, dedupe_items, normalize_text


def test_canonicalize_url_strips_tracking_and_fragment():
    url = "HTTPS://Example.com/Path///to/page/?utm_source=foo&fbclid=bar&a=1#section"
    canon = canonicalize_url(url)
    assert canon == "https://example.com/Path/to/page?a=1"


def test_dedupe_items_by_url_and_title():
    items = [
        FeedEntry(title="Hello World", link="https://x.com/a?utm_source=1", published=None, source="x", summary=""),
        FeedEntry(title="hello  world ", link="https://x.com/a", published=None, source="x", summary=""),
        FeedEntry(title="Different", link="https://x.com/b#frag", published=None, source="x", summary=""),
        FeedEntry(title="Different", link="https://x.com/b", published=None, source="x", summary=""),
    ]
    unique = dedupe_items(items)
    # Expect one for the first two, and one for the b-link duplicates => total 2 unique
    assert len(unique) == 2


def test_normalize_text_collapses_whitespace():
    assert normalize_text("  a\n b\t c  ") == "a b c"
