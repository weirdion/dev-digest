import re
from html.parser import HTMLParser
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


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def get_data(self) -> str:
        return "".join(self.parts)


def strip_html_to_text(html: str) -> str:
    """Remove HTML tags and return plain text."""
    if not html or not isinstance(html, str):
        return ""
    stripper = _HTMLStripper()
    try:
        stripper.feed(html)
        stripper.close()
        return re.sub(r"\s+", " ", stripper.get_data()).strip()
    except Exception:
        # Fallback: naive strip of tags
        return re.sub(r"<[^>]+>", " ", html)


def validate_feed_urls(urls: List[str]) -> List[str]:
    """Validate and filter a list of feed URLs."""
    return [url for url in urls if validate_feed_url(url)]
