# /home/j5/.config/local-ai/tools/modules/context.py
import requests

def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    """Queries llama-server's local tokenize endpoint to get precise token counts."""
    try:
        response = requests.post(
            f"{server_url}/tokenize",
            json={"content": text},
            timeout=2
        )
        if response.status_code == 200:
            return len(response.json().get("tokens", []))
    except Exception:
        pass
    # Fallback heuristic: approx 1.3 words per token if the server is offline
    return int(len(text.split()) * 1.3)

def show_memory_status(messages: list, max_context: int = 8192, server_url: str = "http://localhost:8080"):
    """Formats context, queries token size, and displays a clean visual usage bar."""
    formatted_chat = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        formatted_chat += f"<|im_start|>{role}\n{content}<|im_end|>\n"
    
    # Append final prompt syntax
    formatted_chat += "<|im_start|>assistant\n"
    
    used = get_accurate_token_count(formatted_chat, server_url)
    remaining = max(0, max_context - used)
    pct = (used / max_context) * 100
    
    # Progress bar configuration (safely clamped between 0 and 100% boundary)
    bar_length = 20
    filled_length = min(bar_length, max(0, int(round(bar_length * (pct / 100)))))
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    print(f"\n[sys] Context Window: {used}/{max_context} tokens")
    print(f"[sys] Usage: [{bar}] {pct:.1f}%")
    print(f"[sys] Remaining: {remaining} tokens\n")
