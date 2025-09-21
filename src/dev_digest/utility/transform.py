from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ReleaseInfo:
    title: str
    family: str | None
    tag: str | None
    is_release: bool
    is_prerelease: bool


def format_release_title(title: str, link: str) -> ReleaseInfo:
    if not link:
        return ReleaseInfo(title=title, family=None, tag=None, is_release=False, is_prerelease=False)

    parsed = urlparse(link)
    path = (parsed.path or "").strip("/").lower()
    if not path:
        return ReleaseInfo(title=title, family=None, tag=None, is_release=False, is_prerelease=False)

    segments = path.split("/")
    if len(segments) < 4 or segments[-2] != "tag":
        return ReleaseInfo(title=title, family=None, tag=None, is_release=False, is_prerelease=False)

    tag = segments[-1]
    family = None
    if "hashicorp" in path and "terraform" in path:
        family = "Terraform"
    elif "aws" in path and "aws-cdk" in path:
        family = "AWS CDK"

    if not family:
        return ReleaseInfo(title=title, family=None, tag=None, is_release=False, is_prerelease=False)

    is_prerelease = any(token in tag for token in ("beta", "alpha", "rc"))
    formatted_title = title
    if is_prerelease:
        formatted_title = f"{family} {tag} (Pre-release)"
    else:
        formatted_title = f"{family} {tag} (Release notes)"

    return ReleaseInfo(
        title=formatted_title,
        family=family,
        tag=tag,
        is_release=True,
        is_prerelease=is_prerelease,
    )


__all__ = ["format_release_title", "ReleaseInfo"]
