from typing import Any, Dict, List

from strands import Agent
from strands.agent import AgentResult
from strands.types.content import Message
from strands_tools import http_request

from dev_digest.model.content import SearchResult
from dev_digest.utility.constants import KEYWORDS_TO_IGNORE


class StrandsAgent:
    def __init__(self) -> None:
        # self.search_agent = Agent(
        #     tools=[http_request],
        #     system_prompt="You search for recent technical content and return structured JSON."
        # )
        self.summary_agent = Agent(
            model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            callback_handler=None,
            name="SummaryAgent",
            system_prompt=(
                "You are a senior cloud engineer who is parsing a feed of recent blog posts and announcements."
                "Your task is to balance signal to noise ratio, ignoring things that do not impact your day to day work,"
                "highlighting things that would be considered innovative, or news worthy in tech."
                "Use the summary to decide if the blog post should be included in the weekly "
                "newsletter. The newsletter is in Markdown with sections: AWS & Cloud; ML & AI; Infrastructure as Code;"
                "DevOps; Python; Kubernetes/Containers; CLI & Dev Tools; Security Alerts; Misc."
                "You don't have to be serious and to the point in the summaries though, feel free to add sass or humor"
                "when appropriate, without being too disrespectful though."
                "The title of the daily digest is 'Dev Digest - Week of {Month, dd}' - day of execution."
                "For the items, use this format"
                "title ({news source}) - {publication date yyyy-mm-dd}"
                "summary, and clean link to read more at the end of summary."
                "You are not a content creator trying to maximize clicks, but the audience of this newsletter."
            )
        )

    # def search_recent(self, query: str, window_days: int) -> List[Dict[str, Any]]:
    #     """Search for recent content using the search agent."""
    #     search_prompt = (
    #         f"Find 5-10 noteworthy technical articles from the last {window_days} days "
    #         f"for this audience: {query}. "
    #         "Focus on AWS services, developer tools, security updates, and infrastructure. "
    #         "Exclude regional launches, partner announcements, GovCloud, and certification content. "
    #         "Return JSON array: [{\"title\": \"...\", \"url\": \"...\", \"summary\": \"...\"}]"
    #     )
    #
    #     response = self.search_agent(search_prompt)
    #     search_result = SearchResult.from_json(response.message)
    #     filtered_result = search_result.filter_items(KEYWORDS_TO_IGNORE)
    #     return [item.to_dict() for item in filtered_result.items]

    def summarize_markdown(self, items: List[Dict[str, Any]]) -> str:
        """Generate markdown newsletter from items."""
        if not items:
            return "# Weekly Developer Digest\n\n_No items found._\n"

        items_text = "\n".join([
            f"- {item.get('title', '')} — {item.get('summary', '')} — {item.get('link', '')}"
            for item in items
        ])

        prompt = (
            f"Feed Items for this week:\n{items_text}"
        )

        response: AgentResult = self.summary_agent(prompt)

        return response.message.get("content", [{}])[0].get("text", "")


