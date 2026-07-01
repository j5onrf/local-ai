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
    """Increments the generated token count based on streaming chunks."""
    global _token_count
    if content:
        # In streaming SSE responses (like llama-server), each delta content 
        # packet represents exactly one newly generated token.
        _token_count += 1

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
