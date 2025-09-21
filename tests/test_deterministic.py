from datetime import datetime, timezone, timedelta
from pathlib import Path

import json
import re

from dev_digest.handler.DeterministicDigest import DeterministicDigest
from dev_digest.model import DigestCandidate, FeedEntry
from dev_digest.utility.scoring import (
    classify_recent_announcement,
    get_profile,
    infer_category,
    score_candidate,
)


def _mk_run_dir(tmp_path: Path, stamp: str = "2025-01-01_00-00-00") -> Path:
    p = tmp_path / stamp
    p.mkdir(parents=True, exist_ok=True)
    return p


def test_heuristic_score_signals():
    profile = get_profile("deterministic")
    pos_candidate = DigestCandidate(
        title="Generally available: performance improvements in Rust allocator",
        link="",
        canonical_url="",
        source="Cloudflare",
        summary="allocator performance",
        published=None,
    )
    neg_candidate = DigestCandidate(
        title="Webinar: unlocking next-generation cloud",
        link="",
        canonical_url="",
        source="Some Blog",
        summary="",
        published=None,
    )
    pos, _, _ = score_candidate(pos_candidate, profile)
    neg, _, _ = score_candidate(neg_candidate, profile)
    assert pos > neg
    assert pos > 20


def test_infer_category_mapping():
    assert infer_category("CVE-2024-1234 discovered", "") == "Security & Alerts"
    assert infer_category("Terraform v1.9 released", "") == "Infrastructure as Code"
    assert infer_category("Kubernetes tips", "") == "Kubernetes/Containers"
    assert infer_category("Python typing improvements", "") == "Python"
    assert infer_category("New CLI tool", "") == "CLI & Dev Tools"
    assert infer_category("ML perf", "") == "ML & AI"
    assert infer_category("AWS feature", "") == "AWS & Cloud"


def test_classify_recent_announcement():
    critical = DigestCandidate(
        title="Security update fixes CVE-2025-0001",
        link="",
        canonical_url="",
        source="Recent Announcements",
        summary="",
        published=None,
    )
    high = DigestCandidate(
        title="Now generally available: AWS Widget",
        link="",
        canonical_url="",
        source="Recent Announcements",
        summary="",
        published=None,
    )
    medium = DigestCandidate(
        title="AWS Widget preview adds integration",
        link="",
        canonical_url="",
        source="Recent Announcements",
        summary="",
        published=None,
    )
    low = DigestCandidate(
        title="AWS Widget now available in us-east-1",
        link="",
        canonical_url="",
        source="Recent Announcements",
        summary="",
        published=None,
    )
    assert classify_recent_announcement(critical) == "critical"
    assert classify_recent_announcement(high) == "high"
    assert classify_recent_announcement(medium) == "medium"
    assert classify_recent_announcement(low) == "low"


def test_short_summary_truncates():
    det = DeterministicDigest()
    long = " ".join(["w"] * 60)
    ss = det._short_summary(long, 30)
    assert len(ss.split()) == 30


def test_low_signal_recent_announcements_filtered(tmp_path):
    det = DeterministicDigest()
    run_dir = _mk_run_dir(tmp_path)
    items = [
        FeedEntry(
            title="Now available in us-east-1: service quotas update",
            link="https://aws.amazon.com/about-aws/whats-new/2025/xx",
            published=datetime(2025, 1, 1, tzinfo=timezone.utc),
            source="Recent Announcements",
            summary="",
        ),
        FeedEntry(
            title="Cloudflare postmortem of incident",
            link="https://blog.cloudflare.com/postmortem-xyz",
            published=datetime(2025, 1, 1, tzinfo=timezone.utc),
            source="Cloudflare Blog",
            summary="Postmortem details",
        ),
    ]
    md, diag = det.generate(items, run_dir)

    assert "## AWS Recent Announcements" in md
    assert "### Low" in md
    assert "service quotas update" in md

    aws_cloud_section = next((section for section in md.split("## ") if section.startswith("AWS & Cloud")), "")
    assert "service quotas update" not in aws_cloud_section

    ra_diags = [d for d in diag if d.title.startswith("Now available in us-east-1")]
    assert any(d.reason == "aws_ra_section" and d.aws_severity == "low" for d in ra_diags if not d.included)
    assert any(d.included and d.section == "AWS Recent Announcements" and d.aws_severity == "low" for d in ra_diags)


def test_per_section_cap_and_diagnostics(tmp_path):
    # Disable top picks to test only per-section capping behavior
    det = DeterministicDigest(per_section_cap=3, top_picks=0)
    run_dir = _mk_run_dir(tmp_path)
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    # Use distinct tokens to avoid near-duplicate merging; ensures per-section cap applies
    tokens = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"]
    items = [
        FeedEntry(
            title=f"Security bulletin {tok}",
            link=f"https://example.com/sec/{i}",
            published=base_time,
            source="Security Blog",
            summary="CVE-2025-0000",
        )
        for i, tok in enumerate(tokens)
    ]
    md, diag = det.generate(items, run_dir)
    # One item is featured as a top pick (even when top_picks=0),
    # so the section retains cap-1 included items.
    included_titles = [d.title for d in diag if d.included and d.section == "Security & Alerts"]
    assert len(included_titles) == 2
    # The rest should have per_section_cap reason
    reasons = [d.reason for d in diag if not d.included]
    assert "per_section_cap" in reasons


