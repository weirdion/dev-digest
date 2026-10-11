WINDOW_DAYS = 7  # collect last 7d to catch late posts
MAX_PER_FEED = 10  # safety cap per feed
MAX_STORIES_TOTAL = 50  # safety cap across feeds

# Selection and layout controls
PER_SECTION_CAP = 8  # max items per section in the digest
TOP_PICKS_COUNT = 2  # how many 'Interesting Reads' to feature at the top

OUT_DIR = "out"

# markdown footer
MARKDOWN_FOOTER = "\n\n Generated with ❤️ using [weirdion/dev-digest](https://github.com/weirdion/dev-digest) and curated by [Ankit Patterson](https://substack.com/@weirdion).\n"

# Standardized Substack tag set for Developer Newsletter posts
SUBSTACK_TAGS = [
    "AWS", "DevOps", "Kubernetes", "Security", "Python", "IaC", "Containers",
    "News", "ML", "MLOps", "Agentic AI", "AI", "Bedrock", "CDK", "CI/CD",
    "CLI", "Claude", "Cloud Engineering", "Data Engineering", "Data Pipeline",
    "developers", "Disaster Recovery", "ETL", "GenAI", "Gemini", "Github",
    "GPT", "Infrastructure As Code", "SageMaker", "Serverless",
    "Software Engineering", "software development", "technology", "Terraform",
]

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
    "unlock", "unlocking", "next-generation", "revolutionize", "revolutionizing", "ultimate",
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
    "Philippines", "Makati", "Manila", "Vietnam", "Kansas City", "Kansas", "Missouri", "MO",
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

PRACTICAL_TERMS = [
    "real-world",
    "real world",
    "case study",
    "playbook",
    "field guide",
    "deep dive",
    "production",
    "practical",
]

AI_POLICY_TERMS = [
    "policy",
    "politic",
    "legislation",
    "legislature",
    "bill",
    "congress",
    "senate",
    "senator",
    "house",
    "doj",
    "department of justice",
    "department of war",
    "department of defense",
    "pentagon",
    "lawsuit",
    "court",
    "stalker",
    "grant",
    "funding",
    "campaign",
    "election",
    "regulation",
    "ban",
    "military",
    "lays off",
    "layoff",
    "workforce",
    "mental health",
]

AI_POLICY_HOSTS = [
    "arstechnica.com",
    "openai.com",
]

AI_FINANCE_TERMS = [
    "earnings",
    "revenue",
    "profit",
    "loss",
    "shares",
    "stock",
    "valuation",
    "quarter",
    "q1",
    "q2",
    "q3",
    "q4",
]

# Performance improvement indicators (for overflow routing)
PERFORMANCE_WIN_PATTERNS = [
    r"\d+x\s+(faster|improvement|performance|throughput)",
    r"(latency|response time)\s+reduc",
    r"\d+%\s+(faster|improvement|performance)",
]

# Security quantified impact indicators (for score boosting)
SECURITY_IMPACT_PATTERNS = [
    r"\d+[KM]?\+?\s+downloads?",
    r"\d+[KM]?\+?\s+packages?",
    r"\d+[KM]?\+?\s+victims?",
    r"active exploitation",
    r"in the wild",
    r"actively exploited",
]

# Partner/program keywords that should downgrade AWS RA severity
PARTNER_PROGRAM_TERMS = [
    "partner",
    "specialization",
    "certification",
    "program",
    "initiative",
    "service ready",
    "competency",
]

# Real Python tutorial down-ranking (2026-10-11)
# Real Python publishes ~20 items/week, mostly beginner/intermediate tutorials.
# Across the 2026-09-13, 2026-09-20 and 2026-09-27 runs these needed manual
# trims every week, and on 2026-10-11 one took a top-pick slot ("What Can I Do
# With Python?"), which is what triggered the scoring change. The
# keeper shapes (version-preview series, monthly news roundups) score in the same
# 28-49 band as the tutorials, so a host-wide penalty is not separable -- these
# patterns target title shape instead. Allow patterns win over penalty patterns.
REALPYTHON_KEEP_PATTERNS = [
    # Version coverage: "Python 3.15 Preview: frozendict", "Python 3.14: Cool
    # New Features for You to Try", "What's New in Python 3.14".
    r"python\s+\d+\.\d+",
    # Monthly news roundup: "... and Other Python News for August 2026",
    # "Python's JIT Faces Some Challenges and Other News for July 2026".
    r"\band other\s+(python\s+)?news\b",
    # PEP / standards coverage: "Tool-Agnostic Python Lock Files With PEP 751".
    r"\bpep[\s-]*\d+",
]

REALPYTHON_TUTORIAL_PATTERNS = [
    # Instructional lead-ins.
    r"^how (to|long|do|does)\b",
    r"^what (can|is|are|does|exactly)\b",
    r"^when (should|to)\b",
    r"^(why|where)\b",
    r"^(using|implementing|exploring|validating|sending|writing|automate|build|get started)\b",
    r"^(primer|learning path|learn from|tutorial)\b",
    r"^an? (effective|close look|new python)\b",
    # "<Topic> in Python", "<Topic> in Python: ...", "<X> With Python".
    r"\bin python\b",
    r"\bwith python\b",
    r"\bfor python\b",
    # Guides and fundamentals.
    r":\s*(a|the)\b.*\b(guide|tutorial|basics|primer|introduction)\b",
    r"\b(complete guide|a guide|basics|fundamentals|first steps|beginner)\b",
    # Editor/tool bake-offs: "Cursor vs Copilot", "Gemini CLI vs Claude Code".
    # Deliberately NOT a bare r"\bvs\b" -- a library comparison with real
    # benchmarks ("Polars vs pandas") can be worth keeping, so this only matches
    # the "which is better/best for X" framing that marks the opinion pieces.
    r"\bvs\.?\b.*\bwhich (is|one|to)\b",
    r"\bwhich (ai )?(editor|tool|code editor) is (better|best)\b",
    # The recurring AI vibe-check series.
    r"draws a python reading a book",
    # Career / learning-path content.
    r"\b(get you hired|study schedule|learning roadmap|learn python)\b",
    # "Python's deque: Implement Efficient Queues", "Python Classes: The Power
    # of OOP", "Django Tasks: Exploring the Built-in Tasks Framework" -- the
    # "<Subject>: <gerund/verb phrase>" explainer shape. Anchored on the colon
    # so it cannot reach a "Python 3.15 Preview:" title (already allow-listed).
    r"^[^:]{0,40}:\s*(implement|exploring|connect|convert|try out|the power|what are|how to|a |an |your )",
    # Stdlib/builtin explainers: "Python sleep()", "Python Inner Functions",
    # "Python Practice Problems", "The Python Standard REPL".
    r"^(the\s+)?python(\'s)?\s+(standard\s+)?(repl|sleep|inner|practice|classes|built-in|builtin|deque|mcp\b)",
    # Recurring Real Python idioms for style/teaching pieces.
    r"\b(the pythonic way|best practices|explained)\b",
]
