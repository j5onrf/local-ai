# ~/.config/local-ai/modules/speed_test.py
import time
import sys

_start_time = None
_token_count = 0

def start() -> None:
    """Begins the timer and resets the token count."""
    global _start_time, _token_count
    _start_time = time.time()
    _token_count = 0

def count_token(content: str) -> None:
    """Increments the generated token count based on streaming chunk length.
    
    Uses character length scaling (1 token ≈ 4 characters) to maintain accuracy
    for both local models and high-speed batched cloud APIs.
    """
    global _token_count
    if content:
        # Standardizes token estimation across both single and multi-token stream packets
        _token_count += max(1, len(content) // 4)

def end() -> None:
    """Calculates, prints the token statistics, and resets state."""
    global _start_time, _token_count
    if _start_time is None:
        return
    
    elapsed = time.time() - _start_time
    if elapsed <= 0:
        elapsed = 0.001
        
    tps = _token_count / elapsed
    
    # Print statistics in dim gray below the final answer block
    sys.stdout.write(f"\033[90m [{_token_count} tokens | {elapsed:.2f}s | {tps:.2f} t/s]\033[0m\n")
    sys.stdout.flush()
    
    # Clean up state
    _start_time = None
    _token_count = 0
