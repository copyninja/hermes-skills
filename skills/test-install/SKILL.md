---
title: test-install
description: "Verify a package or binary installs and runs correctly."
name: test-install
version: 1.0.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [debian, installation, headless, sudo, test]
    related_skills: [debian-package-maintenance]
---

# test-install Skill

Install a package, binary, or script for testing in this environment, and verify
the installation.

## When to Use

- When you need to install a test package (binary, script, or source) for
  verification.
- When you need to confirm an installed binary runs and reports its version.

## Prerequisites

- The install script, binary, or source to test.
- Sudo access if installing system-wide.

## How to Run

1. Identify the install method (script, static binary, distro package).
2. Run the install command.
3. Verify the version and that the executable is on the PATH.

## Quick Reference

- Verify: `<pkg> --version`.
- Confirm: search_files for the executable name on PATH.

## Procedure

1. Identify the install method and environment.
2. Run the install command.
3. Verify the version and PATH.
4. Start and authenticate the daemon, if applicable.

## Pitfalls

- A script piped to a shell on Debian auto-selects apt and needs root.
- Static daemon `tailscaled` cannot run as a user (TUN creation needs root).
- `sudo -n` fails without passwordless sudo.

## Verification

- Run the installed binary and confirm its version.
- Confirm the executable is on the PATH.
- Start and, where applicable, authenticate the daemon.
