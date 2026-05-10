from pathlib import Path

from dev_digest.utility.substack_html import parse


def run(md_file: Path) -> int:
    if not md_file.exists():
        print(f"Error: {md_file} does not exist")
        return 1

    title, subtitle, body_html = parse(md_file)

    html_path = md_file.with_suffix(".html")
    html_path.write_text(body_html, encoding="utf-8")

    print(f"Title:    {title}")
    print(f"Subtitle: {subtitle}")
    print(f"HTML:     {html_path}")
    return 0
