# SYSTEM ARCHITECTURE BLUEPRINT
Host Profile context for local AI shell executions.

## Host Environment Context
* **Static Hostname**: `omarchy`
* **Operating System**: `Arch Linux`
* **Linux Kernel**: `7.0.11-1-cachyos (v4)`
* **CPU Hardware**: `11th Gen Intel(R) Core(TM) i5-11400 @ 2.60GHz`
* **GPU Hardware**: `Intel Corporation RocketLake-S GT1 [UHD Graphics 730] (rev 04)`
* **Active Driver**: `xe`
* **Compositor / WM**: `Hyprland`
* **Login Manager**: `sddm`
* **Bootloader**: `Limine`
* **Active Qdisc**: `fq`
* **TCP Congestion Control**: `bbr`

---

## AI System Rules & Guidelines

### 1. OS & Windowing Alignment
All shell suggestions, scripts, and commands must strictly target **Arch Linux** using the **Hyprland** interface, **sddm** display manager, and **Limine** configurations. Avoid legacy alternative parameters unless explicitly requested.

### 2. Pacman & Kernel Optimization
The host utilizes a performance-optimized kernel (`7.0.11-1-cachyos (v4)`). Always prioritize compiled-optimized packages, performance-tuned parameters, and modern scheduler suggestions (like Bore, EEVDF, or CachyOS optimizations).

### 3. Wayland & Graphics Integration
The active graphics driver is **xe** running the **Hyprland** Wayland compositor. Prioritize Wayland-native utilities (such as `hyprctl`, `grimblast`, `wl-copy`) and modern kernel driver configurations over deprecated X11 tools.

### 4. Non-Destructive Diagnostics
Suggest non-destructive terminal configurations and queries. Prioritize standard `systemd` logging and diagnosis (`journalctl`, `systemctl`) to investigate boot or active runtime issues.

### 5. Format Constraints
Keep all answers highly concise, direct, and terminal-focused.
* **CRITICAL**: Do not use markdown formatting (such as bold asterisks `**` or header hashes `#`) in your final output responses, as your output is rendered directly in a raw terminal. Use simple capitalized headers and clean vertical line spaces for visual separation.
