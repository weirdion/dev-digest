WINDOW_DAYS = 7  # collect last 7d to catch late posts
MAX_PER_FEED = 10  # safety cap per feed
MAX_STORIES_TOTAL = 50  # safety cap across feeds

OPEN_AI_MODEL = "gpt-5-mini"

OUT_DIR = "out"

KEYWORDS_TO_IGNORE = [
    "training-and-certification",
    "govcloud",
    "partner network",
    "regional launches",
]

SYSTEM_PROMPT = (
    "You are a seasoned Senior Cloud Engineer focused on backend, AWS, "
    "DevOps, networking, security, and developer tooling. "
    "Produce a concise, actionable weekly newsletter from the past 7 days. "
    "Group items into sections (AWS & Cloud; CLI & Dev Tools; Python; "
    "Git & Workflow; Kubernetes / Containers; Security Alerts; Edge / Infra). "
    "Exclude AWS regional launches, partner network announcements, GovCloud items, "
    "and training and certification content. "
    "For each bullet: say what's new, why it matters, and a clean link to the original post. "
    "Output pure Markdown suitable for Substack. Keep it tight."
)
