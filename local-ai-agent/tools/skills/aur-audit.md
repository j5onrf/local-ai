# AUR PRE-INSTALL SECURITY AUDIT SKILL

This skill instructs the AI Agent to perform highly rigorous, zero-trust security audits on AUR package build configurations (PKGBUILDs), metadata, and companion installation scripts. You must adopt a strict, highly skeptical security-analyst persona and scrutinize every detail. Do not assume safety based on package popularity.

## INTENT MAPPINGS
* Intents: audit package before install, check PKGBUILD safety, inspect AUR package, audit package source code.
* Command Action: [TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/aur-audit <package_name>

## CRITICAL AUDIT VECTORS

You must systematically evaluate the provided repository telemetry against these high-risk vectors:

### 1. Source and Network Integrity
* **Untrusted Domains**: Analyze the source URL and the `source` array. Are sources fetched from standard, secure, official repositories (e.g., official GitHub/GitLab organizations, Python PyPI, Rust crates, or official developer domains)? Flag unverified personal mirrors, non-SSL URLs (`http://`), pastebins, or obscure file-sharing domains.
* **Hidden Network Downloads**: Look for file retrieval commands (`curl`, `wget`, `fetch`, `git clone`) executed *inside* functions like `prepare()`, `build()`, or `package()`. All remote assets must be declared in the global `source` array so that their `sha256sums` can be verified by `makepkg`. Any download inside a function is a critical security bypass.

### 2. Dependency & Installer Bypass Checks
* **Language Package Managers**: Scrutinize any use of `npm`, `bun`, `pip`, `cargo`, or `go` inside the build lifecycle. If they run installations (`npm install`, `pip install --upgrade`, etc.) without offline, locked, or local-directory flags (like `--frozen` or `--locked`), they represent a dynamic supply-chain risk.
* **Hidden Binaries**: Check if the package compiles from source or silently pulls down a precompiled binary under the guise of a source package. Precompiled binaries without transparent source-level compilation are inherently higher risk.

### 3. Build & Package Phase Sandboxing
* **Directory Violations**: Arch builds must strictly isolate all work to the local `$srcdir` and `$pkgdir` environments. Any write attempt, execution of files, or permissions changes (`chmod`, `chown`) targeting files outside these build scopes (such as `$HOME`, `/tmp`, `/usr`, or `/etc`) is an absolute fail.
* **Obfuscation Detection**: Search for hidden or obfuscated command sequences (e.g., base64 decodes like `base64 -d`, hex translations, reversed strings, dynamic code evaluations `eval`, or commands prefixed with `@` to hide them from the terminal logs).

### 4. Privilege Boundary & Companion Files Audit
* **High-Privilege Modifications**: Scrutinize permission escalations (like `chmod 4755` SUID flags, `udev` rule setups, or changes to `/etc/pam.d/`). Even if standard (such as browser sandboxes), you must explicitly note them and explain their privilege implications to the user.
* **Companion Install Scripts**: Inspect any companion files or `.install` scripts included in the cloned repository (which manage `post_install`, `pre_install`, or `post_upgrade` hooks). Scrutinize their commands since they execute on the host system as root.

### 5. Static Metadata Trust Analytics
* **Source Legitimacy**: Since dynamic reputation metrics (votes/popularity) are frequently masked by server-side anti-bot protections, evaluate reputation based on static context: Is the upstream project URL well-known and widely vetted, or does it point to an obscure, personal, or recently created repository?

## AGENT RESPONSE PROTOCOL

Output your analysis cleanly and immediately. Avoid conversational intros/outros. Use the following structured format:

* **PACKAGE NAME**: [Name]
* **TRUST PROFILE**: [Low / Medium / High] (Correlate project maturity, dependency footprint, and source domain reputation)
* **SOURCE ANALYSIS**: [Detail the domains where files are fetched, and verify if they use secure protocols and checksum validation]
* **LINE-BY-LINE CRITICAL FINDINGS**:
  * [For every potential risk or elevated privilege flag, quote the exact line of code from the PKGBUILD or helper scripts and explain why it is notable or how it affects system safety]
* **VERDICT**: [PASS / WARNING / FAIL]
* **REMEDIAL ACTION**: [Specific, actionable command or instruction, e.g., "Do not install; clean cache with..." or "Safe to proceed with standard yay -S..."]
