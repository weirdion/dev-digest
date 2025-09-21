import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from dev_digest.utility.constants import KEYWORDS_TO_IGNORE

def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def within_window(published_dt, upper_bound, lower_bound) -> bool:
    if not published_dt:
        return False
    return (upper_bound - published_dt) <= timedelta(days=lower_bound)


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

def filter_ignored_keywords(items):
    """
    Filters items by using KEYWORDS_IGNORE list.
    Each item is a dict with keys: title, link, published (datetime|None), source.
    """
    ignore_lc = [k.lower() for k in KEYWORDS_TO_IGNORE]
    results = []
    filtered = []
    for item in items:
        title = item.get("title", "")
        if not title:
            filtered.append(item)
            continue

        # Filter by keywords to ignore
        tl = title.lower()
        if any(k in tl for k in ignore_lc):
            filtered.append(item)
            continue

        results.append(item)
    return results, filtered

def write_to_file(base_dir: Path, file_name: str, items: list):
    """
    Writes items to a file in JSON format.
    Each item is a dict with keys: title, link, published (datetime|None), source.
    """
    tmp_file = base_dir.joinpath(file_name)
    tmp_file.write_text(
        json.dumps(items, default=_json_default, indent=2),
        encoding="utf-8"
    )