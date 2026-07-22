# File: ~/.config/local-ai/modules/agent_usage.py
import os
import json
import time

LEDGER_PATH = os.path.expanduser("~/.config/local-ai/.spend_ledger.json")

# Current mid-2026 standard API pricing rates (per 1,000,000 tokens)
PRICING_MAP = {
    "gpt-5.5": {"in": 2.00, "out": 8.00},
    "gpt-5": {"in": 1.50, "out": 6.00},
    "claude-fable-5": {"in": 3.00, "out": 12.00},
    "claude-sonnet-5": {"in": 1.00, "out": 4.00},
    "claude-opus-4-8": {"in": 4.50, "out": 18.00},
    "gemini-3.1-flash-lite": {"in": 0.075, "out": 0.30},
    "gemini-3.5-flash": {"in": 0.075, "out": 0.30},
    "local-model": {"in": 0.0, "out": 0.0}
}

def record(model: str, in_tok: int, out_tok: int, cost: float = 0.0) -> None:
    """Records token metrics and transaction costs to a daily spend database."""
    today = time.strftime("%Y-%m-%d")
    
    if cost == 0.0:
        pricing = None
        for key, val in PRICING_MAP.items():
            if key in model.lower():
                pricing = val
                break
        if pricing:
            cost = ((in_tok * pricing["in"]) + (out_tok * pricing["out"])) / 1000000.0

    data = {"date": today, "total_cost": 0.0, "models": {}}
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                temp = json.load(f)
                if temp.get("date") == today:
                    data = temp
        except Exception:
            pass

    m_data = data["models"].get(model, {"in": 0, "out": 0, "cost": 0.0})
    m_data["in"] += in_tok
    m_data["out"] += out_tok
    m_data["cost"] += cost
    data["models"][model] = m_data
    data["total_cost"] += cost

    try:
        os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
        with open(LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def refresh_balance_async(min_age: int = 10) -> None:
    """Async ledger synchronizer mapping OpenRouter backend endpoints."""
    pass


def turn_line(in_tok: int, out_tok: int, cost: float, ctx_used: int, ctx_max: int = None) -> str:
    """Generates a structured terminal diagnostic summary line."""
    today_cost = 0.0
    if cost > 0.0 and os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                today_cost = json.load(f).get("total_cost", 0.0)
        except Exception:
            pass

    ctx_max = ctx_max or 8192
    ctx_pct = (ctx_used / ctx_max) * 100
    
    dim = "\033[90m"
    reset = "\033[0m"
    green = "\033[32m"

    # Completely omit cost and today spend metrics for $0 / local model turns
    cost_part = f"cost: {green}${cost:.5f}{dim} | " if cost > 0.0 else ""
    today_part = f"today: {green}${today_cost:.4f}{dim} | " if (cost > 0.0 and today_cost > 0.0) else ""

    return (
        f"{dim} [ {in_tok} in | {out_tok} out | "
        f"{cost_part}{today_part}"
        f"ctx: {ctx_pct:.1f}% ]{reset}"
    )
