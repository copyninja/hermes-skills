---
title: kite-connect
description: "Kite Connect API auth + read-only portfolio/margin access via local callback server."
name: kite-connect
version: 1.0.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: MIT
category: finance
metadata:
  hermes:
    tags: [zerodha, kite, trading, portfolio, api, auth]
    related_skills: []
---

# Kite Connect Skill

Manage Kite Connect v3 authentication (daily login flow) and read-only portfolio/margin endpoints via a local callback server.

## When to Use

- Daily morning: run `kite_bridge auth` to complete login flow and store `access_token` (valid until 6 AM next day).
- Anytime: `kite_bridge holdings`, `kite_bridge positions`, `kite_bridge margins` to fetch read-only data.
- Cron reminder at 6:05 AM: "Token expired, run `kite_bridge auth`".

## Prerequisites

- Zerodha trading account with 2FA TOTP enabled.
- Kite Connect developer app: `api_key`, `api_secret`, redirect URL set to `http://localhost:8765/kite/callback`.
- Python 3.10+ with `httpx`, `cryptography` (for token encryption).
- `gnome-keyring` or `secret-tool` for secure secret storage (recommended).

## Configuration

Create `~/.config/kite-connect/config.toml`:

```toml
api_key = "your_api_key"
api_secret = ""  # or store in keyring: secret-tool store --label=kite-connect api_secret
redirect_url = "http://localhost:8765/kite/callback"
token_file = "~/.local/share/kite-connect/token.enc"
callback_port = 8765
```

**Never commit `api_secret` or tokens to git.** Use keyring.

## Hermes Tool Invocations

When user asks for portfolio data, run these exact `terminal` commands:

### Daily Authentication (run each morning)
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge auth
```
- Opens browser for Kite login with 2FA
- Saves encrypted `access_token` valid until 6 AM next day
- Returns exit code 0 on success

### Get Holdings (long-term equity)
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge holdings
```
Returns JSON array of holdings with `tradingsymbol`, `quantity`, `average_price`, `last_price`, `pnl`, `day_change_percentage`.

### Get Positions (derivatives + intraday)
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge positions
```
Returns JSON with `net` and `day` position arrays.

### Get Margins (funds & margin)
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge margins
```
Returns JSON with `equity` and `commodity` margin details.

### Get User Profile
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge profile
```

### Check Token Status
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge status
```
Returns JSON: `{"status": "valid|expired|no_token", "valid": true|false, "expires_at": "...", "remaining_hours": N, "remaining_minutes": M}`

## Procedure: Daily Auth

1. Run `kite_bridge auth` (starts HTTP server on `localhost:8765`).
2. Browser opens `https://kite.zerodha.com/connect/login?v=3&api_key=...&redirect_params=source%3Dhermes`.
3. Log in with credentials + 2FA TOTP on Zerodha page.
4. Redirect hits `http://localhost:8765/kite/callback?request_token=XXX`.
5. Server computes `checksum = sha256(api_key + request_token + api_secret)`.
6. POST `https://api.kite.trade/session/token` → receives `access_token`.
7. Encrypt `access_token` + expiry (6 AM next day) → save to `token_file`.
8. Print confirmation; server shuts down.

## Procedure: Read Endpoints

All read commands:
1. Load & decrypt `access_token` from `token_file`.
2. Verify not expired (expires 6 AM daily).
3. Call Kite API with `Authorization: token api_key:access_token`.
4. Return parsed JSON to stdout.

## Token Expiry Handling

- `access_token` expires at **6:00 AM IST daily** (regulatory).
- `kite_bridge status` shows hours remaining.
- Cron job (suggested): `5 6 * * * cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge status` → check and alert.

## Security Notes

- `api_secret` **never** sent to browser; only used server-side for checksum.
- `access_token` encrypted at rest (Fernet/AES-GCM) with key from keyring or passphrase.
- Local callback server binds to `127.0.0.1` only — no external exposure.
- Redirect URL must match exactly in developer console.

## Pitfalls

- **2FA TOTP required** — cannot automate login; human must approve daily.
- **`refresh_token` not available** for standard developer accounts (only approved platforms).
- **Redirect URL mismatch** → login fails; verify in developer console.
- **Token file corruption** → delete and re-run `kite_bridge auth`.
- **Clock skew** → token expiry check uses local time; ensure NTP synced.
- **Rate limits** — Kite allows ~3 req/sec; read tools are lightweight.

## Verification

- `kite_bridge auth` → prints "✅ Token saved, valid until 2026-11-16 06:00 IST".
- `kite_bridge holdings` → returns array of holdings with `tradingsymbol`, `quantity`, `pnl`, `last_price`.
- `kite_bridge margins` → returns `equity.net`, `equity.available.cash`, `commodity.net`.
- `kite_bridge status` → shows `{"status": "valid", "valid": true, "remaining_hours": 14, "remaining_minutes": 32}` or `{"status": "expired", "valid": false}`.

## References

- `references/kite-api.md` — endpoint details, response schemas.
- `references/token-encryption.md` — Fernet key derivation, storage.
- `references/cron-setup.md` — systemd timer / crontab for 6 AM reminder.