import sys
import types


def test_normalize_source_aws_paths():
    # Stub feedparser before importing FeedHandler
    if "feedparser" not in sys.modules:
        sys.modules["feedparser"] = types.SimpleNamespace(parse=lambda url: types.SimpleNamespace(entries=[], feed={"title": url}))

    from dev_digest.handler.FeedHandler import FeedHandler

    fh = FeedHandler()
    # What's New
    assert fh._normalize_source("https://aws.amazon.com/about-aws/whats-new/2024/", "fallback").lower() == "recent announcements"
    # Security bulletins
    assert fh._normalize_source("https://aws.amazon.com/security/security-bulletins/", "fb").lower() == "security bulletins"
    # Blogs mapping
    assert fh._normalize_source("https://aws.amazon.com/blogs/ai/", "fb") == "AWS Blog - Artificial Intelligence"
    assert fh._normalize_source("https://aws.amazon.com/blogs/machine-learning/xyz", "fb") == "AWS Machine Learning Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/compute/", "fb") == "AWS Compute Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/database/", "fb") == "AWS Database Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/containers/", "fb") == "AWS Containers Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/devops/", "fb") == "AWS DevOps & Developer Productivity Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/networking-and-content-delivery/", "fb") == "Networking & Content Delivery"
    assert fh._normalize_source("https://aws.amazon.com/blogs/architecture/", "fb") == "AWS Architecture Blog"
