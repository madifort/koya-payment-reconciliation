#!/usr/bin/env python3
"""Reconcile payment events using the latest attempt per transaction."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent


def parse_timestamp(value):
    """Convert an ISO 8601 timestamp into a UTC datetime."""
    if isinstance(value, str):
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    raise ValueError("Invalid timestamp")


def reconcile_payments():
    latest_transactions = {}

    with (BASE_DIR / "payments.jsonl").open(
        "r", encoding="utf-8"
    ) as file:

        for line in file:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(event, dict):
                continue

            txn_id = event.get("txn_id")

            if not txn_id:
                continue

            timestamp = parse_timestamp(event["ts"])

            if (
                txn_id not in latest_transactions
                or timestamp > latest_transactions[txn_id]["timestamp"]
            ):
                latest_transactions[txn_id] = {
                    "timestamp": timestamp,
                    "event": event,
                }

    total = Decimal("0")
    count = 0

    for transaction in latest_transactions.values():
        event = transaction["event"]

        if event["status"] == "success":
            try:
                amount = Decimal(str(event["amount"]))
            except (InvalidOperation, ValueError, TypeError):
                raise ValueError(
                    f"Invalid amount for transaction {event['txn_id']}"
                )

            total += amount
            count += 1

    return count, total


def main():
    count, total = reconcile_payments()

    with (BASE_DIR / "expected.txt").open(
        "r", encoding="utf-8"
    ) as file:
        expected = int(file.read().strip())

    if count != expected:
        print(
            f"Check failed: counted {count} successful payments, "
            f"expected {expected}."
        )
        return

    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")


if __name__ == "__main__":
    main()
