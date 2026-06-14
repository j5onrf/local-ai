# SYSTEM ARCHITECTURE BLUEPRINT
Host Profile context for local AI shell executions.

## Host Environment Context
* **Static Hostname**: `omarchy`
* **Operating System**: `Arch Linux`
* **Linux Kernel**: `7.0.11-1-cachyos (v4)`
* **CPU Hardware**: `11th Gen Intel(R) Core(TM) i5-11400 @ 2.60GHz (Max: 4.40 GHz)`
* **CPU Threads (Logical)**: `12`
* **GPU Hardware**: `Intel Corporation RocketLake-S GT1 [UHD Graphics 730] (rev 04)`
* **Active Driver**: `xe`
* **Compositor / WM**: `Hyprland`
* **Login Manager**: `sddm`
* **Bootloader**: `systemd-boot`
* **Active Qdisc**: `fq`
* **TCP Congestion Control**: `bbr`
* **Boot Filesystem**: `vfat`
* **Boot Mount Options**: `rw,noatime,fmask=0077,dmask=0077,codepage=437,iocharset=ascii,shortname=mixed,utf8,errors=remount-ro`

---

## AI System Rules & Guidelines

### 1. OS & Windowing Alignment
All shell suggestions, scripts, and commands must strictly target **Arch Linux** using the **Hyprland** interface, **sddm** display manager, and **systemd-boot** configurations. Avoid legacy alternative parameters unless explicitly requested.

### 2. Pacman & Kernel Optimization
The host utilizes a performance-optimized kernel (`7.0.11-1-cachyos (v4)`). Always prioritize compiled-optimized packages, performance-tuned parameters, and modern scheduler suggestions (like Bore, EEVDF, or CachyOS optimizations).

### 3. Wayland & Graphics Integration
The active graphics driver is **xe** running the **Hyprland** Wayland compositor. Prioritize Wayland-native utilities (such as `hyprctl`, `grimblast`, `wl-copy`) and modern kernel driver configurations over deprecated X11 tools.

### 4. Filesystem & Storage Safety
Your boot partition at `/boot` utilizes a **vfat** filesystem. NEVER suggest using `chmod` or `chown` on files or directories under `/boot` or `/efi`. If the current live **Boot Mount Options** contain `fmask=0077,dmask=0077`, the system is already secure! Inform the user that log errors related to mount permissions are purely historical entries from earlier in the boot sequence, and no action is required.

### 5. Non-Destructive Diagnostics
Suggest non-destructive terminal configurations and queries. Prioritize standard `systemd` logging and diagnosis (`journalctl`, `systemctl`) to investigate boot or active runtime issues.
