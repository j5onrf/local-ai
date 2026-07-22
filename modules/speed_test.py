# ~/.config/local-ai/modules/speed_test.py
import time
import sys

_start_time = None
_think_start_time = None
_think_end_time = None
_think_chars = 0
_ans_chars = 0
_in_thinking = False

def start() -> None:
    """Begins the timer and resets state."""
    global _start_time, _think_start_time, _think_end_time, _think_chars, _ans_chars, _in_thinking
    _start_time = time.time()
    _think_start_time = None
    _think_end_time = None
    _think_chars = 0
    _ans_chars = 0
    _in_thinking = False

def count_token(content: str, is_thinking: bool = False) -> None:
    """Accumulates content character counts for precise token estimation across generation phases."""
    global _think_chars, _ans_chars, _in_thinking, _think_start_time, _think_end_time
    if not content:
        return
    
    now = time.time()
    if is_thinking:
        if not _in_thinking:
            _in_thinking = True
            if _think_start_time is None:
                _think_start_time = now
        _think_chars += len(content)
    else:
        if _in_thinking:
            _in_thinking = False
            _think_end_time = now
        _ans_chars += len(content)

def end(actual_out_tokens: int = None, is_local: bool = False) -> None:
    """Calculates, prints token statistics (including thinking TPS for local runs), and resets state."""
    global _start_time, _think_start_time, _think_end_time, _think_chars, _ans_chars, _in_thinking
    if _start_time is None:
        return
    
    total_elapsed = time.time() - _start_time
    if total_elapsed <= 0:
        total_elapsed = 0.001

    if _in_thinking and _think_end_time is None:
        _think_end_time = time.time()

    total_chars = _think_chars + _ans_chars
    if actual_out_tokens is not None and actual_out_tokens > 0:
        total_tokens = actual_out_tokens
    else:
        total_tokens = max(1, round(total_chars / 4.0)) if total_chars > 0 else 0

    think_tokens = round((_think_chars / total_chars) * total_tokens) if total_chars > 0 and _think_chars > 0 else 0
    ans_tokens = max(0, total_tokens - think_tokens)

    think_duration = 0.0
    if _think_start_time and _think_end_time:
        think_duration = max(0.001, _think_end_time - _think_start_time)
    elif _think_start_time:
        think_duration = max(0.001, total_elapsed)

    ans_duration = max(0.001, total_elapsed - think_duration) if think_duration > 0 else total_elapsed
    tps_total = total_tokens / total_elapsed if total_elapsed > 0 else 0.0

    if is_local and think_tokens > 0 and think_duration > 0:
        msg = f"\033[90m [ think: {think_tokens} | ans: {ans_tokens} | {total_tokens} tokens | {total_elapsed:.1f}s @ {tps_total:.1f} t/s ]\033[0m\n"
    else:
        msg = f"\033[90m [ {total_tokens} tokens | {total_elapsed:.2f}s | {tps_total:.2f} t/s ]\033[0m\n"

    sys.stdout.write(msg)
    sys.stdout.flush()

    _start_time = None
    _think_start_time = None
    _think_end_time = None
    _think_chars = 0
    _ans_chars = 0
    _in_thinking = False
