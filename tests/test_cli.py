from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import types

from click.testing import CliRunner
import pytest

# Provide a lightweight stub for feedparser to avoid requiring the package in tests
if "feedparser" not in sys.modules:
    sys.modules["feedparser"] = types.SimpleNamespace(parse=lambda url: types.SimpleNamespace(entries=[], feed={"title": url}))

from dev_digest import __version__
from dev_digest.cli import app


runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout.strip()


def test_run_deterministic_smoke(monkeypatch, tmp_path):
    """Run the deterministic pipeline via CLI and verify outputs are created.

    Network calls are avoided by monkeypatching FeedHandler.fetch_recent to return fixed items.
    Output directory is redirected to a temp folder.
    """
    # Redirect OUT_DIR used by command
    import dev_digest.command.digest as digest_mod
    monkeypatch.setattr(digest_mod, "OUT_DIR", str(tmp_path / "out"), raising=True)

    # Provide fixed recent items
    now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    items = [
        {
            "title": "AWS Compute Blog: Lambda now supports Rust runtime GA",
            "link": "https://aws.amazon.com/blogs/compute/lambda-rust-ga/",
            "published": now,
            "source": "AWS Compute Blog",
            "summary": "AWS Lambda adds GA support for Rust runtime with improved performance.",
        },
        {
            "title": "Cloudflare: Improving allocator performance at scale",
            "link": "https://blog.cloudflare.com/improving-allocator-performance/",
            "published": now,
            "source": "Cloudflare Blog",
            "summary": "Deep dive into allocator optimizations improving latency and throughput.",
        },
        {
            "title": "Kubernetes v1.34 released",
            "link": "https://kubernetes.io/blog/announce-1-34/",
            "published": now,
            "source": "Kubernetes Blog",
            "summary": "Release notes for Kubernetes 1.34 with feature updates.",
        },
    ]

    def fake_fetch_recent(self, feed_urls, now_utc, window_days):
        return items

    import dev_digest.handler.FeedHandler as FH_mod
    monkeypatch.setattr(FH_mod.FeedHandler, "fetch_recent", fake_fetch_recent, raising=True)

    # Run CLI in debug mode (writes diagnostics)
    result = runner.invoke(app, ["run", "--no-ai", "-d", "--days", "7"])
    assert result.exit_code == 0, result.output

    # Find created run directory and outputs
    out_root = Path(digest_mod.OUT_DIR)
    runs = sorted([p for p in out_root.iterdir() if p.is_dir()])
    assert runs, "No run directory created under OUT_DIR"
    latest = runs[-1]

    # Markdown digest file named with underscores per date
    run_date = latest.name.split("_", 1)[0]
    digest_path = latest / f"dev_digest_newsletter_{run_date.replace('-', '_')}.md"
    assert digest_path.exists(), f"Missing digest file: {digest_path}"

    content = digest_path.read_text(encoding="utf-8")
    assert content.startswith(f"# Dev Digest — Week of {run_date}")
    # Check that at least one line uses the required item format with Read: URL
    assert "Read: https://" in content

    # Debug diagnostics should exist in debug mode
    debug_json = latest / "debug_ranking.json"
    debug_csv = latest / "debug_ranking.csv"
    debug_md = latest / "debug_ranking.md"
    assert debug_json.exists() and debug_csv.exists() and debug_md.exists()

    # Ensure debug JSON can be parsed
    diag = json.loads(debug_json.read_text(encoding="utf-8"))
    assert isinstance(diag, list)


def test_deterministic_merge_near_duplicates(tmp_path):
    """Ensure near-duplicate stories from the same host are merged with diagnostics."""
    from dev_digest.handler.DeterministicDigest import DeterministicDigest

    run_dir = tmp_path / "2025-01-01_12-00-00"
    run_dir.mkdir(parents=True, exist_ok=True)

    items = [
        {
            "title": "AWS Lambda performance improvements",
            "link": "https://aws.amazon.com/blogs/compute/lambda-performance-optimizations/",
            "published": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "source": "AWS Compute Blog",
            "summary": "We improved performance of AWS Lambda cold starts.",
        },
        {
            "title": "Performance improvements for AWS Lambda",
            "link": "https://aws.amazon.com/blogs/compute/lambda-performance-optimizations-detail/",
            "published": datetime(2025, 1, 2, tzinfo=timezone.utc),
            "source": "AWS Compute Blog",
            "summary": "Deeper dive into Lambda performance improvements.",
        },
    ]

    det = DeterministicDigest()
    markdown, diagnostics = det.generate(items, run_dir)

    assert markdown.startswith("# Dev Digest — Week of 2025-01-01")
    # Expect one merged_duplicate diagnostic entry
    reasons = [d.get("reason") for d in diagnostics if not d.get("included")]
    assert "merged_duplicate" in reasons
