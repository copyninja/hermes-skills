#!/usr/bin/env python3
"""
Kite Connect v3 — Multi-Profile Auth + Token Manager + Read API Tools

Usage:
  python -m scripts.kite_auth --profile default auth       # Run login flow, save token
  python -m scripts.kite_auth --profile default holdings   # GET /portfolio/holdings
  python -m scripts.kite_auth --profile second positions   # GET /portfolio/positions
  python -m scripts.kite_auth --profile default margins    # GET /user/margins
  python -m scripts.kite_auth --profile default profile    # GET /user/profile
  python -m scripts.kite_auth --profile default status     # Check token expiry
  python -m scripts.kite_auth --list-profiles              # List configured profiles
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import tomli
import tomli_w
from cryptography.fernet import Fernet

# ─── Config ────────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".config" / "kite-connect"
CONFIG_FILE = CONFIG_DIR / "config.toml"
TOKEN_DIR = Path.home() / ".local" / "share" / "kite-connect"
KEYRING_LABEL_PREFIX = "kite-connect"

KITE_API_BASE = "https://api.kite.trade"
LOGIN_URL = "https://kite.zerodha.com/connect/login"

DEFAULT_PROFILE = "default"

# ─── Helpers ────────────────────────────────────────────────────────────────

def load_config(profile: str = DEFAULT_PROFILE) -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        create_default_config()
        print(f"Created config template: {CONFIG_FILE}")
        print("Edit it with your api_key, api_secret (or store secret in keyring)")
        sys.exit(1)

    with open(CONFIG_FILE, "rb") as f:
        full_config = tomli.load(f)

    profiles = full_config.get("profiles", {})
    if profile not in profiles:
        print(f"Error: Profile '{profile}' not found in config.")
        print(f"Available profiles: {list(profiles.keys())}")
        sys.exit(1)

    cfg = profiles[profile]
    cfg["profile_name"] = profile

    # Set defaults
    cfg.setdefault("redirect_url", "http://localhost:8765/kite/callback")
    cfg.setdefault("callback_port", 8765)
    cfg.setdefault("token_file", str(TOKEN_DIR / f"token-{profile}.enc"))

    # Resolve api_secret from keyring if not in config
    if not cfg.get("api_secret"):
        # Try profile-specific label first, then fallback to legacy label
        for label in [f"{KEYRING_LABEL_PREFIX}-{profile}", KEYRING_LABEL_PREFIX]:
            try:
                import secretstorage
                bus = secretstorage.dbus_init()
                collection = secretstorage.get_default_collection(bus)
                for item in collection.get_all_items():
                    if item.get_label() == label:
                        cfg["api_secret"] = item.get_secret().decode()
                        break
                if cfg.get("api_secret"):
                    break
            except Exception:
                pass

    if not cfg.get("api_key") or not cfg.get("api_secret"):
        print(f"Error: api_key and api_secret must be set for profile '{profile}' (config or keyring)")
        sys.exit(1)

    return cfg


def create_default_config():
    """Create default config with single 'default' profile."""
    default_config = {
        "profiles": {
            "default": {
                "api_key": "",
                "api_secret": "",
                "redirect_url": "http://localhost:8765/kite/callback",
                "token_file": str(TOKEN_DIR / "token-default.enc"),
                "callback_port": 8765,
            }
        }
    }
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(default_config, f)


def list_profiles():
    """List all configured profiles."""
    if not CONFIG_FILE.exists():
        print("No config file found.")
        return

    with open(CONFIG_FILE, "rb") as f:
        full_config = tomli.load(f)

    profiles = full_config.get("profiles", {})
    if not profiles:
        print("No profiles configured.")
        return

    print("Configured profiles:")
    for name, cfg in profiles.items():
        has_secret = "✓" if cfg.get("api_secret") else "✗ (keyring)"
        print(f"  {name}: api_key={cfg.get('api_key', 'NOT SET')} api_secret={has_secret}")


def get_fernet_key(cfg: dict) -> bytes:
    """Derive Fernet key from api_secret + machine-id (stable per user)."""
    machine_id = Path("/etc/machine-id").read_text().strip() if Path("/etc/machine-id").exists() else "fallback"
    seed = (cfg["api_secret"] + machine_id).encode()
    key = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(key)


def get_token_file(cfg: dict) -> Path:
    return Path(cfg["token_file"])


def encrypt_token(token: str, expiry: datetime, key: bytes) -> bytes:
    f = Fernet(key)
    payload = json.dumps({"access_token": token, "expiry": expiry.isoformat()})
    return f.encrypt(payload.encode())


def decrypt_token(data: bytes, key: bytes) -> tuple[str, datetime] | None:
    try:
        f = Fernet(key)
        payload = json.loads(f.decrypt(data).decode())
        return payload["access_token"], datetime.fromisoformat(payload["expiry"])
    except Exception:
        return None


def compute_checksum(api_key: str, request_token: str, api_secret: str) -> str:
    return hashlib.sha256(f"{api_key}{request_token}{api_secret}".encode()).hexdigest()


def next_6am() -> datetime:
    """Return 6 AM today (or tomorrow if past 6 AM)."""
    now = datetime.now()
    target = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


# ─── Callback Server ───────────────────────────────────────────────────────

from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

request_token_holder = {"token": None, "error": None}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/kite/callback":
            qs = parse_qs(parsed.query)
            if "request_token" in qs:
                request_token_holder["token"] = qs["request_token"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2>Kite Connect authenticated</h2>
                <p>Token received. You can close this window.</p>
                </body></html>
                """)
            elif "error" in qs:
                request_token_holder["error"] = qs["error"][0]
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Error: {qs['error'][0]}".encode())
            else:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # Suppress default logging


