#!/usr/bin/env python3
"""Kite Connect bridge for Hermes Agent — Multi-Profile Support.

Usage (via terminal tool):
  python -m scripts.kite_bridge --profile default holdings
  python -m scripts.kite_bridge --profile second positions
  python -m scripts.kite_bridge --profile default margins
  python -m scripts.kite_bridge --profile default profile
  python -m scripts.kite_bridge --profile default status
  python -m scripts.kite_bridge --profile default orders
  python -m scripts.kite_bridge --profile default trades
  python -m scripts.kite_bridge --profile default mf-holdings
  python -m scripts.kite_bridge --profile default mf-orders
  python -m scripts.kite_bridge --profile default mf-sips
  python -m scripts.kite_bridge --profile default mf-xirr
  python -m scripts.kite_bridge --list-profiles

Returns JSON to stdout. Errors to stderr with non-zero exit code.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure sibling modules are importable
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from kite_auth import (
    load_config,
    list_profiles,
    api_get,
    DEFAULT_PROFILE,
    load_token,
)
from datetime import datetime


def run_command(cfg: dict, command: str) -> int:
    """Execute a command and return exit code."""
    if command == "holdings":
        data = api_get(cfg, "/portfolio/holdings")
        if data:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "positions":
        data = api_get(cfg, "/portfolio/positions")
        if data:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "margins":
        data = api_get(cfg, "/user/margins")
        if data:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "profile":
        data = api_get(cfg, "/user/profile")
        if data:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "orders":
        data = api_get(cfg, "/orders")
        if data is not None:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "trades":
        data = api_get(cfg, "/trades")
        if data is not None:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "mf-holdings":
        data = api_get(cfg, "/mf/holdings")
        if data:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "mf-orders":
        data = api_get(cfg, "/mf/orders")
        if data:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "mf-sips":
        data = api_get(cfg, "/mf/sips")
        if data:
            print(json.dumps(data, ensure_ascii=False))
            return 0
        return 1
    elif command == "mf-xirr":
        result = compute_mf_xirr(cfg)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        return 1
    elif command == "status":
        token_data = load_token(cfg)
        if not token_data:
            print(json.dumps({"status": "no_token", "valid": False}))
            return 0
        access_token, expiry = token_data
        now = datetime.now()
        if now >= expiry:
            print(json.dumps({
                "status": "expired",
                "valid": False,
                "expired_at": expiry.isoformat()
            }))
        else:
            remaining = expiry - now
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            print(json.dumps({
                "status": "valid",
                "valid": True,
                "expires_at": expiry.isoformat(),
                "remaining_hours": hours,
                "remaining_minutes": mins
            }))
        return 0
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1


def compute_mf_xirr(cfg: dict) -> dict:
    """Compute XIRR for mutual fund holdings using order history."""
    # Get MF holdings
    holdings = api_get(cfg, "/mf/holdings")
    if not holdings:
        return {"error": "No MF holdings found"}

    # Get MF orders (last 7 days from API, but we need all)
    orders = api_get(cfg, "/mf/orders")
    if not orders:
        return {"error": "No MF orders found"}

    # Build cashflows per fund (tradingsymbol/ISIN)
    # XIRR: sum of discounted cashflows = 0
    # Cashflows: negative for investments (BUY), positive for redemptions (SELL)
    # Current value as final positive cashflow

    # Group orders by tradingsymbol
    fund_orders = {}
    for order in orders:
        ts = order.get("tradingsymbol")
        if not ts:
            continue
        if ts not in fund_orders:
            fund_orders[ts] = []
        fund_orders[ts].append(order)

    results = {}
    today = datetime.now().date()

    for holding in holdings:
        ts = holding.get("tradingsymbol")
        fund_name = holding.get("fund")
        current_qty = holding.get("quantity", 0)
        current_nav = holding.get("last_price", 0)
        current_val = current_qty * current_nav
        avg_price = holding.get("average_price", 0)

        if ts not in fund_orders:
            results[fund_name] = {
                "tradingsymbol": ts,
                "current_value": round(current_val, 2),
                "current_qty": current_qty,
                "current_nav": current_nav,
                "avg_price": avg_price,
                "simple_return_pct": round((current_nav - avg_price) / avg_price * 100, 2) if avg_price else 0,
                "xirr": None,
                "xirr_note": "No order history available"
            }
            continue

        # Build cashflows: (date, amount)
        # BUY = negative (outflow), SELL = positive (inflow)
        cashflows = []

        for order in fund_orders[ts]:
            txn_type = order.get("transaction_type", "").upper()
            amount = order.get("amount", 0)
            order_ts = order.get("order_timestamp", "")

            try:
                order_date = datetime.fromisoformat(order_ts.replace(" ", "T")).date()
            except Exception:
                continue

            if txn_type == "BUY":
                cashflows.append((order_date, -amount))
            elif txn_type == "SELL":
                cashflows.append((order_date, amount))

        # Add current value as final cashflow (positive = redemption value)
        if current_val > 0:
            cashflows.append((today, current_val))

        if len(cashflows) < 2:
            results[fund_name] = {
                "tradingsymbol": ts,
                "current_value": round(current_val, 2),
                "current_qty": current_qty,
                "current_nav": current_nav,
                "avg_price": avg_price,
                "simple_return_pct": round((current_nav - avg_price) / avg_price * 100, 2) if avg_price else 0,
                "xirr": None,
                "xirr_note": "Insufficient cashflows for XIRR"
            }
            continue

        # Compute XIRR using Newton-Raphson
        xirr = compute_xirr(cashflows)

        results[fund_name] = {
            "tradingsymbol": ts,
            "current_value": round(current_val, 2),
            "current_qty": current_qty,
            "current_nav": current_nav,
            "avg_price": avg_price,
            "simple_return_pct": round((current_nav - avg_price) / avg_price * 100, 2) if avg_price else 0,
            "xirr_pct": round(xirr * 100, 2) if xirr else None,
            "cashflows_count": len(cashflows)
        }

    # Portfolio-level XIRR
    all_cashflows = []
    for holding in holdings:
        ts = holding.get("tradingsymbol")
        if ts in fund_orders:
            for order in fund_orders[ts]:
                txn_type = order.get("transaction_type", "").upper()
                amount = order.get("amount", 0)
                order_ts = order.get("order_timestamp", "")
                try:
                    order_date = datetime.fromisoformat(order_ts.replace(" ", "T")).date()
                except Exception:
                    continue
                if txn_type == "BUY":
                    all_cashflows.append((order_date, -amount))
                elif txn_type == "SELL":
                    all_cashflows.append((order_date, amount))

    total_current_val = sum(h.get("quantity", 0) * h.get("last_price", 0) for h in holdings)
    if total_current_val > 0:
        all_cashflows.append((today, total_current_val))

    portfolio_xirr = compute_xirr(all_cashflows) if len(all_cashflows) >= 2 else None

    return {
        "funds": results,
        "portfolio_xirr_pct": round(portfolio_xirr * 100, 2) if portfolio_xirr else None,
        "total_current_value": round(total_current_val, 2),
        "as_of": today.isoformat()
    }


def compute_xirr(cashflows: list) -> float | None:
    """Compute XIRR using Newton-Raphson method.

    cashflows: list of (date, amount) tuples
    Returns annualized rate or None if fails.
    """
    if len(cashflows) < 2:
        return None

    # Convert dates to days from first cashflow
    dates = [cf[0] for cf in cashflows]
    amounts = [cf[1] for cf in cashflows]

    # Use first date as epoch
    epoch = min(dates)
    days = [(d - epoch).days for d in dates]

    # Initial guess: simple annualized return
    total_invested = sum(a for a in amounts if a < 0)
    total_returned = sum(a for a in amounts if a > 0)
    if total_invested == 0:
        return None
    years = max(days) / 365.25 if max(days) > 0 else 1
    guess = (total_returned / abs(total_invested)) ** (1/years) - 1 if years > 0 else 0.1
    guess = max(0.01, min(guess, 10.0))  # Clamp

    def npv(rate):
        """Net Present Value at given rate."""
        if rate <= -1:
            return float('inf')
        return sum(amounts[i] / (1 + rate) ** (days[i] / 365.25) for i in range(len(amounts)))

    def npv_derivative(rate):
        """Derivative of NPV."""
        if rate <= -1:
            return float('inf')
        return sum(-amounts[i] * (days[i] / 365.25) / (1 + rate) ** (days[i] / 365.25 + 1) for i in range(len(amounts)))

    # Newton-Raphson
    rate = guess
    for _ in range(100):
        try:
            f = npv(rate)
            f_prime = npv_derivative(rate)
            if f_prime == 0:
                break
            new_rate = rate - f / f_prime
            if abs(new_rate - rate) < 1e-8:
                rate = new_rate
                break
            rate = new_rate
        except Exception:
            break

    # Validate result
    if rate <= -0.99 or rate > 100 or rate != rate:  # Sanity check (NaN check)
        return None
    return rate


def main():
    parser = argparse.ArgumentParser(description="Kite Connect Bridge for Hermes")
    parser.add_argument("--profile", default="default", help="Profile name (default: default)")
    parser.add_argument("--list-profiles", action="store_true", help="List configured profiles")
    parser.add_argument("command", nargs="?", help="Command to run")

    args = parser.parse_args()

    if args.list_profiles:
        from kite_auth import list_profiles
        list_profiles()
        return

    if not args.command:
        parser.print_help()
        sys.exit(1)

    command = args.command
    cfg = load_config(args.profile)
    sys.exit(run_command(cfg, command))


if __name__ == "__main__":
    main()