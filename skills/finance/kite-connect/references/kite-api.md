# Kite Connect API Reference

## Base URL
```
https://api.kite.trade
```

## Headers (All Requests)
```
X-Kite-Version: 3
Authorization: token {api_key}:{access_token}
```

## Endpoints Used by This Skill

### GET /session/token (POST actually)
Exchange `request_token` for `access_token`.

**Request:**
```
POST /session/token
Content-Type: application/x-www-form-urlencoded

api_key=xxx&request_token=yyy&checksum=zzz
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "access_token": "xxx",
    "user_id": "XX0000",
    "user_name": "Name",
    "email": "user@example.com",
    "broker": "ZERODHA",
    "exchanges": ["NSE", "NFO", "BSE", "MCX", "MF"],
    "products": ["CNC", "NRML", "MIS"],
    "order_types": ["MARKET", "LIMIT", "SL"],
    "login_time": "2026-11-15 09:30:00"
  }
}
```

### GET /portfolio/holdings
Long-term equity holdings (DEMAT).

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "tradingsymbol": "SBIN",
      "exchange": "NSE",
      "instrument_token": 779521,
      "isin": "INE062A01020",
      "product": "CNC",
      "quantity": 16,
      "average_price": 801.78,
      "last_price": 762.45,
      "close_price": 766.40,
      "pnl": -629.30,
      "day_change": -3.95,
      "day_change_percentage": -0.515,
      "t1_quantity": 0,
      "realised_quantity": 16,
      "collateral_quantity": 0
    }
  ]
}
```

### GET /portfolio/positions
Short-term positions (derivatives + intraday).

**Response:**
```json
{
  "status": "success",
  "data": {
    "net": [
      {
        "tradingsymbol": "NIFTY26JAN24000CE",
        "exchange": "NFO",
        "instrument_token": 123456,
        "product": "NRML",
        "quantity": 1,
        "overnight_quantity": 1,
        "multiplier": 50,
        "average_price": 150.0,
        "last_price": 155.0,
        "close_price": 148.0,
        "value": 7750,
        "pnl": 250,
        "m2m": 250,
        "unrealised": 250,
        "realised": 0,
        "buy_quantity": 1,
        "buy_price": 150.0,
        "sell_quantity": 0
      }
    ],
    "day": [...]
  }
}
```

### GET /user/margins
Funds and margin info.

**Response:**
```json
{
  "status": "success",
  "data": {
    "equity": {
      "enabled": true,
      "net": 99725.05,
      "available": {
        "cash": 245431.6,
        "opening_balance": 245431.6,
        "live_balance": 99725.05,
        "collateral": 0,
        "intraday_payin": 0
      },
      "utilised": {
        "debits": 145706.55,
        "exposure": 38981.25,
        "span": 101989,
        "m2m_realised": 761.7
      }
    },
    "commodity": {
      "enabled": true,
      "net": 100661.7,
      "available": { ... },
      "utilised": { ... }
    }
  }
}
```

### GET /user/profile
User profile info.

**Response:**
```json
{
  "status": "success",
  "data": {
    "user_id": "AB1234",
    "user_name": "Vasudev Kamath",
    "email": "vasudev@example.com",
    "broker": "ZERODHA",
    "exchanges": ["NSE", "NFO", "BSE", "MCX"],
    "products": ["CNC", "NRML", "MIS"],
    "order_types": ["MARKET", "LIMIT", "SL"]
  }
}
```

## Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request / invalid parameters |
| 401 | Invalid/expired `access_token` |
| 403 | Permission denied (IP not whitelisted, etc.) |
| 429 | Rate limit exceeded (~3 req/sec) |
| 500 | Server error |

## Rate Limits

- **3 requests/second** per `api_key`
- **100 requests/minute** per `api_key`
- Exceeding returns 429 with `Retry-After` header

## Token Expiry

- `access_token` expires at **06:00 IST daily** (regulatory requirement)
- No `refresh_token` for standard developer accounts
- Must re-run login flow each morning