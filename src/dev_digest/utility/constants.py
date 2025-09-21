WINDOW_DAYS = 7  # collect last 7d to catch late posts
MAX_PER_FEED = 10  # safety cap per feed
MAX_STORIES_TOTAL = 50  # safety cap across feeds

# Selection and layout controls
PER_SECTION_CAP = 8  # max items per section in the digest
TOP_PICKS_COUNT = 2  # how many 'Interesting Reads' to feature at the top

OUT_DIR = "out"

# markdown footer
MARKDOWN_FOOTER = "\n\n Generated with ❤️ using [weirdion/dev-digest](https://github.com/weirdion/dev-digest).\n"

KEYWORDS_TO_IGNORE = [
    "training-and-certification",
    "govcloud",
    "partner network",
    "regional launches",
    "The Real Python Podcast",
    "more regions",
    "gartner",
    "aws weekly roundup",
    "extended support",
    "now available in",
    "outposts"
]

# Model profiles and pricing (USD per 1K tokens)
# Adjust the model_id strings to match your provider/region naming if needed.
MODEL_PROFILES = {
    "sonnet-4": {
        "display_name": "Claude Sonnet 4",
        "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "pricing": {
            "input_per_1k": 0.003,
            "output_per_1k": 0.015,
            "batch_input_per_1k": 0.0015,
            "batch_output_per_1k": 0.0075,
            "cache_write_per_1k": 0.00375,
            "cache_read_per_1k": 0.0003,
        },
    },
    "sonnet-3.7": {
        "display_name": "Claude 3.7 Sonnet",
        "model_id": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "pricing": {
            "input_per_1k": 0.003,
            "output_per_1k": 0.015,
            "batch_input_per_1k": None,   # N/A
            "batch_output_per_1k": None,  # N/A
            "cache_write_per_1k": 0.00375,
            "cache_read_per_1k": 0.0003,
        },
    },
}

DEFAULT_MODEL_KEY = "sonnet-3.7"

# Heuristic filters/keywords
CLICKBAIT_TERMS = [
    "unlocking", "next-generation", "revolutionize", "revolutionizing", "ultimate",
    "game-changing", "seamless", "empower", "supercharge", "unleash", "transformative",
]

AWS_WHATS_NEW_LOW_SIGNAL = [
    "now supports", "now available", "is available", "adds support", "adds quota",
    "quota visibility", "service quotas", "limits", "available in", "region", "regions",
]

# Common AWS region/location indicators to down-rank regional announcements
AWS_REGION_TERMS = [
    "us-east-1", "us-west-1", "us-west-2", "eu-west-1", "eu-west-2", "eu-central-1",
    "ap-south-1", "ap-northeast-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
    "sa-east-1", "me-south-1", "me-central-1", "af-south-1",
    "Tokyo", "Seoul", "Singapore", "Sydney", "Frankfurt", "London", "Paris", "Ireland",
    "Mumbai", "Sao Paulo", "Bahrain", "Hyderabad", "Melbourne", "Ohio", "N. Virginia",
]

# Developer-preference signals
PERFORMANCE_TERMS = [
    "performance", "latency", "throughput", "scalability", "benchmark",
    "allocator", "allocation", "memory leak", "memory usage", "garbage collector",
    "gc", "profiling", "pprof", "flamegraph", "perf", "optimiz",
]

LANGUAGE_FEATURE_TERMS = [
    "rust", "memory safety", "borrow checker", "wasm", "zig",
    "python", "pep ", "type hint", "typing", "no gil", "cpython",
]

IAC_HIGH_SIGNAL_TERMS = [
    "terraform", "pulumi", "cdk", "aws cdk", "infrastructure as code",
]
