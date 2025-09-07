from datetime import datetime, timezone
from pathlib import Path

import json
import re

from dev_digest.handler.DeterministicDigest import DeterministicDigest


def _mk_run_dir(tmp_path: Path, stamp: str = "2025-01-01_00-00-00") -> Path:
    p = tmp_path / stamp
    p.mkdir(parents=True, exist_ok=True)
    return p


def test_heuristic_score_signals():
    det = DeterministicDigest()
    pos = det._heuristic_score(
        title="Generally available: performance improvements in Rust allocator",
        summary="allocator performance", source="Cloudflare"
    )
    neg = det._heuristic_score(
        title="Webinar: unlocking next-generation cloud", summary="",
        source="Some Blog"
    )
    assert pos > neg
    assert pos > 20


def test_infer_category_mapping():
    det = DeterministicDigest()
    assert det._infer_category("CVE-2024-1234 discovered", "") == "Security & Alerts"
    assert det._infer_category("Terraform v1.9 released", "") == "Infrastructure as Code"
    assert det._infer_category("Kubernetes tips", "") == "Kubernetes/Containers"
    assert det._infer_category("Python typing improvements", "") == "Python"
    assert det._infer_category("New CLI tool", "") == "CLI & Dev Tools"
    assert det._infer_category("ML perf", "") == "ML & AI"
    assert det._infer_category("AWS feature", "") == "AWS & Cloud"


def test_short_summary_truncates():
    det = DeterministicDigest()
    long = " ".join(["w"] * 60)
    ss = det._short_summary(long, 30)
    assert len(ss.split()) == 30


def test_low_signal_recent_announcements_filtered(tmp_path):
    det = DeterministicDigest()
    run_dir = _mk_run_dir(tmp_path)
    items = [
        {
            "title": "Now available in us-east-1: service quotas update",
            "link": "https://aws.amazon.com/about-aws/whats-new/2025/xx",
            "published": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "source": "Recent Announcements",
            "summary": "",
        },
        {
            "title": "Cloudflare postmortem of incident",
            "link": "https://blog.cloudflare.com/postmortem-xyz",
            "published": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "source": "Cloudflare Blog",
            "summary": "Postmortem details",
        },
    ]
    md, diag = det.generate(items, run_dir)
    # Ensure Recent Announcements item excluded with low_signal reason
    reasons = [d.get("reason") for d in diag if not d.get("included")]
    assert "low_signal" in reasons
    # Only non-RA item should appear
    assert "Cloudflare" in md
    assert "Recent Announcements" not in md


def test_per_section_cap_and_diagnostics(tmp_path):
    # Disable top picks to test only per-section capping behavior
    det = DeterministicDigest(per_section_cap=3, top_picks=0)
    run_dir = _mk_run_dir(tmp_path)
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    # Use distinct tokens to avoid near-duplicate merging; ensures per-section cap applies
    tokens = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"]
    items = [
        {
            "title": f"Security bulletin {tok}",
            "link": f"https://example.com/sec/{i}",
            "published": base_time,
            "source": "Security Blog",
            "summary": "CVE-2025-0000",
        }
        for i, tok in enumerate(tokens)
    ]
    md, diag = det.generate(items, run_dir)
    # One item is featured as a top pick (even when top_picks=0),
    # so the section retains cap-1 included items.
    included_titles = [d["title"] for d in diag if d.get("included") and d.get("section") == "Security & Alerts"]
    assert len(included_titles) == 2
    # The rest should have per_section_cap reason
    reasons = [d.get("reason") for d in diag if not d.get("included")]
    assert "per_section_cap" in reasons


def test_ra_microcap_within_aws(tmp_path):
    det = DeterministicDigest(per_section_cap=10)
    run_dir = _mk_run_dir(tmp_path)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    # Mix of AWS RA and non-RA
    items = [
        {"title": "Big AWS blog post", "link": "https://aws.amazon.com/blogs/architecture/abc", "published": now, "source": "AWS Architecture Blog", "summary": "deep"},
    ]
    # 5 RA items
    for i in range(5):
        items.append({
            "title": f"Now available in eu-west-1 {i}",
            "link": f"https://aws.amazon.com/about-aws/whats-new/{i}",
            "published": now,
            "source": "Recent Announcements",
            "summary": "",
        })
    md, diag = det.generate(items, run_dir)
    # In AWS & Cloud, at most 2 RA items remain due to micro-cap
    aws_included = [d for d in diag if d.get("included") and d.get("section") == "AWS & Cloud"]
    ra_included = [d for d in aws_included if (d.get("source") or "").strip().lower() == "recent announcements"]
    assert len(ra_included) <= 2


def test_top_picks_selection_and_removal_from_sections(tmp_path):
    det = DeterministicDigest(top_picks=2)
    run_dir = _mk_run_dir(tmp_path)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    items = [
        {"title": "Cloudflare: deep postmortem", "link": "https://blog.cloudflare.com/postmortem-xyz", "published": now, "source": "Cloudflare Blog", "summary": "postmortem"},
        {"title": "Kubernetes v1.34 released", "link": "https://kubernetes.io/blog/1-34", "published": now, "source": "Kubernetes Blog", "summary": "release notes"},
        {"title": "Terraform v1.9 released", "link": "https://www.hashicorp.com/blog/terraform-v1-9", "published": now, "source": "HashiCorp Blog", "summary": "release notes"},
    ]
    md, diag = det.generate(items, run_dir)
    # Top picks section should exist
    assert "## Interesting Reads" in md
    # Kubernetes release should be excluded from top picks (release-like)
    assert not any(d.get("featured_top_pick") and "Kubernetes" in d.get("title", "") for d in diag)
    # Terraform release is IaC and allowed as a top pick
    assert any(d.get("featured_top_pick") and "Terraform" in d.get("title", "") for d in diag)
    # Featured items should not appear again in their sections
    feat_titles = {d.get("title") for d in diag if d.get("featured_top_pick")}
    repeated = [d for d in diag if d.get("included") and not d.get("featured_top_pick") and d.get("title") in feat_titles]
    assert not repeated


def test_markdown_item_format(tmp_path):
    det = DeterministicDigest()
    run_dir = _mk_run_dir(tmp_path)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    items = [
        {"title": "GitHub CLI improvements", "link": "https://github.blog/cli-improvements", "published": now, "source": "GitHub Engineering", "summary": "CLI"}
    ]
    md, _ = det.generate(items, run_dir)
    # Expect bold title and Read: URL pattern on a line
    line = next((l for l in md.splitlines() if l.startswith("- ")), "")
    assert "**GitHub CLI improvements" in line
    assert re.search(r"Read: https://", line)
