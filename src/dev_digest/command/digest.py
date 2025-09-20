import json
import logging
from datetime import datetime, timezone
import shutil
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from dev_digest.handler.FeedHandler import FeedHandler
from dev_digest.handler.StrandsAgent import StrandsAgent
from dev_digest.handler.DeterministicDigest import DeterministicDigest
from dev_digest.utility.constants import MARDOWN_FOOTER, WINDOW_DAYS, OUT_DIR, DEFAULT_MODEL_KEY
from dev_digest.utility.feeds import ALL_FEEDS
from dev_digest.utility.security import validate_feed_urls
from dev_digest.utility.tools import dedupe_items

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dev-digest")


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


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
    # Optionally clear today's folder before regenerating
    if overwrite and output_dir.exists():
        # Only remove directories inside OUT_DIR to be safe
        out_root = Path(OUT_DIR).resolve()
        try:
            resolved = output_dir.resolve()
            if str(resolved).startswith(str(out_root)):
                shutil.rmtree(resolved)
        except FileNotFoundError:
            pass
    output_dir.mkdir(parents=True, exist_ok=True)
    outfile = output_dir.joinpath(f"dev-digest-{date_str}.md")
    if is_debug:
        tmp_dir = output_dir.joinpath("tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)

    feed_handler = FeedHandler()
    ai_handler = StrandsAgent(model_key=model_key) if ai_generated else None

    # 1) Fetch feeds (with security validation)
    validated_feeds = validate_feed_urls(ALL_FEEDS)
    feed_items: List[Dict[str, Any]] = feed_handler.fetch_recent(validated_feeds, now, days)
    log.info(f"Found {len(feed_items)} recent items")
    if is_debug:
        tmp_file = tmp_dir.joinpath("feed.json")
        tmp_file.write_text(json.dumps(feed_items, default=_json_default, indent=2), encoding="utf-8")

    # 2) De-duplicate
    combined = dedupe_items(feed_items)
    log.info(f"Combined {len(combined)} items")
    if is_debug:
        tmp_file = tmp_dir.joinpath("combined.json")
        tmp_file.write_text(json.dumps(combined, default=_json_default, indent=2), encoding="utf-8")

    # 4) Generate newsletter
    if not ai_generated:
        det = DeterministicDigest()
        markdown, diagnostics = det.generate(combined, output_dir)
        if include_footer:
            markdown = markdown.rstrip() + MARDOWN_FOOTER
        out_path = det.write_outputs(output_dir, markdown, diagnostics, debug=is_debug)
        print(f"Newsletter generated (deterministic): {out_path}")
    else:
        newsletter_content = ai_handler.summarize_markdown(combined)  # type: ignore[union-attr]
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

        print(f"Newsletter generated: {outfile}")
    return 0
