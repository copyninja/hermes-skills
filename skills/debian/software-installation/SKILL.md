---
title: software-installation
description: "Install packages from scripts, sources, or binaries."
name: software-installation
version: 1.0.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: MIT
category: debian
metadata:
  hermes:
    tags: [debian, installation, headless, sudo]
    related_skills: [debian-package-maintenance]
---

# Software Installation Skill

Install software following a provided command/script or guided by web/source.
Environment: headless Debian hosts, VPS, or local workstation without
passwordless sudo.

## When to Use

- Install a package when the user supplies a command, script, or source.
- Set up software on headless Debian hosts, VPS, or workstations without
  passwordless sudo.
- Verify and start the installed software/daemon.

## Prerequisites

- OS, architecture, and privilege level (run `uname -m`; read `/etc/os-release`
  with read_file; `id`).
- The install script or source (remote or local).
- Sudo access if the method requires it.

## How to Run

1. Identify the environment first (OS, arch, privileges).
2. Try the supplied install command first.
3. If the script needs root and you lack passwordless sudo:
   - Static binary, Debian/Ubuntu: download the binary tarball from the upstream
     release URL, extract it, and copy the binaries to `$HOME/.local/bin`.
   - Other distros: same static-binary approach, or use distro packages if a
     repository is configured.
   - Do not silently install a distro package without the password.
4. Verify: run the binary (`<pkg> --version`), and confirm the executable is on
   the PATH (search_files for the executable name).
5. Start the daemon: `tailscaled` (static) or `systemctl start tailscaled`.
   A static daemon cannot create the TAP/TUN device without `CAP_NET_ADMIN`.
6. Authenticate: `tailscale up -email kamathvasudev@gmail.com`, then
   `tailscale status`.

## Quick Reference

- Verify: `<pkg> --version` and confirm it is on PATH.
- Start: `systemctl start tailscaled` (systemd) or `tailscaled` (static).
- Authenticate: `tailscale up -email <you@domain>`.

## Procedure

1. Identify the environment first (OS, arch, privileges).
2. Try the supplied install command first.
3. If the script needs root and you lack passwordless sudo, use the static
   binary approach or a distro package if a repository is configured.
4. Verify the binary runs and is on the PATH.
5. Start the daemon, then authenticate.

## Pitfalls

- The install script should be expected to fail with a sudo error when it is
  run without root.
- Static daemon `tailscaled` cannot run as a user: TUN interface creation needs
  root. The client binaries are fine; the daemon is not.
- `sudo -n` will fail if there is no passwordless sudo. Test with `sudo -n true`
  before assuming you can use it.
- Headless/VPS sessions: no display, no sudo -A/askpass. Do not expect
  interactive prompts to work.

## Verification

- Run the installed binary (`<pkg> --version`).
- Confirm the executable is on the PATH.
- Start and, where applicable, authenticate the daemon.

## References

- `references/install-methods.md` — decision table for installation methods per
  environment.
- `references/static-binary-install.md` — step-by-step static binary install
  recipe.