def run_callback_server(port: int) -> str | None:
    """Start server, wait for request_token, return it or None on error."""
    global request_token_holder
    request_token_holder = {"token": None, "error": None}

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"🌐 Callback server listening on http://127.0.0.1:{port}/kite/callback")
    print("   Waiting for redirect... (browser should open)")

    try:
        for _ in range(240):
            time.sleep(0.5)
            if request_token_holder["token"]:
                return request_token_holder["token"]
            if request_token_holder["error"]:
                print(f"❌ OAuth error: {request_token_holder['error']}")
                return None
        print("⏱ Timeout waiting for callback")
        return None
    finally:
        server.shutdown()


# ─── Auth Flow ─────────────────────────────────────────────────────────────

def do_auth(cfg: dict) -> bool:
    key = get_fernet_key(cfg)
    port = cfg.get("callback_port", 8765)

    redirect_params = "source=hermes"
    login_url = f"{LOGIN_URL}?v=3&api_key={cfg['api_key']}&redirect_params={redirect_params}"

    print(f"🔐 Opening browser for Kite login (profile: {cfg['profile_name']})...")
    print(f"   URL: {login_url}")
    webbrowser.open(login_url)

    request_token = run_callback_server(port)
    if not request_token:
        return False

    print(f"📨 Got request_token, exchanging for access_token...")

    checksum = compute_checksum(cfg["api_key"], request_token, cfg["api_secret"])
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{KITE_API_BASE}/session/token",
            headers={"X-Kite-Version": "3"},
            data={
                "api_key": cfg["api_key"],
                "request_token": request_token,
                "checksum": checksum,
            },
        )

    if resp.status_code != 200:
        print(f"❌ Token exchange failed: {resp.status_code} {resp.text}")
        return False

    data = resp.json()
    if data.get("status") != "success":
        print(f"❌ Token exchange error: {data}")
        return False

    access_token = data["data"]["access_token"]
    expiry = next_6am()

    token_file = get_token_file(cfg)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    encrypted = encrypt_token(access_token, expiry, key)
    token_file.write_bytes(encrypted)
    os.chmod(token_file, 0o600)

    print(f"✅ Token saved to {token_file}")
    print(f"   Valid until: {expiry.strftime('%Y-%m-%d %H:%M %Z')}")
    return True


# ─── API Calls ─────────────────────────────────────────────────────────────

def load_token(cfg: dict) -> tuple[str, datetime] | None:
    key = get_fernet_key(cfg)
    token_file = get_token_file(cfg)
    if not token_file.exists():
        return None
    return decrypt_token(token_file.read_bytes(), key)


