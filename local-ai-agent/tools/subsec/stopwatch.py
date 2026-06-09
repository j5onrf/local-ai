#!/usr/bin/env python3
# Universal Stopwatch & Lap Timer TUI v1.3.0

import sys
import os
import tty
import termios
import select
import time
import math

def get_key_non_blocking():
    """Checks stdin for a keypress while terminal is in raw mode."""
    rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
    if rlist:
        ch = sys.stdin.read(1)
        if ch == '\033': 
            rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
            if rlist:
                ch += sys.stdin.read(2)
        return ch
    return None

def fmt_time_high_res(seconds):
    """Formats raw seconds into a highly precise HH:MM:SS.hh string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    hundredths = int((seconds % 1) * 100)
    return f"{h:02d}:{m:02d}:{s:02d}.{hundredths:02d}"

def get_elapsed(is_running, start_time, elapsed_paused):
    """Calculates true elapsed time accounting for active running state."""
    if is_running:
        return (time.time() - start_time) + elapsed_paused
    return elapsed_paused

def generate_visualizer(is_running, ticks, style_mode, current_elapsed):
    """Generates reactive chronograph visualizers synced with the timer state."""
    cols = 60

    # --- Mode 0: Linear Pulse (Default - Expanding Center Bar) ---
    if style_mode == 0:
        t = current_elapsed * 6.0 if is_running else 0.0
        width = int((math.sin(t) + 1.0) * 0.5 * 25) + 5
        side = (cols - width) // 2
        bar_content = "━" * width
        color = "\033[38;5;110m" if is_running else "\033[90m"
        return f"{' ' * side}{color}{bar_content}\033[0m{' ' * (cols - width - side)}"

    # --- Mode 1: Sweep Oscilloscope (Analog Sweep Hand) ---
    elif style_mode == 1:
        frac = (current_elapsed % 1.0)
        sweep_pos = int(frac * cols)
        line = []
        for i in range(cols):
            if i == sweep_pos:
                line.append("\033[1;32m█\033[0m" if is_running else "\033[90m█\033[0m")
            elif (sweep_pos - i) % cols < 6:
                dist = (sweep_pos - i) % cols
                greens = ["\033[38;5;46m", "\033[38;5;40m", "\033[38;5;34m", "\033[38;5;28m", "\033[38;5;22m"]
                color = greens[dist - 1] if is_running and (dist - 1) < len(greens) else "\033[90m"
                char = "▰" if is_running else "⠂"
                line.append(f"{color}{char}\033[0m")
            else:
                line.append("\033[90m⠂\033[0m")
        return "".join(line)

    # --- Mode 2: Chrono Pendulum (Clock Metronome) ---
    elif style_mode == 2:
        t = current_elapsed * math.pi
        pos = int((math.sin(t) + 1.0) * 0.5 * 53)
        pendulum = [" "] * cols
        pendulum[1] = "["
        pendulum[58] = "]"
        for idx in range(3, 57):
            if idx == pos + 3:
                pendulum[idx] = "\033[1;38;5;209m●\033[0m" if is_running else "\033[90m●\033[0m"
            else:
                pendulum[idx] = "\033[90m·\033[0m"
        return "".join(pendulum)

    # --- Mode 3: Sweep Radar (Bouncing Dot) ---
    else:
        t = current_elapsed * 4.0
        pos = int((math.sin(t) + 1.0) * 0.5 * (cols - 3))
        bar = [" "] * cols
        color = "\033[38;5;209m" if is_running else "\033[90m"
        bar[pos] = "◀"
        bar[pos+1] = "█"
        bar[pos+2] = "▶"
        return "".join(f"{color}{c}\033[0m" if c != " " else c for c in bar)

def run_stopwatch_tui():
    """Main terminal UI loop for rendering the stopwatch frames."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    # Clear terminal and hide cursor
    sys.stdout.write("\033[?25l\033[H\033[J")
    sys.stdout.flush()

    # Stopwatch variables
    is_running = False
    start_time = 0.0
    elapsed_paused = 0.0
    laps = []

    # UI variables
    ticks = 0
    visualizer_mode = 0  
    mode_names = {
        0: "Linear Pulse",
        1: "Sweep Oscilloscope",
        2: "Chrono Pendulum",
        3: "Sweep Radar"
    }

    try:
        tty.setraw(fd)

        while True:
            ticks += 1
            current_elapsed = get_elapsed(is_running, start_time, elapsed_paused)

            # Return cursor to home (prevent scrolling/jitter)
            sys.stdout.write("\033[H")
            sys.stdout.write("\r\033[1;32m CHRONOGRAPH \033[90m──────────────────────────────────────────────\033[0m\033[K\r\n\r\n")
            
            # Master Clock Display Face
            time_display = fmt_time_high_res(current_elapsed)
            sys.stdout.write(f"\r                  \033[1;39m[ {time_display} ]\033[0m\033[K\r\n\r\n")
            
            # Interactive OS-style Dual Button HUD Layout
            if is_running:
                btn_left = "\033[1;36m[L] LAP\033[0m"
                btn_right = "\033[1;31m[SPACE] STOP\033[0m"
            elif current_elapsed > 0:
                btn_left = "\033[1;33m[R] RESET\033[0m"
                btn_right = "\033[1;32m[SPACE] START\033[0m"
            else:
                btn_left = "\033[90m[L] LAP\033[0m"
                btn_right = "\033[1;32m[SPACE] START\033[0m"

            sys.stdout.write(f"\r     {btn_left:<20}{btn_right:>30}\033[K\r\n\r\n")
            
            # Chrono Dial Animation Track
            sys.stdout.write(f"\r {generate_visualizer(is_running, ticks, visualizer_mode, current_elapsed)}\033[K\r\n")

            # Progress Bar (Ceiling Loop represents progress toward the next whole minute)
            current_minute_pct = (current_elapsed % 60) / 60.0
            filled = max(0, min(60, int(current_minute_pct * 60)))
            progress_bar = f"\033[38;5;209m{'━' * filled}\033[0m\033[90m{'━' * (60 - filled)}\033[0m"
            sys.stdout.write(f"\r {progress_bar}\033[K\r\n")
            sys.stdout.write(f"\r\033[90m────────────────────────────────────────────────────────────\033[0m\033[K\r\n")

            # Running Active Lap Calculation
            if not laps:
                current_lap_time = current_elapsed
            else:
                current_lap_time = current_elapsed - laps[-1]['split_time']
            current_lap_str = fmt_time_high_res(current_lap_time)

            # Active Chrono Settings Panel
            sys.stdout.write(f"\r \033[1mTHEME:\033[0m {mode_names[visualizer_mode]:<25} \033[1mCURRENT LAP:\033[0m {current_lap_str}\033[K\r\n")

            # --- Bottom Lap History Split (with dynamic Best/Worst highlighting) ---
            sys.stdout.write("\r\n\033[90m ── Lap History ───────────────────────────────────────────────\033[0m\033[K\r\n")
            
            # Determine indices of fastest and slowest recorded laps (only active if at least 2 laps exist)
            best_lap_idx = -1
            worst_lap_idx = -1
            if len(laps) >= 2:
                lap_times = [lap['lap_time'] for lap in laps]
                min_time = min(lap_times)
                max_time = max(lap_times)
                if min_time != max_time:
                    best_lap_idx = lap_times.index(min_time)
                    worst_lap_idx = lap_times.index(max_time)

            if not laps:
                sys.stdout.write("\r  \033[90m(No Laps Recorded)\033[0m\033[K\r\n")
            else:
                for idx, lap in list(enumerate(laps))[-3:][::-1]:
                    lap_num = idx + 1
                    lap_fmt = fmt_time_high_res(lap['lap_time'])
                    split_fmt = fmt_time_high_res(lap['split_time'])
                    
                    # Apply iOS-style highlighting colors
                    if idx == best_lap_idx:
                        lap_color = "\033[1;32m"  # Green
                        tag = " (Fastest)"
                    elif idx == worst_lap_idx:
                        lap_color = "\033[1;31m"  # Red
                        tag = " (Slowest)"
                    else:
                        lap_color = "\033[0m"
                        tag = ""

                    marker = "▶ " if idx == len(laps) - 1 else "  "
                    sys.stdout.write(f"\r {marker}{lap_color}Lap {lap_num:02d}: {lap_fmt:<12}{tag:<12}\033[90m(Split: {split_fmt})\033[0m\033[K\r\n")

            # Print filler buffers if under 3 laps to preserve exact layout height constraints
            num_laps_printed = min(len(laps), 3) if laps else 1
            for _ in range(3 - num_laps_printed):
                sys.stdout.write("\r\033[K\r\n")

            sys.stdout.write("\r\033[K\r\n")
            sys.stdout.write("\r \033[90m[v] Change Theme  │  [q] Quit stopwatch\033[0m\033[K\r\n")
            sys.stdout.flush()

            # Handle keystroke inputs
            key = get_key_non_blocking()
            if key:
                if key == ' ' or key == '\r':
                    if is_running:
                        elapsed_paused += time.time() - start_time
                        is_running = False
                    else:
                        start_time = time.time()
                        is_running = True
                elif key.lower() == 'l':
                    if is_running:
                        total_elapsed = get_elapsed(is_running, start_time, elapsed_paused)
                        if not laps:
                            lap_duration = total_elapsed
                        else:
                            last_split = laps[-1]['split_time']
                            lap_duration = total_elapsed - last_split
                        laps.append({'lap_time': lap_duration, 'split_time': total_elapsed})
                elif key.lower() == 'r':
                    if not is_running and current_elapsed > 0:
                        is_running = False
                        start_time = 0.0
                        elapsed_paused = 0.0
                        laps = []
                elif key.lower() == 'v':
                    visualizer_mode = (visualizer_mode + 1) % 4
                elif key.lower() == 'q':
                    break

            time.sleep(0.03)

    except KeyboardInterrupt:
        pass
    finally:
        # Restore terminal settings and show cursor again
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?25h\033[H\033[J")
        sys.stdout.flush()

if __name__ == "__main__":
    run_stopwatch_tui()
