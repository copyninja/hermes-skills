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
- **Mutual Funds**: `kite_bridge mf-holdings`, `kite_bridge mf-orders`, `kite_bridge mf-sips`, `kite_bridge mf-xirr`
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

## Keyring Storage (GNOME Keyring)

```bash
# Correct syntax: secret-tool store --label=<label> <attribute> <value> <secret>
secret-tool store --label=kite-connect api_secret kite-connect "your_api_secret_here"

# Verify
secret-tool lookup label kite-connect api_secret kite-connect
```

The `secret-tool` command requires attribute-value pairs. The label is for display; the attribute+value are the lookup keys.

## Family Account Access

**API tokens are user-scoped** — each access token returns data only for the authenticated user. Console family view (UI) does not extend to API. To access a family member's data:
- They must create their own developer app at `developers.kite.trade`
- Run their own login flow (their 2FA)
- Store their token separately (e.g., `token-wife.enc`, separate config profile)
- Query via separate bridge invocation with their profile

**No shared/impersonation access** via API.

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

### Get Equity Orders (today)
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge orders
```
Returns JSON array of today's equity/F&O orders with `order_id`, `tradingsymbol`, `transaction_type`, `quantity`, `price`, `status`, `order_timestamp`.

### Get Equity Trades (today)
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge trades
```
Returns JSON array of today's executed trades (fills) with `trade_id`, `order_id`, `tradingsymbol`, `quantity`, `price`, `trade_timestamp`.

### Get MF Holdings
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge mf-holdings
```
Returns JSON array of MF holdings with fund name, folio, quantity, NAV, average price.

### Get MF Orders (last 7 days)
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge mf-orders
```
Returns JSON array of recent MF orders (BUY/SELL/SIP) with status, amounts, NAV dates.

### Get Active SIPs
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge mf-sips
```
Returns JSON array of SIPs with frequency, amount, status, step-up details.

### Compute MF XIRR
```bash
cd ~/devel/hermes-skills/skills/finance/kite-connect && .venv/bin/python -m scripts.kite_bridge mf-xirr
```
Returns XIRR (annualized return) per fund + portfolio-level. **Note**: Limited by Kite API 7-day order history; uses simple returns as fallback.

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
- **Equity orders/trades are today-only** — `/orders` and `/trades` endpoints return only current trading day data. For historical orders, export Tradebook from Kite Console (Reports → Tradebook).

## Verification

- `kite_bridge auth` → prints "✅ Token saved, valid until 2026-11-16 06:00 IST".
- `kite_bridge holdings` → returns array of holdings with `tradingsymbol`, `quantity`, `pnl`, `last_price`.
- `kite_bridge margins` → returns `equity.net`, `equity.available.cash`, `commodity.net`.
- `kite_bridge status` → shows `{"status": "valid", "valid": true, "remaining_hours": 14, "remaining_minutes": 32}` or `{"status": "expired", "valid": false}`.
- `kite_bridge orders` → returns today's equity/F&O orders (empty array if none).
- `kite_bridge trades` → returns today's executed trades (empty array if none).
- `kite_bridge mf-holdings` → 6 funds with fund name, folio, quantity, NAV, avg price.
- `kite_bridge mf-orders` → recent orders with status, transaction_type, amount.
- `kite_bridge mf-sips` → 4 SIPs (all PAUSED) with frequency, instalment_amount, step_up.
- `kite_bridge mf-xirr` → per-fund simple returns + portfolio XIRR (limited by 7-day order history).

## References

- `references/kite-api.md` — endpoint details, response schemas.
- `references/token-encryption.md` — Fernet key derivation, storage.
- `references/cron-setup.md` — systemd timer / crontab for 6 AM reminder.