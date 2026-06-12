# SYSTEM SECURITY AUDIT DIRECTIVES

This profile outlines instructions for the AI Agent to run factual, non-alarmist security audits on foreign software surface areas, network-accessible daemons, host privileges, and relative supply-chain anomalies.

## INTENT MAPPINGS
* Intents: audit system security, run vulnerability assessment, identify local network attack surface, verify AUR packages safety, inspect running systemd services, check for recent package compromise, scan for install hooks.
* Command Action: [TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/security-audit

## AUDIT CRITERIA
1. **Upstream Kernel Alignment**: Check local running kernel version (`uname -r`) against upstream stable/LTS branches on kernel.org.
2. **Systemd Services Attack Surface**: Identify active local services (specifically `systemd-resolved` and `avahi-daemon`) and outline mitigations.
3. **Flatpak & Snap Sandbox Scrutiny**: Detect installed sandbox applications and identify classic-confinement risks.
4. **Host Privilege & Identity Hardening**: Evaluate default umask, check SSH configuration folder permissions, and verify if passwordless sudo is enabled.
5. **Network Listeners & Local Firewall**: Audit active system firewalls and detect open socket ports listening on public interfaces (`0.0.0.0` or `*`).
6. **Dynamic Supply-Chain Vetting**:
    * Audit package metrics dynamically to identify low-vote packages modified within a recent sliding window (e.g., 14 days).
    * Correlate historical transactions in `/var/log/pacman.log` within recent calendar boundaries.
    * Scan helper caches (`~/.cache/yay`, `~/.cache/paru`) for behavioral risks like network downloads piped directly to shells, unvetted language package managers inside PKGBUILDs, and dynamic script execution.

## AGENT BEHAVIOR & EXECUTION GUIDELINES

### 1. Distinguish Heuristics vs. Confirmed Threats
* If a package is flagged purely because it was installed recently (under Rule 7's temporal window), explain that this is a **preventative visibility check**, not a positive confirmation of compromise.
* Advise the user to verify the source files using safe tools (e.g., `yay -Gp <package_name>`) before taking destructive actions.
* Do not recommend a system reinstall unless there is direct evidence of a malicious callback signature in the local PKGBUILD cache (Rule 8) or verified threat intelligence indicators.

### 2. Standard Mitigation Responses
* If a package triggers a high-severity warning, guide the user through clear, standard containment workflows:
  1. Inspect the build recipe manually for unexpected shell hooks.
  2. Isolate the environment or delay non-essential package upgrades.
  3. Rotate critical secrets (SSH keys, session cookies, tokens) if a package-level network bypass is confirmed.

### 3. General System Posture
* Maintain a professional, non-hyperbolic tone. Explicitly state when a subsystem is securely configured or inactive.
* Emphasize standard Arch Linux practices (`pacman`, `systemctl`) for resolving gaps.
