from __future__ import annotations

from urllib.parse import urlparse


REALPYTHON_SKIP_PREFIXES = ("/quizzes/", "/courses/")


def should_exclude_link(link: str) -> bool:
    if not link:
        return False
    parsed = urlparse(link)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if host.endswith("realpython.com") and any(path.startswith(prefix) for prefix in REALPYTHON_SKIP_PREFIXES):
        return True
    return False


__all__ = ["should_exclude_link"]
