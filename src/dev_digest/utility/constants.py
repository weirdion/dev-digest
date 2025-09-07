WINDOW_DAYS = 7  # collect last 7d to catch late posts
MAX_PER_FEED = 10  # safety cap per feed
MAX_STORIES_TOTAL = 50  # safety cap across feeds

# Selection and layout controls
PER_SECTION_CAP = 8  # max items per section in the digest
TOP_PICKS_COUNT = 2  # how many 'Interesting Reads' to feature at the top

OUT_DIR = "out"

KEYWORDS_TO_IGNORE = [
    "end-of-support",
    "training-and-certification",
    "govcloud",
    "partner network",
    "regional launches",
    "The Real Python Podcast",
    "more regions",
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
