from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urlparse

from dev_digest.model import DigestCandidate
from dev_digest.utility.sections import resolve_section
from dev_digest.utility.constants import (
    AWS_REGION_TERMS,
    AWS_WHATS_NEW_LOW_SIGNAL,
    CLICKBAIT_TERMS,
    IAC_HIGH_SIGNAL_TERMS,
    LANGUAGE_FEATURE_TERMS,
    PERFORMANCE_TERMS,
    PRACTICAL_TERMS,
    PERFORMANCE_WIN_PATTERNS,
    SECURITY_IMPACT_PATTERNS,
    PARTNER_PROGRAM_TERMS,
    AI_POLICY_TERMS,
    AI_POLICY_HOSTS,
    AI_FINANCE_TERMS,
)

GA_TERMS = ("generally available", "general availability", "ga ", "ga:", "stable release", "v1.0")
PREVIEW_TERMS = ("preview", "public preview", "beta")
POSTMORTEM_TERMS = ("postmortem", "incident", "outage", "root cause")
SECURITY_TERMS = ("0-day", "security")
DEPRECATION_TERMS = ("deprecate", "breaking change", "removed", "end of support")
OPEN_SOURCE_TERMS = ("open source", "oss", "released", "announce")
BRANCH_TERMS = ("branch", "branching")
SDK_TERMS = ("sdk", "cli")
PART_TWO_TERMS = ("part 2",)
GOVERNMENT_TERMS = ("government", "education", "schools", "policy", "partnership")
NEG_WEBINAR_TERMS = ("webinar", "podcast", "training", "certification", "partner", "regional")
NEG_TLS_TERMS = ("tls policy", "post-quantum")
RA_STRONG_TERMS = ("ga", "generally available", "security", "cve", "deprecat", "breaking")


@dataclass(frozen=True)
class HeuristicConfig:
    ga: float
    preview: float
    postmortem: float
    security: float
    deprecation: float
    performance: float
    brand_keywords: tuple[str, ...]
    brand_weight: float
    open_source: float
    language_feature: float
    branch: float
    sdk: float
    part_two: float
    government: float
    iac_release: float
    practical_example: float
    policy_penalty: float
    finance_penalty: float
    negative_webinar: float
    negative_clickbait: float
    ra_penalty: float
    ra_low_signal_penalty: float
    region_penalty: float
    tls_penalty: float


@dataclass(frozen=True)
class ScoreBlend:
    heuristic_weight: float
    model_weight: float
    fallback_to_heuristic: bool = False

    def effective_model_score(self, heuristic_score: float, model_score: float | None) -> float:
        if model_score is None:
            return heuristic_score if self.fallback_to_heuristic else 0.0
        return model_score

    def combine(self, heuristic_score: float, model_score: float | None) -> float:
        model = self.effective_model_score(heuristic_score, model_score)
        value = self.heuristic_weight * heuristic_score + self.model_weight * model
        return max(0.0, min(100.0, value))


@dataclass(frozen=True)
class ScoreProfile:
    name: str
    heuristic: HeuristicConfig
    blend: ScoreBlend


DETERMINISTIC_PROFILE = ScoreProfile(
    name="deterministic",
    heuristic=HeuristicConfig(
        ga=20,
        preview=16,
        postmortem=26,
        security=26,
        deprecation=24,
        performance=18,
        brand_keywords=("cloudflare", "github", "google", "microsoft"),
        brand_weight=6,
        open_source=10,
        language_feature=16,
        branch=8,
        sdk=6,
        part_two=6,
        government=8,
        iac_release=16,
        practical_example=8,
        policy_penalty=10,
        finance_penalty=8,
        negative_webinar=30,
        negative_clickbait=14,
        ra_penalty=0,
        ra_low_signal_penalty=0,
        region_penalty=0,
        tls_penalty=0,
    ),
    blend=ScoreBlend(heuristic_weight=0.7, model_weight=0.3, fallback_to_heuristic=False),
)

