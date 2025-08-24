import re
from urllib.parse import urlparse
from typing import List


def validate_feed_url(url: str) -> bool:
    """Validate that a URL is safe for feed parsing."""
    if not url or not isinstance(url, str):
        return False
        
    try:
        parsed = urlparse(url.strip())
        return (
            parsed.scheme in ('http', 'https') and
            parsed.netloc and
            not parsed.netloc.startswith('localhost') and
            not parsed.netloc.startswith('127.') and
            not parsed.netloc.startswith('10.') and
            not parsed.netloc.startswith('192.168.')
        )
    except Exception:
        return False


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Sanitize text input by removing potentially harmful content."""
    if not text or not isinstance(text, str):
        return ""
        
    # Remove control characters and limit length
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return sanitized[:max_length].strip()


def validate_feed_urls(urls: List[str]) -> List[str]:
    """Validate and filter a list of feed URLs."""
    return [url for url in urls if validate_feed_url(url)]