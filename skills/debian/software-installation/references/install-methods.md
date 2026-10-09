## Installation Methods by Environment

| Environment | Privileges | Method | Notes |
|---|---|---|---|
| Local Debian/Ubuntu | User + passwordless sudo | `sudo apt install <pkg>` | Fastest, system-managed |
| Remote/VPS (headless) | No passwordless sudo | Static binary to `$HOME/.local/bin` | No systemd, no TUN, manual auth |
| Container/Docker | No privileges | Static binary + static client only | Daemon cannot start without CAP_NET_ADMIN |
| Development VM | User sudo | Static binary or apt with sudo | Run `sudo -n true` first to check |
| Mobile (iOS/Android) | Device | Official client app | Download from app store |

## Decision Table

- Run `sudo -n true` (exit 0 = passwordless sudo available)
- Run `uname -m` and `cat /etc/os-release` to identify arch and distro
- If the script auto-detects distro and uses apt/apk/yum, it needs root
- If no sudo, use static binaries from `https://dl.tailscale.com/stable/` or GitHub releases