AI_PROFILE = ScoreProfile(
    name="ai",
    heuristic=HeuristicConfig(
        ga=8,
        preview=8,
        postmortem=12,
        security=10,
        deprecation=14,
        performance=12,
        brand_keywords=("aws", "cloudflare", "github", "google", "microsoft"),
        brand_weight=6,
        open_source=10,
        language_feature=16,
        branch=8,
        sdk=6,
        part_two=6,
        government=8,
        iac_release=8,
        practical_example=6,
        policy_penalty=8,
        finance_penalty=6,
        negative_webinar=30,
        negative_clickbait=14,
        ra_penalty=18,
        ra_low_signal_penalty=18,
        region_penalty=16,
        tls_penalty=10,
    ),
    blend=ScoreBlend(heuristic_weight=0.4, model_weight=0.6, fallback_to_heuristic=False),
)

SCORING_PROFILES: Dict[str, ScoreProfile] = {
    DETERMINISTIC_PROFILE.name: DETERMINISTIC_PROFILE,
    AI_PROFILE.name: AI_PROFILE,
}


def get_profile(name: str) -> ScoreProfile:
    if name not in SCORING_PROFILES:
        raise KeyError(f"Unknown scoring profile: {name}")
    return SCORING_PROFILES[name]


def infer_category(title: str, source: str, link: str = "", summary: str = "") -> str:
    return resolve_section(title, source, link, summary).title


def _iac_release_bonus(title_lower: str, weight: float) -> float:
    if weight == 0:
        return 0.0
    if not any(term in title_lower for term in IAC_HIGH_SIGNAL_TERMS):
        return 0.0
    if re.search(r"\bv\d+\.\d+\b", title_lower) or "release" in title_lower or "changelog" in title_lower or "what's new" in title_lower:
        return weight
    return 0.0


def compute_heuristic_score(candidate: DigestCandidate, config: HeuristicConfig) -> float:
    title_lower = (candidate.title or "").lower()
    summary_lower = (candidate.summary or "").lower()
    source_lower = (candidate.source or "").lower()

    score = 0.0
    if any(term in title_lower for term in GA_TERMS):
        score += config.ga
    if any(term in title_lower for term in PREVIEW_TERMS):
        score += config.preview
    if any(term in title_lower for term in POSTMORTEM_TERMS):
        score += config.postmortem
    if "cve-" in title_lower or "cve-" in summary_lower or any(term in title_lower for term in SECURITY_TERMS):
        score += config.security
        # Boost security items with quantified impact (downloads, victims, etc.)
        text = f"{title_lower} {summary_lower}"
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in SECURITY_IMPACT_PATTERNS):
            score += 3
    if any(term in title_lower for term in DEPRECATION_TERMS):
        score += config.deprecation
    if any(term in title_lower for term in PERFORMANCE_TERMS):
        score += config.performance
    if any(term in source_lower for term in config.brand_keywords):
        score += config.brand_weight
    if any(term in title_lower for term in OPEN_SOURCE_TERMS):
        score += config.open_source
    if any(term in title_lower for term in LANGUAGE_FEATURE_TERMS):
        score += config.language_feature
    if any(term in title_lower for term in BRANCH_TERMS):
        score += config.branch
    if any(term in title_lower for term in SDK_TERMS):
        score += config.sdk
    if any(term in title_lower for term in PART_TWO_TERMS):
        score += config.part_two
    if any(term in title_lower for term in GOVERNMENT_TERMS):
        score += config.government
    score += _iac_release_bonus(title_lower, config.iac_release)
    if any(term in title_lower for term in PRACTICAL_TERMS) or any(term in summary_lower for term in PRACTICAL_TERMS):
        score += config.practical_example

    host_lower = ""
    try:
        parsed = urlparse((getattr(candidate, "canonical_url", "") or candidate.link or "").strip())
        host_lower = (parsed.netloc or "").lower()
    except Exception:
        host_lower = ""
    if host_lower:
        if any(host_lower.endswith(policy_host) for policy_host in AI_POLICY_HOSTS):
            if any(term in title_lower for term in AI_POLICY_TERMS) or any(term in summary_lower for term in AI_POLICY_TERMS):
                score -= config.policy_penalty
            if any(term in title_lower for term in AI_FINANCE_TERMS) or any(term in summary_lower for term in AI_FINANCE_TERMS):
                score -= config.finance_penalty

    if any(term in title_lower for term in ("ec2", "instance", "compute")):
        score += 6

    canonical = (getattr(candidate, "canonical_url", "") or "").lower()
    if "github.com/hashicorp/terraform/releases/tag/" in canonical:
        score += 12
    if "github.com/aws/aws-cdk/releases/tag/" in canonical:
        score += 12

    if any(term in title_lower for term in NEG_WEBINAR_TERMS):
        score -= config.negative_webinar
    if any(term in title_lower for term in CLICKBAIT_TERMS):
        score -= config.negative_clickbait

    is_recent_announcement = source_lower == "recent announcements"
    if is_recent_announcement and config.ra_penalty:
        if not any(term in title_lower for term in RA_STRONG_TERMS):
            score -= config.ra_penalty
    if is_recent_announcement and config.ra_low_signal_penalty:
        if any(term in title_lower for term in AWS_WHATS_NEW_LOW_SIGNAL):
            score -= config.ra_low_signal_penalty
    if config.region_penalty and any(term.lower() in title_lower for term in AWS_REGION_TERMS):
        score -= config.region_penalty
    if is_recent_announcement and config.tls_penalty:
        if any(term in title_lower for term in NEG_TLS_TERMS):
            score -= config.tls_penalty

    return max(0.0, min(100.0, score))


