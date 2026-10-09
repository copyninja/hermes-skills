---
name: software-installation
description: Install packages from scripts, sources, or binaries.
version: 1.0.0
category: debian
author: Vasudev Kamath
license: MIT
metadata:
  hermes:
    tags: [debian, installation, headless, sudo]
    related_skills: [debian-package-maintenance]
---

# Software Installation

Install software following a provided command/script or guided by web/source. Environment: headless Debian hosts, VPS, or local workstation without passwordless sudo.

## Procedure

1. **Identify the environment first** — OS, arch, privileges. Run `uname -m`, `cat /etc/os-release`, `id`. This decides the install path.
2. **Try the supplied install command first** — `curl -fsSL <script> | sh` or similar. Many auto-detect the distro and pull via apt/apk/yum, which require root.
3. **If the script needs root and you lack passwordless sudo:**
   - Static binary, Debian/Ubuntu: download `tailscale_<ver>_amd64.tgz` (or arm64) from `https://dl.tailscale.com/stable/` or GitHub releases, extract, copy binaries to `$HOME/.local/bin`.
   - Other distros: same static binary approach, or use distro-specific packages if a repo is configured.
   - Never `sudo apt install <pkg>` silently — you need the password.
4. **Verify** — `tailscale version` (or `<pkg> --version`), `which <cmd>`. Add `~/.local/bin` to PATH if not already there (it usually is on this system).
5. **Start the daemon** — `tailscaled` (static) or `systemctl start tailscaled`. Note: static daemon **cannot** create the TAP/TUN device without `CAP_NET_ADMIN`; a normal user session cannot run `tailscaled` headlessly. Use `sudo tailscaled &` or run on a machine you can sudo into.
6. **Authenticate** — `tailscale up -email kamathvasudev@gmail.com` (or the email from the context), then `tailscale status` to confirm online.

## User Preferences

- Concise, direct, no filler. State what was done and what failed, with exact paths/commands.
- Use `$HOME/.hermes/cache/scratch` for transient download/state files — never pollute the home directory with build artifacts.
- Package work on Debian: prefer `dch` + `debuild` conventions; do not hand-install .debs outside the package workflow.

## Common Pitfalls

- `curl | sh` on Debian **auto-selects apt** → needs root. The install script should be expected to fail with a sudo error.
- Static binary `tailscaled` **cannot run as a user** — TUN interface creation needs root. The client binaries are fine; the daemon is not.
- `sudo -n` will fail if there is no passwordless sudo. Test with `sudo -n true` before assuming you can use it.
- Headless/VPS sessions: no display, no `sudo -A`/askpass. Do not expect interactive prompts to work.

## References

- `references/install-methods.md` — decision table for installation methods per environment
- `references/static-binary-install.md` — step-by-step static binary install recipe