def api_get(cfg: dict, endpoint: str) -> dict | None:
    token_data = load_token(cfg)
    if not token_data:
        print("❌ No valid token. Run 'kite-auth auth' first.")
        return None

    access_token, expiry = token_data
    if datetime.now() >= expiry:
        print(f"❌ Token expired at {expiry}. Run 'kite-auth auth' to refresh.")
        return None

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{KITE_API_BASE}{endpoint}",
            headers={
                "X-Kite-Version": "3",
                "Authorization": f"token {cfg['api_key']}:{access_token}",
            },
        )

    if resp.status_code != 200:
        print(f"❌ API error {resp.status_code}: {resp.text}")
        return None

    data = resp.json()
    if data.get("status") != "success":
        print(f"❌ API error: {data}")
        return None

    return data["data"]


# ─── Command Handlers ──────────────────────────────────────────────────────

def cmd_holdings(cfg: dict):
    data = api_get(cfg, "/portfolio/holdings")
    if data:
        print(json.dumps(data, indent=2))


def cmd_positions(cfg: dict):
    data = api_get(cfg, "/portfolio/positions")
    if data:
        print(json.dumps(data, indent=2))


def cmd_margins(cfg: dict):
    data = api_get(cfg, "/user/margins")
    if data:
        print(json.dumps(data, indent=2))


def cmd_profile(cfg: dict):
    data = api_get(cfg, "/user/profile")
    if data:
        print(json.dumps(data, indent=2))


def cmd_mf_holdings(cfg: dict):
    data = api_get(cfg, "/mf/holdings")
    if data:
        print(json.dumps(data, indent=2))


def cmd_mf_orders(cfg: dict):
    data = api_get(cfg, "/mf/orders")
    if data:
        print(json.dumps(data, indent=2))


def cmd_mf_sips(cfg: dict):
    data = api_get(cfg, "/mf/sips")
    if data:
        print(json.dumps(data, indent=2))


def cmd_status(cfg: dict):
    token_data = load_token(cfg)
    if not token_data:
        print("🔴 No token stored")
        return

    access_token, expiry = token_data
    now = datetime.now()
    if now >= expiry:
        print(f"🔴 Token EXPIRED at {expiry.strftime('%Y-%m-%d %H:%M')}")
    else:
        remaining = expiry - now
        hours = int(remaining.total_seconds() // 3600)
        mins = int((remaining.total_seconds() % 3600) // 60)
        print(f"🟢 Token valid: {hours}h {mins}m remaining (expires {expiry.strftime('%Y-%m-%d %H:%M')})")


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Kite Connect CLI")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help=f"Profile name (default: {DEFAULT_PROFILE})")
    parser.add_argument("--list-profiles", action="store_true", help="List configured profiles")
    parser.add_argument("command", nargs="?", help="Command to run")

    subparsers = parser.add_subparsers(dest="subcommand", help="Commands")

    # Auth commands
    subparsers.add_parser("auth", help="Run login flow and save token")
    subparsers.add_parser("holdings", help="GET /portfolio/holdings")
    subparsers.add_parser("positions", help="GET /portfolio/positions")
    subparsers.add_parser("margins", help="GET /user/margins")
    subparsers.add_parser("profile", help="GET /user/profile")
    subparsers.add_parser("status", help="Check token expiry")
    subparsers.add_parser("mf-holdings", help="GET /mf/holdings")
    subparsers.add_parser("mf-orders", help="GET /mf/orders")
    subparsers.add_parser("mf-sips", help="GET /mf/sips")

    args = parser.parse_args()

    if args.list_profiles:
        list_profiles()
        return

    if not args.command and not args.subcommand:
        parser.print_help()
        sys.exit(1)

    cmd = args.command or args.subcommand
    profile = args.profile

    cfg = load_config(profile)

    if cmd == "auth":
        ok = do_auth(cfg)
        sys.exit(0 if ok else 1)
    elif cmd == "holdings":
        cmd_holdings(cfg)
    elif cmd == "positions":
        cmd_positions(cfg)
    elif cmd == "margins":
        cmd_margins(cfg)
    elif cmd == "profile":
        cmd_profile(cfg)
    elif cmd == "status":
        cmd_status(cfg)
    elif cmd == "mf-holdings":
        cmd_mf_holdings(cfg)
    elif cmd == "mf-orders":
        cmd_mf_orders(cfg)
    elif cmd == "mf-sips":
        cmd_mf_sips(cfg)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()