def score_candidate(candidate: DigestCandidate, profile: ScoreProfile, model_score: float | None = None) -> tuple[float, float, float]:
    heuristic = compute_heuristic_score(candidate, profile.heuristic)
    model = profile.blend.effective_model_score(heuristic, model_score)
    combined = profile.blend.combine(heuristic, model_score)
    return round(heuristic, 3), round(model, 3), round(combined, 3)


__all__ = [
    "ScoreBlend",
    "ScoreProfile",
    "SCORING_PROFILES",
    "get_profile",
    "infer_category",
    "score_candidate",
    "classify_recent_announcement",
]


def classify_recent_announcement(candidate: DigestCandidate) -> str:
    title_lower = (candidate.title or "").lower()
    summary_lower = (candidate.summary or "").lower()
    instance_low_terms = (
        "instance type",
        "instance types",
        "instance family",
        "instance families",
        "instance size",
        "instance sizes",
        "instance class",
        "instance classes",
        "instances",
    )
    admin_low_terms = (
        "console",
        "dashboard",
        "screen recording",
        "terms of use",
        "privacy policy",
        "invoice",
        "billing",
        "view and connect",
        "view instances",
        "onboarding",
        "alerts via",
        "time-off",
        "time off",
        "schedule adherence",
        "analytics data lake",
    )

    # Check for partner/program announcements first (downgrade to low unless it's a security incident)
    has_partner_terms = any(term in title_lower for term in PARTNER_PROGRAM_TERMS)
    has_security_incident = any(term in title_lower for term in ("cve", "vulnerability", "exploit", "breach"))

    if has_partner_terms and not has_security_incident:
        return "low"

    if any(term in title_lower for term in ("cve", "cve-", "security bulletin", "security vulnerability", "privilege escalation", "vulnerability")):
        return "critical"
    if "vulnerability" in summary_lower or "zero-day" in title_lower:
        return "critical"

    if any(term in title_lower for term in AWS_WHATS_NEW_LOW_SIGNAL):
        return "low"
    if any(term.lower() in title_lower for term in AWS_REGION_TERMS):
        return "low"
    if any(term in title_lower for term in instance_low_terms):
        return "low"
    if any(term in title_lower for term in admin_low_terms):
        return "low"
    if "ec2" in title_lower and "instance" in title_lower:
        return "low"

    if any(term in title_lower for term in ("security", "firewall", "guardduty", "shield", "threat", "ddos", "protection", "iam", "policy")):
        return "high"
    if any(term in title_lower for term in ("terraform", "aws cdk", "cdk", "cloudformation")):
        return "high"
    if any(term in title_lower for term in DEPRECATION_TERMS):
        return "high"
    if any(term in title_lower for term in GA_TERMS):
        if any(term in title_lower for term in ("ec2", "redshift", "network firewall", "iac", "terraform", "cdk")):
            return "high"
        return "medium"
    if any(term in title_lower for term in PREVIEW_TERMS):
        return "medium"

    return "medium"
