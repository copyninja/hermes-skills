# Kite Connect MF (Mutual Fund) API Reference

## Base URL
```
https://api.kite.trade
```

## Headers (All Requests)
```
X-Kite-Version: 3
Authorization: token {api_key}:{access_token}
```

## Endpoints

### GET /mf/holdings
Mutual fund holdings in DEMAT.

**Response:**
```json
[
  {
    "tradingsymbol": "INF194KB1AL4",
    "fund": "BANDHAN SMALL CAP FUND - DIRECT PLAN",
    "folio": "5512109/39",
    "last_price": 56.766,
    "last_price_date": "",
    "quantity": 12445.264,
    "pnl": 0.0,
    "xirr": 0.0,
    "average_price": 51.466728,
    "discrepancy": false,
    "pledged_quantity": 0.0,
    "las_quantity": 0.0
  }
]
```

### GET /mf/orders
Orders from last 7 days only.

**Response:**
```json
[
  {
    "order_id": "ba802329-23f4-4814-b332-60b8661c0ba9",
    "exchange_order_id": "3197550340",
    "status": "PROCESSING",
    "settlement_id": null,
    "exchange_timestamp": null,
    "order_timestamp": "2026-11-13 18:10:01",
    "placed_by": "XS1927",
    "amount": 5000.0,
    "quantity": 0.0,
    "status_message": "Order sent to AMC.",
    "last_price": 0.0,
    "last_price_date": null,
    "average_price": 0.0,
    "fund": "MOTILAL OSWAL MIDCAP FUND - DIRECT GROWTH",
    "transaction_type": "BUY",
    "folio": null,
    "tradingsymbol": "INF247L01445",
    "purchase_type": "ADDITIONAL",
    "variety": "stp",
    "sip_id": "18629320",
    "tag": null,
    "fund_source": "mandates",
    "payment_source": "mandates",
    "payment_confirmed": false,
    "payment_details": {...},
    "meta": {...},
    "instruction_id": "...",
    "payment_allowed": false,
    "lifecycle": [...]
  }
]
```

### GET /mf/sips
All active and paused SIPs.

**Response:**
```json
[
  {
    "status": "PAUSED",
    "instalment_day": 0,
    "tradingsymbol": "INF204K01XI3",
    "transaction_type": "BUY",
    "last_instalment": "2026-07-30 01:37:04",
    "next_instalment": "2026-08-14",
    "created": "2024-12-02 09:50:53",
    "dividend_type": "growth",
    "sip_id": "1bc0e965-0fd6-4e82-857d-7cb5c7b9fac9",
    "fund": "Nippon India Large Cap Fund - Direct Plan",
    "frequency": "15-days",
    "instalments": -1,
    "pending_instalments": -1,
    "completed_instalments": 15,
    "instalment_amount": 7000.0,
    "tag": "coiniossip",
    "trigger_price": 0,
    "weekday": null,
    "sip_type": "sip",
    "exchange": "NSE",
    "sip_reg_num": null,
    "fund_source": "rp-pg",
    "step_up": {"02-12": 10},
    "mandate_type": "",
    "mandate_id": null
  }
]
```

## Key Limitations

| Limitation | Impact |
|------------|--------|
| `/mf/orders` only returns last 7 days | XIRR calculation incomplete for funds with longer history; falls back to simple returns (current NAV vs avg price) |
| No `/mf/orders/all` endpoint | Cannot fetch full transaction history via API |
| `xirr` field in holdings always 0 | Must compute client-side |
| SIP status often `PAUSED` after completion | Completed SIPs show as PAUSED; check `completed_instalments` |

## XIRR Calculation Notes

The bridge implements XIRR using Newton-Raphson on cashflows:
- BUY orders → negative cashflow (outflow)
- SELL orders → positive cashflow (inflow)
- Current holding value → final positive cashflow

**Fallback**: When order history is insufficient (API limit), returns `null` for XIRR and provides `simple_return_pct` = `(current_NAV - avg_price) / avg_price * 100`.

## Rate Limits

Same as main API: ~3 req/sec per `api_key`.