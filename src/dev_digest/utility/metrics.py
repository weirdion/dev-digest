import json
from typing import Any, Dict, Optional, Tuple
from dev_digest.utility.constants import MODEL_PROFILES


def extract_usage(agent_result: Any) -> Dict[str, int]:
    """
    Try to extract token usage from a Strands AgentResult, supporting multiple shapes.
    Returns a dict with keys: input_tokens, output_tokens, total_tokens (when derivable).
    """
    in_tok = out_tok = total = 0

    # Common places to look
    candidates: Tuple[Optional[dict], ...] = (
        getattr(agent_result, "usage", None),
        getattr(agent_result, "metrics", None),
        getattr(agent_result, "raw", None),
        getattr(agent_result, "message", None),
        None,
    )

    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        # Popular key variants
        in_tok = in_tok or int(obj.get("input_tokens") or obj.get("prompt_tokens") or 0)
        out_tok = out_tok or int(obj.get("output_tokens") or obj.get("completion_tokens") or 0)
        total = total or int(obj.get("total_tokens") or 0)
        if in_tok or out_tok or total:
            break

    # Compute total if missing
    if not total and (in_tok or out_tok):
        total = in_tok + out_tok

    return {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": total,
    }


def estimate_cost_usd_by_model(model_key: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD using built-in pricing profiles for the given model key."""
    profile = MODEL_PROFILES.get(model_key) or {}
    pricing = profile.get("pricing") if isinstance(profile, dict) else None
    if not isinstance(pricing, dict):
        return 0.0
    in_price = float(pricing.get("input_per_1k") or 0.0)
    out_price = float(pricing.get("output_per_1k") or 0.0)
    return (input_tokens / 1000.0) * in_price + (output_tokens / 1000.0) * out_price


def usage_summary(agent_result: Any, model_key: str = "", model_id: str = "") -> Dict[str, Any]:
    usage = extract_usage(agent_result)
    cost = estimate_cost_usd_by_model(model_key, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
    return {
        "model_key": model_key,
        "model": model_id or model_key,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "estimated_cost_usd": round(cost, 6),
    }


def to_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
