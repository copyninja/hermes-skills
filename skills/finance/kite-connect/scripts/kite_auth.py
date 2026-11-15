#!/usr/bin/env python3
"""
Kite Connect v3 — Local Callback Server + Token Manager + Read API Tools

Usage:
  python -m scripts.kite_auth auth       # Run login flow, save token
  python -m scripts.kite_auth holdings   # GET /portfolio/holdings
  python -m scripts.kite_auth positions  # GET /portfolio/positions
  python -m scripts.kite_auth margins    # GET /user/margins
  python -m scripts.kite_auth profile    # GET /user/profile
  python -m scripts.kite_auth status     # Check token expiry
"""

import asyncio
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
TOKEN_FILE = TOKEN_DIR / "token.enc"
KEYRING_LABEL = "kite-connect"

DEFAULT_CONFIG = {
    "api_key": "",
    "api_secret": "",
    "redirect_url": "http://localhost:8765/kite/callback",
    "token_file": str(TOKEN_FILE),
    "callback_port": 8765,
}

KITE_API_BASE = "https://api.kite.trade"
LOGIN_URL = "https://kite.zerodha.com/connect/login"

# ─── Helpers ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(DEFAULT_CONFIG, f)
        print(f"Created config template: {CONFIG_FILE}")
        print("Edit it with your api_key, api_secret (or store secret in keyring)")
        sys.exit(1)

    with open(CONFIG_FILE, "rb") as f:
        cfg = tomli.load(f)

    # Resolve api_secret from keyring if not in config
    if not cfg.get("api_secret"):
        try:
            import secretstorage
            bus = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(bus)
            for item in collection.get_all_items():
                if item.get_label() == KEYRING_LABEL:
                    cfg["api_secret"] = item.get_secret().decode()
                    break
        except Exception:
            pass

    if not cfg.get("api_key") or not cfg.get("api_secret"):
        print("Error: api_key and api_secret must be set in config or keyring")
        sys.exit(1)

    return cfg


def get_fernet_key(cfg: dict) -> bytes:
    """Derive Fernet key from api_secret + machine-id (stable per user)."""
    machine_id = Path("/etc/machine-id").read_text().strip() if Path("/etc/machine-id").exists() else "fallback"
    seed = (cfg["api_secret"] + machine_id).encode()
    key = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(key)


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
        # Wait up to 120 seconds for callback
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

    # Build login URL
    redirect_params = "source=hermes"
    login_url = f"{LOGIN_URL}?v=3&api_key={cfg['api_key']}&redirect_params={redirect_params}"

    print(f"🔐 Opening browser for Kite login...")
    print(f"   URL: {login_url}")
    webbrowser.open(login_url)

    # Wait for callback
    request_token = run_callback_server(port)
    if not request_token:
        return False

    print(f"📨 Got request_token, exchanging for access_token...")

    # Exchange for access_token
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

    # Encrypt and save
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    encrypted = encrypt_token(access_token, expiry, key)
    TOKEN_FILE.write_bytes(encrypted)
    os.chmod(TOKEN_FILE, 0o600)

    print(f"✅ Token saved to {TOKEN_FILE}")
    print(f"   Valid until: {expiry.strftime('%Y-%m-%d %H:%M %Z')}")
    return True


# ─── API Calls ─────────────────────────────────────────────────────────────

def load_token(cfg: dict) -> tuple[str, datetime] | None:
    key = get_fernet_key(cfg)
    if not TOKEN_FILE.exists():
        return None
    return decrypt_token(TOKEN_FILE.read_bytes(), key)


def api_get(cfg: dict, endpoint: str) -> dict | None:
    token_data = load_token(cfg)
    if not token_data:
        print("❌ No valid token. Run 'kite-auth' first.")
        return None

    access_token, expiry = token_data
    if datetime.now() >= expiry:
        print(f"❌ Token expired at {expiry}. Run 'kite-auth' to refresh.")
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
    if len(sys.argv) < 2:
        print("Usage: kite-auth <auth|holdings|positions|margins|profile|status>")
        sys.exit(1)

    cmd = sys.argv[1]
    cfg = load_config()

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
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()