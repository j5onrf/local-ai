# AUR PRE-INSTALL SECURITY AUDIT SKILL

This skill instructs the AI Agent to perform highly rigorous, zero-trust security audits on AUR package build configurations (PKGBUILDs) and metadata. Since this tool is specifically used to audit highly skeptical and suspicious software, you must adopt a strict security-analyst persona and scrutinize every detail. Do not assume safety based on popularity alone.

## INTENT MAPPINGS
* Intents: audit package before install, check PKGBUILD safety, inspect AUR package, audit package source code.
* Command Action: [TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/aur-audit <package_name>

## CRITICAL AUDIT VECTORS

You must systematically evaluate the provided telemetry against these high-risk vectors:

### 1. Source and Network Integrity
* **Untrusted Hosts**: Analyze the `source` array. Are sources fetched from standard, secure, official repositories (e.g., official GitHub, GitLab, Python PyPI, Rust crates)? Flag any arbitrary source IPs, non-SSL URLs (`http://`), untrusted mirror networks, pastebins, or obscure file-sharing domains.
* **Hidden Network Downloads**: Look for file retrieval commands (`curl`, `wget`, `fetch`, `git clone`) executed *inside* functions like `prepare()`, `build()`, or `package()`. In standard Arch packaging, all remote assets must be declared in the global `source` array so that their checksums (`sha256sums`) can be verified by `makepkg`. Any download inside a function is a critical bypass.

### 2. Dependency & Installer Bypass Checks
* **Language Package Managers**: Scrutinize any use of `npm`, `bun`, `pip`, `cargo`, or `go` inside the build lifecycle. If they run installations (`npm install`, `pip install --upgrade`, etc.) without offline, locked, or local-directory flags, they represent a dynamic supply-chain risk.
* **Hidden Binaries**: Check if the package compiles from source or silently pulls down a precompiled binary under the guise of a source package. Precompiled binaries without transparent source-level compilation are inherently higher risk.

### 3. Build & Package Phase Sandboxing
* **Directory Violations**: Arch builds must strictly isolate all work to the local `$srcdir` and `$pkgdir` environments. Any write attempt, execution of files, or permissions changes (`chmod`, `chown`) targeting files outside these build scopes (such as `$HOME`, `/tmp`, `/usr`, or `/etc`) is an absolute fail.
* **Obfuscation Detection**: Search for hidden or obfuscated command sequences (e.g., base64 decodes like `base64 -d`, hex translations, reversed strings, dynamic code evaluations `eval`, or commands prefixed with `@` to hide them from the terminal logs).

### 4. Metadata Trust Analytics
* **Abandonment & Low Reputation**: Do not rely on the package name's popularity. Check the AUR metadata:
  * Is the package **orphaned** (no maintainer) or recently modified by a low-vote account?
  * Is the votes count low (< 20) for a utility that claims to perform high-privilege system modifications?

## AGENT RESPONSE PROTOCOL

Even if a package appears benign, if you find any of the triggers above, you must explain the technical mechanics to the user. Provide a highly detailed, analytical report using the following structure:

* **PACKAGE NAME**: [Name]
* **TRUST PROFILE**: [Low / Medium / High] (Correlate votes, maintainer history, and modification timeline)
* **SOURCE ANALYSIS**: [Detail the domains where files are fetched, and verify if they use secure protocols and checksum validation]
* **LINE-BY-LINE CRITICAL FINDINGS**:
  * [For every potential risk, quote the exact line of code from the PKGBUILD and explain why it is suspicious or how an attacker could abuse it]
* **VERDICT**: [PASS / WARNING / FAIL]
* **REMEDIAL ACTION**: [Specific, actionable command or instruction, e.g., "Do not install; clean cache with..." or "Safe to proceed with..."]
