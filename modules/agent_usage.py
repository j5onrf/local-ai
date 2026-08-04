# File: ~/.config/local-ai/modules/agent_usage.py
"""Local-AI Agent Token Usage & Spend Ledger Manager"""

import os, json, time
from typing import Optional

LEDGER_PATH: str = os.path.expanduser("~/.config/local-ai/.spend_ledger.json")

PRICING_MAP = {
    "gpt-5.5": {"in": 2.00, "out": 8.00}, "gpt-5": {"in": 1.50, "out": 6.00},
    "claude-fable-5": {"in": 3.00, "out": 12.00}, "claude-sonnet-5": {"in": 1.00, "out": 4.00},
    "claude-opus-4-8": {"in": 4.50, "out": 18.00}, "gemini-3.1-flash-lite": {"in": 0.075, "out": 0.30},
    "gemini-3.5-flash": {"in": 0.075, "out": 0.30}, "local-model": {"in": 0.0, "out": 0.0}
}


def record(model: str, in_tok: int, out_tok: int, cost: float = 0.0) -> None:
    """Records token metrics and transaction costs to a daily spend database."""
    today = time.strftime("%Y-%m-%d")
    if cost == 0.0 and (pricing := next((v for k, v in PRICING_MAP.items() if k in model.lower()), None)):
        cost = ((in_tok * pricing["in"]) + (out_tok * pricing["out"])) / 1000000.0

    data = {"date": today, "total_cost": 0.0, "models": {}}
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                if (temp := json.load(f)).get("date") == today: data = temp
        except Exception: pass

    m_data = data["models"].setdefault(model, {"in": 0, "out": 0, "cost": 0.0})
    m_data["in"] += in_tok; m_data["out"] += out_tok; m_data["cost"] += cost
    data["total_cost"] += cost

    try:
        os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
        tmp = f"{LEDGER_PATH}.tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        os.replace(tmp, LEDGER_PATH)
    except Exception: pass


def refresh_balance_async(min_age: int = 10) -> None:
    """Async ledger synchronizer mapping OpenRouter backend endpoints."""
    pass


def turn_line(in_tok: int, out_tok: int, cost: float, ctx_used: int, ctx_max: Optional[int] = None) -> str:
    """Generates a structured terminal diagnostic summary line."""
    today_cost = 0.0
    if cost > 0.0 and os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                today_cost = json.load(f).get("total_cost", 0.0)
        except Exception: pass

    ctx_pct = (ctx_used / (ctx_max or 8192)) * 100
    cost_part = f"cost: \033[32m${cost:.5f}\033[90m | " if cost > 0.0 else ""
    today_part = f"today: \033[32m${today_cost:.4f}\033[90m | " if (cost > 0.0 and today_cost > 0.0) else ""

    return f"\033[90m [ {in_tok} in | {out_tok} out | {cost_part}{today_part}ctx: {ctx_pct:.1f}% ]\033[0m"
