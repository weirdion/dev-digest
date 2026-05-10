import re
from pathlib import Path

# Matches: - **Title (Source)** — date: description. Read: https://url
_BOLD_ITEM = re.compile(
    r"^-\s+\*\*(.+?)\*\*\s+(.+)\s+Read:\s+(https?://\S+)\s*$"
)
# Matches: - 2026-05-08 — [Link text](https://url)
_RA_ITEM = re.compile(
    r"^-\s+(\d{4}-\d{2}-\d{2})\s+—\s+\[(.+?)\]\((https?://[^)]+)\)\s*$"
)
_H2 = re.compile(r"^##\s+(.+)$")
_H3 = re.compile(r"^###\s+(.+)$")
_INLINE_LINK = re.compile(r"\[(.+?)\]\((https?://[^)]+)\)")


def _inline_links(text: str) -> str:
    return _INLINE_LINK.sub(r'<a href="\2">\1</a>', text)


def parse(md_path: Path) -> tuple[str, str, str]:
    """Return (title, subtitle, body_html) parsed from a newsletter markdown file."""
    lines = md_path.read_text(encoding="utf-8").splitlines()

    title = subtitle = ""
    body_start = 0

    for i, line in enumerate(lines):
        s = line.strip()
        if not title and s.startswith("# "):
            title = s[2:].strip()
        elif title and not subtitle and s and not s.startswith("#"):
            subtitle = s
            body_start = i + 1
            break

    return title, subtitle, _to_html(lines[body_start:])


def _to_html(lines: list[str]) -> str:
    parts: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    def open_list() -> None:
        nonlocal in_list
        if not in_list:
            parts.append("<ul>")
            in_list = True

    for line in lines:
        s = line.strip()

        if not s:
            close_list()
            continue

        if m := _H2.match(s):
            close_list()
            parts.append(f"<h2>{m.group(1)}</h2>")
            continue

        if m := _H3.match(s):
            close_list()
            parts.append(f"<h3>{m.group(1)}</h3>")
            continue

        # Regular section item: **Title** — date: desc. Read: URL
        if m := _BOLD_ITEM.match(s):
            open_list()
            item_title = m.group(1)
            rest = re.sub(r"[.!?]\s*$", "", m.group(2).strip())
            url = m.group(3)
            # Preserve original terminal punctuation if present, else add period
            orig_end = m.group(2).strip()
            terminal = orig_end[-1] if orig_end and orig_end[-1] in ".!?" else "."
            parts.append(
                f'<li><a href="{url}"><strong>{item_title}</strong></a> {rest}{terminal}</li>'
            )
            continue

        # RA item: date — [Link text](URL)
        if m := _RA_ITEM.match(s):
            open_list()
            date, text, url = m.group(1), m.group(2), m.group(3)
            parts.append(f'<li>{date} — <a href="{url}">{text}</a></li>')
            continue

        # Plain paragraph (footer, unrecognised lines)
        close_list()
        parts.append(f"<p>{_inline_links(s)}</p>")

    close_list()
    return "\n".join(parts)