def test_ra_microcap_within_aws(tmp_path):
    det = DeterministicDigest(per_section_cap=10)
    run_dir = _mk_run_dir(tmp_path)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    # Mix of AWS RA and non-RA
    items = [
        FeedEntry(
            title="Big AWS blog post",
            link="https://aws.amazon.com/blogs/architecture/abc",
            published=now,
            source="AWS Architecture Blog",
            summary="deep",
        ),
    ]
    # 5 RA items
    for i in range(5):
        items.append(
            FeedEntry(
                title=f"Now available in eu-west-1 {i}",
                link=f"https://aws.amazon.com/about-aws/whats-new/{i}",
                published=now,
                source="Recent Announcements",
                summary="",
            )
        )
    md, diag = det.generate(items, run_dir)
    # In AWS & Cloud, at most 2 RA items remain due to micro-cap
    aws_included = [d for d in diag if d.included and d.section == "AWS & Cloud"]
    ra_included = [d for d in aws_included if (d.source or "").strip().lower() == "recent announcements"]
    assert len(ra_included) <= 2


def test_top_picks_selection_and_removal_from_sections(tmp_path):
    det = DeterministicDigest(top_picks=2)
    run_dir = _mk_run_dir(tmp_path)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    items = [
        FeedEntry(
            title="Cloudflare: deep postmortem",
            link="https://blog.cloudflare.com/postmortem-xyz",
            published=now,
            source="Cloudflare Blog",
            summary="postmortem",
        ),
        FeedEntry(
            title="Kubernetes v1.34 released",
            link="https://kubernetes.io/blog/1-34",
            published=now,
            source="Kubernetes Blog",
            summary="release notes",
        ),
        FeedEntry(
            title="Terraform v1.9 released",
            link="https://www.hashicorp.com/blog/terraform-v1-9",
            published=now,
            source="HashiCorp Blog",
            summary="release notes",
        ),
    ]
    md, diag = det.generate(items, run_dir)
    # Top picks section should exist
    assert "## Interesting Reads" in md
    # Kubernetes release should be excluded from top picks (release-like)
    assert not any(d.featured_top_pick and "Kubernetes" in d.title for d in diag)
    # Terraform release is IaC and allowed as a top pick
    assert any(d.featured_top_pick and "Terraform" in d.title for d in diag)
    # Featured items should not appear again in their sections
    feat_titles = {d.title for d in diag if d.featured_top_pick}
    repeated = [d for d in diag if d.included and not d.featured_top_pick and d.title in feat_titles]
    assert not repeated


def test_markdown_item_format(tmp_path):
    det = DeterministicDigest()
    run_dir = _mk_run_dir(tmp_path)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    items = [
        FeedEntry(
            title="GitHub CLI improvements",
            link="https://github.blog/cli-improvements",
            published=now,
            source="GitHub Engineering",
            summary="CLI",
        )
    ]
    md, _ = det.generate(items, run_dir)
    # Expect bold title and Read: URL pattern on a line
    line = next((l for l in md.splitlines() if l.startswith("- ")), "")
    assert "**GitHub CLI improvements" in line
    assert re.search(r"Read: https://", line)


def test_aws_recent_announcements_section(tmp_path):
    det = DeterministicDigest()
    run_dir = _mk_run_dir(tmp_path)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    items = [
        FeedEntry(
            title="Core blog story",
            link="https://example.com/post",
            published=now,
            source="AWS Architecture Blog",
            summary="Deep dive",
        ),
        FeedEntry(
            title="Security patch resolves vulnerability",
            link="https://aws.amazon.com/about-aws/whats-new/security-patch",
            published=now,
            source="Recent Announcements",
            summary="Security update",
        ),
        FeedEntry(
            title="AWS Widget now available in us-east-1",
            link="https://aws.amazon.com/about-aws/whats-new/us-east-1-widget",
            published=now,
            source="Recent Announcements",
            summary="",
        ),
    ]

    md, diag = det.generate(items, run_dir)
    assert "## AWS Recent Announcements" in md
    assert "### Critical" in md
    assert "Security patch resolves vulnerability" in md
    assert "### Low" in md
    assert "AWS Widget now available in us-east-1" in md

    security_section = next((section for section in md.split("## ") if section.startswith("Security & Alerts")), "")
    assert "Security patch resolves vulnerability" in security_section
    aws_cloud_section = next((section for section in md.split("## ") if section.startswith("AWS & Cloud")), "")
    assert "AWS Widget now available in us-east-1" not in aws_cloud_section

    # Collect diagnostics for the low-severity announcement
    low_diag = [d for d in diag if d.title.startswith("AWS Widget")]
    assert any(d.reason == "aws_ra_section" and d.aws_severity == "low" for d in low_diag if not d.included)
    assert any(d.section == "AWS Recent Announcements" and d.included and d.aws_severity == "low" for d in low_diag)


def test_combined_score_prefers_recent_items(tmp_path):
    det = DeterministicDigest()
    run_dir = _mk_run_dir(tmp_path)
    run_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    items = [
        FeedEntry(
            title="GA release for Widget",
            link="https://example.com/widget",
            published=run_date,
            source="AWS Architecture Blog",
            summary="GA release",
        ),
        FeedEntry(
            title="GA release for Gizmo",
            link="https://example.com/gizmo-old",
            published=run_date - timedelta(days=7),
            source="AWS Architecture Blog",
            summary="GA release",
        ),
    ]
    _, diag = det.generate(items, run_dir)
    included = {d.title: d for d in diag if d.included}
    assert included["GA release for Widget"].combined_score > included["GA release for Gizmo"].combined_score
    assert included["GA release for Widget"].model_score >= included["GA release for Gizmo"].model_score
