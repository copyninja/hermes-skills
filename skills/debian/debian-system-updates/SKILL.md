---
title: debian-system-updates
description: "Run apt full-upgrade; handle dpkg/apt-listbugs issues."
name: debian-system-updates
version: 1.0.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: MIT
category: debian
metadata:
  hermes:
    tags: [debian, apt, upgrade, dpkg, maintenance]
    related_skills: [software-installation, debian-package-maintenance]
---

# Debian System Updates Skill

Run `apt full-upgrade` on Debian (sid/testing/stable) and recover from
common interruption scenarios: apt-listbugs holds, dpkg lock contention,
and partial upgrades.

## When to Use

- User asks to update/upgrade the system.
- `apt full-upgrade` fails or hangs.
- dpkg reports "dpkg was interrupted, you must manually run 'sudo dpkg --configure -a'".
- apt-listbugs blocks upgrade on a serious bug.

## Prerequisites

- Debian-based system (check `/etc/os-release`).
- Sudo access for apt/dpkg (user has whitelisted apt/dpkg in sudoers).
- Network connectivity to Debian mirrors and third-party repos.

## Procedure

1. **Update package lists**
   ```bash
   sudo apt update
   ```

2. **Run full upgrade** (background for large upgrades >500MB)
   ```bash
   DEBIAN_FRONTEND=noninteractive sudo apt full-upgrade -y
   ```
   - Use `DEBIAN_FRONTEND=noninteractive` to avoid prompts.
   - For downloads >500MB, run as tracked background process (Hermes `terminal` with `background=true`, `notify=true`).

3. **If apt-listbugs blocks upgrade** (serious bug hold)
   - Output shows: `serious bugs of <pkg> ... Exiting with an error in order to stop the installation.`
   - Option A: Accept the bug temporarily
     ```bash
     sudo apt listbugs override <pkg>
     sudo apt full-upgrade -y
     ```
   - Option B: Hold the package and upgrade the rest
     ```bash
     sudo apt-mark hold <pkg>
     sudo apt full-upgrade -y
     ```
   - Option C: Report/inspect bug first (`apt-listbugs show <pkg>`).

4. **If dpkg is interrupted** ("dpkg was interrupted")
   ```bash
   sudo dpkg --configure -a
   ```
   Then resume:
   ```bash
   DEBIAN_FRONTEND=noninteractive sudo apt full-upgrade -y
   ```

5. **Clean up after upgrade**
   ```bash
   sudo apt autoremove -y
   sudo apt autoclean
   ```

## Pitfalls

- **apt-listbugs halts the entire upgrade** on serious/critical bugs. The upgrade does not continue automatically. Override or hold the package to proceed.
- **dpkg lock files persist** after interruption (`/var/lib/dpkg/lock`, `/var/lib/dpkg/lock-frontend`). Check with `lsof` before assuming another process holds them; stale locks from crashed dpkg are common.
- **Large upgrades (1GB+) exceed foreground timeout**. Use background tracked process with notification; do not re-run the command.
- **sudo requires TTY for password** even with whitelisted commands if NOPASSWD is not set. User must run `sudo dpkg --configure -a` manually in their terminal when this occurs.
- **Kernel upgrades require reboot**. Check `linux-image-*` in upgrade list; plan reboot after.
- **Third-party repos (Chrome, Tailscale, GitHub CLI, etc.)** may have slower mirrors. Allow extra download time.

## Verification

- `apt list --upgradable` returns empty.
- `dpkg --audit` returns clean.
- `systemctl is-system-running` reports `running` or `degraded` (not `maintenance`).

## References

- `references/apt-listbugs-handling.md` — apt-listbugs override/hold workflows.
- `references/dpkg-recovery.md` — dpkg interruption recovery steps.
