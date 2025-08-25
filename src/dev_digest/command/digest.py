import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from dev_digest.handler.FeedHandler import FeedHandler
from dev_digest.handler.StrandsAgent import StrandsAgent
from dev_digest.utility.constants import WINDOW_DAYS, OUT_DIR
from dev_digest.utility.feeds import ALL_FEEDS
from dev_digest.utility.security import validate_feed_urls
from dev_digest.utility.tools import dedupe_items

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dev-digest")


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def run(is_debug: bool = False, days: int = WINDOW_DAYS) -> int:
    """
    Build the weekly digest:
    @:param days: number of days to look back for recent items
    """
    load_dotenv()
    now = datetime.now(timezone.utc)
    run_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path(OUT_DIR).joinpath(run_time)
    output_dir.mkdir(parents=True, exist_ok=True)
    outfile = output_dir.joinpath(f"dev-digest-{now.strftime('%Y-%m-%d')}.md")
    if is_debug:
        tmp_dir = output_dir.joinpath("tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)

    feed_handler = FeedHandler()
    ai_handler = StrandsAgent()

    # 1) Fetch feeds (with security validation)
    validated_feeds = validate_feed_urls(ALL_FEEDS)
    feed_items: List[Dict[str, Any]] = feed_handler.fetch_recent(validated_feeds, now, days)
    log.info(f"Found {len(feed_items)} recent items")
    if is_debug:
        tmp_file = tmp_dir.joinpath("feed.json")
        tmp_file.write_text(json.dumps(feed_items, default=_json_default, indent=2), encoding="utf-8")

    # 2) AI search
    # ai_query = (
    #     "Senior Cloud Engineer topics: AWS, backend, DevOps, networking, security, "
    #     "developer tooling, Python, Git workflow, Kubernetes/containers, security alerts, edge/infra."
    # )
    # ai_items: List[Dict[str, Any]] = ai_handler.search_recent(ai_query, window_days=days)
    # log.info(f"Found {len(ai_items)} AI items")
    # if is_debug:
    #     tmp_file = tmp_dir.joinpath("ai.json")
    #     tmp_file.write_text(json.dumps(ai_items, default=_json_default, indent=2), encoding="utf-8")

    # 3) De-duplicate
    combined = dedupe_items(feed_items)
    log.info(f"Combined {len(combined)} items")
    if is_debug:
        tmp_file = tmp_dir.joinpath("combined.json")
        tmp_file.write_text(json.dumps(combined, default=_json_default, indent=2), encoding="utf-8")

    # 4) Generate newsletter
    newsletter_content = ai_handler.summarize_markdown(combined)
    outfile.write_text(newsletter_content, encoding="utf-8")

    print(f"Newsletter generated: {outfile}")
    return 0

if __name__ == "__main__":
    run()