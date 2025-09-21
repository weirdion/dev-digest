import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from dev_digest.handler.FeedHandler import FeedHandler
from dev_digest.handler.StrandsAgent import StrandsAgent
from dev_digest.handler.DeterministicDigest import DeterministicDigest
from dev_digest.model import FeedEntry
from dev_digest.utility.constants import MARDOWN_FOOTER, WINDOW_DAYS, OUT_DIR, DEFAULT_MODEL_KEY
from dev_digest.utility.feeds import ALL_FEEDS
from dev_digest.utility.security import validate_feed_urls
from dev_digest.utility.tools import dedupe_items, filter_ignored_keywords, write_to_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dev-digest")


def run(
    is_debug: bool = False,
    days: int = WINDOW_DAYS,
    model_key: str = DEFAULT_MODEL_KEY,
    ai_generated: bool = False,
    include_footer: bool = False,
    overwrite: bool = False,
) -> int:
    """
    Build the weekly digest:
    @:param days: number of days to look back for recent items
    """
    load_dotenv()
    now = datetime.now(timezone.utc)
    date_str = now.date().isoformat()

    output_dir = Path(OUT_DIR) / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    outfile = output_dir.joinpath(f"dev-digest-{date_str}.md")

    if is_debug:
        tmp_dir = output_dir.joinpath("tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)

    feed_handler = FeedHandler()
    ai_handler = StrandsAgent(model_key=model_key) if ai_generated else None

    # 1) Fetch feeds (with security validation)
    validated_feeds = validate_feed_urls(ALL_FEEDS)
    feed_items: List[FeedEntry] = feed_handler.fetch_recent(validated_feeds, now, days, overwrite)
    log.info(f"Found {len(feed_items)} recent items")
    if is_debug:
        write_to_file(tmp_dir, "feed.json", feed_items)

    # 2) De-duplicate
    combined = dedupe_items(feed_items)
    combined_cleaned, filtered = filter_ignored_keywords(combined)
    log.info(f"Combined and filtered {len(combined_cleaned)} items")
    if is_debug:
        write_to_file(tmp_dir, "combined.json", combined_cleaned)
        write_to_file(tmp_dir, "combined-filtered.json", filtered)

    # 4) Generate newsletter
    if not ai_generated:
        det = DeterministicDigest()
        markdown, diagnostics = det.generate(combined_cleaned, output_dir)
        if include_footer:
            markdown = markdown.rstrip() + MARDOWN_FOOTER
        out_path = det.write_outputs(output_dir, markdown, diagnostics, debug=is_debug)
        print(f"Newsletter generated (deterministic): {out_path}")
    else:
        newsletter_content = ai_handler.summarize_markdown(combined_cleaned)  # type: ignore[union-attr]
        if include_footer:
            newsletter_content = newsletter_content.rstrip() + MARDOWN_FOOTER
        outfile.write_text(newsletter_content, encoding="utf-8")

        # Log and persist token/cost metrics if available
        usage = getattr(ai_handler, "last_usage", None)  # type: ignore[union-attr]
        if usage:
            log.info(
                "LLM usage model=%s in=%s out=%s total=%s est_cost_usd=%.6f",
                usage.get("model", ""),
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("total_tokens", 0),
                usage.get("estimated_cost_usd", 0.0),
            )
            if is_debug:
                tmp_file = tmp_dir.joinpath("metrics.json")
                from dev_digest.utility.metrics import to_json
                tmp_file.write_text(to_json(usage), encoding="utf-8")
        # Persist a debug snapshot of the agent result if available
        if is_debug:
            snapshot = getattr(ai_handler, "last_debug_snapshot", None)  # type: ignore[union-attr]
            if snapshot:
                write_to_file(tmp_dir, "agent_result.json", snapshot)

        print(f"Newsletter generated: {outfile}")
    return 0
