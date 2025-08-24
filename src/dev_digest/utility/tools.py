import re
from datetime import timedelta
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from dev_digest.utility.constants import WINDOW_DAYS


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def within_window(published_dt, now_utc) -> bool:
    if not published_dt:
        return False
    return (now_utc - published_dt) <= timedelta(days=WINDOW_DAYS)


def canonicalize_url(url: str) -> str:
    """Normalize a URL for de-duplication: strip tracking params and fragments, normalize host."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Drop fragment, normalize scheme/host, strip tracking query params
    query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                   if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    new_query = urlencode(query_pairs)
    netloc = parsed.netloc.lower()
    scheme = parsed.scheme.lower() or "https"
    # Remove trailing slash normalization handled by path
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunparse((scheme, netloc, path.rstrip("/") or "/", parsed.params, new_query, ""))


def dedupe_items(items):
    """
    De-duplicate items by canonical URL and by normalized title.
    Each item is a dict with keys: title, link, published (datetime|None), source.
    """
    seen_urls = set()
    seen_titles = set()
    unique = []
    for it in items:
        title_norm = normalize_text((it.get("title") or "").casefold())
        url_key = canonicalize_url(it.get("link") or "")
        key = (url_key, title_norm)
        if not url_key and not title_norm:
            continue
        if url_key in seen_urls or title_norm in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_norm)
        unique.append(it)
    return unique
