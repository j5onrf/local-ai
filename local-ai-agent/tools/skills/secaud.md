# SYSTEM SECURITY AUDIT DIRECTIVES

This profile outlines instructions for the AI Agent to run factual, non-alarmist security audits on foreign software surface areas, network-accessible daemons, and host privileges.

## INTENT MAPPINGS
* Intents: audit system security, run vulnerability assessment, identify local network attack surface, verify AUR packages safety, inspect running systemd services.
* Command Action: [TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/security-audit

## AUDIT CRITERIA
1. **Upstream Kernel Alignment**: Check local running kernel version (`uname -r`) against upstream stable/LTS branches on kernel.org.
2. **Systemd Services Attack Surface**: Identify active local services (specifically `systemd-resolved` and `avahi-daemon`) and outline mitigations.
3. **Flatpak & Snap Sandbox Scrutiny**: Detect installed sandbox applications and identify classic-confinement risks.
4. **Host Privilege & Identity Hardening**: Evaluate default umask, check SSH configuration folder permissions, and verify if passwordless sudo is enabled.
5. **Network Listeners & Local Firewall**: Audit active system firewalls and detect open socket ports listening on public interfaces (`0.0.0.0` or `*`).
6. **AUR Vetting & Abandonment Scan**: Assess foreign packages using non-alarmist multi-factor risk categorization (unmaintained/orphans + low votes + age + sensitive network descriptions).

## AGENT BEHAVIOR & EXECUTION GUIDELINES

### 1. Non-Alarmist Classification
* Avoid hyperbolic security warnings. If no high-priority risks are found, explicitly state that the host is in a highly secure, well-vetted state.
* Clearly highlight inactive vectors (such as an inactive `avahi-daemon.service` or disabled passwordless sudo) as positive security postures.

### 2. Rolling-Release Kernel Awareness
* Minor patch-level discrepancies (e.g., running `7.0.11` when upstream is `7.0.12`) are standard for rolling-release distributions due to mirror sync delays. Note that the system tracks a current kernel branch.

### 3. Actionable & Safe Terminal Mitigations
* If any service, port, or permission gap exposes an active surface, provide the exact, non-destructive commands to manage or harden it (e.g., `systemctl disable --now`, `chmod 700 ~/.ssh`, or firewall configuration commands).
* Keep all suggestions focused on standard Arch Linux package management (`pacman`) and configuration practices.
