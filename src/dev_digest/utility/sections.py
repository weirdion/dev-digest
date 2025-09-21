from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse
from typing import Iterable, Tuple


@dataclass(frozen=True)
class Section:
    slug: str
    title: str
    order: int
    max_items: int
    keywords: Tuple[str, ...] = ()
    source_terms: Tuple[str, ...] = ()
    host_terms: Tuple[str, ...] = ()
    path_contains: Tuple[str, ...] = ()
    exclude_hosts: Tuple[str, ...] = ()
    exclude_path_contains: Tuple[str, ...] = ()

    def matches(self, *, title: str, source: str, link: str, summary: str = "") -> bool:
        text = f"{title} {summary}".lower()
        source_lower = (source or "").lower()
        parsed = urlparse(link or "")
        host_lower = (parsed.netloc or "").lower()
        path_lower = (parsed.path or "").lower()

        if self.exclude_hosts and any(term in host_lower for term in self.exclude_hosts):
            return False
        if self.exclude_path_contains and any(token in path_lower for token in self.exclude_path_contains):
            return False

        if self.source_terms and any(term in source_lower for term in self.source_terms):
            return True
        if self.host_terms and any(term in host_lower for term in self.host_terms):
            return True
        if self.path_contains and any(token in path_lower for token in self.path_contains):
            return True
        if self.keywords and any(term in text for term in self.keywords):
            return True
        return False


SECTIONS: Tuple[Section, ...] = (
    Section(
        slug="security",
        title="Security & Alerts",
        order=10,
        max_items=8,
        keywords=(
            "security",
            "cve",
            "vulnerable",
            "ransom",
            "breach",
            "incident",
            "exploit",
            "zero-day",
            "zeroday",
            "ddos",
            "malware",
            "patch",
            "threat",
            "encryption",
            "guardduty",
            "shield",
        ),
        source_terms=("security", "cisa", "nessus"),
        exclude_path_contains=("/blogs/machine-learning/",),
    ),
    Section(
        slug="infrastructure",
        title="Infrastructure & Tooling",
        order=15,
        max_items=7,
        keywords=(
            "terraform",
            "pulumi",
            "cloudformation",
            "infrastructure as code",
            "infrastructure-as-code",
            "iac",
            "devops",
            "deployment",
            "pipelines",
            "sdk",
            "cli",
            "command line",
            "aws toolkit",
            "toolkit",
            "build system",
            "infrastructure",
            "cdk",
        ),
        source_terms=("devops", "operations"),
        host_terms=(
            "hashicorp.com",
            "aws.amazon.com/blogs/compute",
            "aws.amazon.com/blogs/developer",
        ),
        path_contains=(
            "hashicorp/terraform",
            "aws/aws-cdk",
            "terraform/releases",
        ),
    ),
    Section(
        slug="aws_cloud",
        title="AWS & Cloud",
        order=20,
        max_items=8,
        keywords=(
            "aws",
            "amazon",
            "cloudfront",
            "cloudformation",
            "lambda",
            "s3",
            "sagemaker",
            "bedrock",
            "ec2",
            "aurora",
            "rds",
            "dynamodb",
            "cloudwatch",
            "eks",
            "ecs",
            "fargate",
            "neptune",
            "route 53",
            "route53",
        ),
        source_terms=("aws", "amazon"),
    ),
    Section(
        slug="ml_ai",
        title="ML & AI",
        order=40,
        max_items=8,
        keywords=(
            " ai",
            "machine learning",
            "ml ",
            " llm",
            "foundation model",
            "inference",
            "training",
            "cuda",
            "neuron",
            "anthropic",
            "openai",
            "gemini",
            "deepmind",
            "stability",
        ),
        source_terms=("ai", "machine learning"),
    ),
    Section(
        slug="dev_lang",
        title="Dev Tools & Languages",
        order=50,
        max_items=6,
        keywords=(
            "python",
            "rust",
            "golang",
            "typescript",
            "javascript",
            "compiler",
            "interpreter",
            "project management",
            "package manager",
            "lint",
            "formatter",
            "ide",
            "editor",
            "developer tools",
            "repl",
        ),
        source_terms=("developer", "python", "rust", "github"),
        host_terms=("realpython.com", "pythoninsider", "github.blog"),
    ),
    Section(
        slug="kubernetes",
        title="Kubernetes/Containers",
        order=60,
        max_items=6,
        keywords=(
            "kubernetes",
            "k8s",
            "container",
            "helm",
            "istio",
            "cncf",
            "pod",
            "cluster",
        ),
        source_terms=("kubernetes", "cncf", "containers"),
    ),
    Section(
        slug="misc",
        title="Misc",
        order=100,
        max_items=8,
    ),
)


SECTION_BY_SLUG = {section.slug: section for section in SECTIONS}


@lru_cache(maxsize=None)
def ordered_sections() -> Tuple[Section, ...]:
    return tuple(sorted(SECTIONS, key=lambda sec: sec.order))


def resolve_section(title: str, source: str, link: str = "", summary: str = "") -> Section:
    for section in ordered_sections():
        if section.slug == "misc":
            continue
        if section.matches(title=title, source=source, link=link, summary=summary):
            return section
    return SECTION_BY_SLUG["misc"]


def section_titles() -> Iterable[str]:
    return (section.title for section in ordered_sections())


def section_by_title(title: str) -> Section:
    for section in ordered_sections():
        if section.title == title:
            return section
    return SECTION_BY_SLUG["misc"]
