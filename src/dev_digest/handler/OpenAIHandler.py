from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from openai import OpenAI

from dev_digest.utility.constants import OPEN_AI_MODEL, SYSTEM_PROMPT, KEYWORDS_TO_IGNORE


class OpenAIHandler:
    def __init__(self) -> None:
        self.client = OpenAI()

    def search_recent(self, query: str, window_days: int) -> List[Dict[str, Any]]:
        """
        Ask the model to propose noteworthy items with links from the last N days.
        Returns a list of dicts: {title, link, published=None, source="openai-search"}.
        """
        user = (
            f"Find noteworthy items from the last {window_days} days for this audience:\n"
            f"{query}\n"
            "Exclude AWS regional launches, partner network announcements, GovCloud items, "
            "and training and certification content.\n\n"
            "Return a compact list of 5-10 distinct items as JSON array with objects like:\n"
            '{"title": "...", "url": "..."}\n'
            "Only include items with direct, canonical URLs. No duplicates."
        )
        try:
            resp = self.client.chat.completions.create(
                model=OPEN_AI_MODEL,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You generate strictly formatted JSON as requested."},
                    {"role": "user", "content": user},
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
        except Exception:
            text = ""

        items: List[Dict[str, Any]] = []
        # Try JSON parse
        if text:
            # Extract JSON array if wrapped in markdown fences
            m = re.search(r"(\[\s*\{.*\}\s*\])", text, re.DOTALL)
            blob = m.group(1) if m else text
            try:
                data = json.loads(blob)
                for o in data if isinstance(data, list) else []:
                    title = (o.get("title") or "").strip()
                    url = (o.get("url") or o.get("link") or "").strip()
                    if title and url:
                        items.append({"title": title, "link": url, "published": None, "source": "openai-search"})
            except Exception:
                # Fallback: scan for markdown links [title](url)
                for mt in re.finditer(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", text):
                    title, url = mt.group(1).strip(), mt.group(2).strip()
                    items.append({"title": title, "link": url, "published": None, "source": "openai-search"})

        # Enforce filtering of unwanted categories in AI-suggested items
        if items:
            ignore_terms = {s for kw in KEYWORDS_TO_IGNORE for s in (kw.lower(), kw.replace("-", " ").lower())}

            def blocked(s: str) -> bool:
                s = (s or "").lower()
                return any(term in s for term in ignore_terms)

            items = [it for it in items if not (blocked(it.get("title", "")) or blocked(it.get("link", "")))]

        return items

    def summarize_markdown(self, items: List[Dict[str, Any]]) -> str:
        """
        Ask the model to synthesize a weekly digest in Markdown given items.
        Each item includes title and link, optionally published.
        """
        if not items:
            return "# Weekly Developer Digest\n\n_No items found._\n"

        # Compose a compact items list for the model
        bullet_lines = []
        for it in items:
            t = it.get("title") or ""
            l = it.get("link") or ""
            bullet_lines.append(f"- {t} — {l}")
        items_block = "\n".join(bullet_lines)

        user_prompt = (
            "Summarize the following items into a concise weekly newsletter in Markdown. "
            "Use sections suited for AWS & Cloud; CLI & Dev Tools; Python; Git & Workflow; "
            "Kubernetes / Containers; Security Alerts; Edge / Infra. "
            "For each bullet: state what's new, why it matters, and include a clean link. "
            "Only output Markdown, no preface or commentary.\n\n"
            "Items:\n"
            f"{items_block}\n"
        )

        try:
            resp = self.client.chat.completions.create(
                model=OPEN_AI_MODEL,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            content = ""

        if not content:
            # Basic fallback
            return "# Weekly Developer Digest\n\n" + "\n".join(f"- {line}" for line in bullet_lines) + "\n"

        return content
