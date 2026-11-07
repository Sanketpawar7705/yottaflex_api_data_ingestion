"""Validation of one source record. Pure functions: no database, no network."""
import math
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

REQUIRED_FIELDS = ("event_id", "customer_id", "amount", "currency", "status", "event_time", "updated_at")
STATUSES = {"pending", "completed", "cancelled"}
CURRENCY = re.compile(r"^[A-Z]{3}$")
MAX_FUTURE = timedelta(days=1)


class RejectError(ValueError):
    """Raised for a bad record. reason looks like 'category' or 'category:detail'."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def reject_category(reason):
    return reason.split(":", 1)[0]


def parse_timestamp(value, field):
    """ISO-8601 with timezone -> normalised UTC text 'YYYY-MM-DDTHH:MM:SSZ'."""
    if not isinstance(value, str):
        raise RejectError(f"invalid_timestamp:{field}")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise RejectError(f"invalid_timestamp:{field}")
    if parsed.tzinfo is None:
        raise RejectError(f"invalid_timestamp:{field}")      # timezone is mandatory
    if len(text) == 20 and text[-1] == "Z":
        return text                                          # already in canonical UTC form: skip strftime
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def amount_to_minor_units(value):
    """12.34 -> 1234. Must be a number, finite, >= 0, at most 2 decimals."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RejectError("invalid_amount:not_numeric")
    if isinstance(value, float) and not math.isfinite(value):
        raise RejectError("invalid_amount:not_finite")
    if value < 0:
        raise RejectError("invalid_amount:negative")
    try:
        exact = Decimal(str(value))
    except InvalidOperation:
        raise RejectError("invalid_amount:not_numeric")
    if exact.as_tuple().exponent < -2:
        raise RejectError("invalid_amount:too_many_decimals")
    return int(exact * 100)


def future_limit_for(now):
    """Latest updated_at we accept. Callers that validate many records compute this once."""
    return (now + MAX_FUTURE).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_event(record, customer_ids, now=None, future_limit=None):
    """Return (clean_row, unexpected_field_names) or raise RejectError.

    Check order matters (the data generator labels follow the same order):
    structure -> required fields -> event_id -> customer reference -> amount ->
    currency -> status -> timestamps -> not in the far future.
    """
    if not isinstance(record, dict):
        raise RejectError("malformed_record")
    for field in REQUIRED_FIELDS:
        if field not in record:
            raise RejectError(f"missing_field:{field}")
    event_id = record["event_id"]
    if not isinstance(event_id, str) or not event_id.strip():
        raise RejectError("invalid_event_id")
    if record["customer_id"] not in customer_ids:
        raise RejectError("invalid_customer_ref")
    amount_minor = amount_to_minor_units(record["amount"])
    currency = record["currency"]
    if not isinstance(currency, str) or not CURRENCY.match(currency):
        raise RejectError("invalid_currency")
    if record["status"] not in STATUSES:
        raise RejectError("invalid_status")
    event_time = parse_timestamp(record["event_time"], "event_time")
    updated_at = parse_timestamp(record["updated_at"], "updated_at")
    if future_limit is None and now is not None:
        future_limit = future_limit_for(now)
    if future_limit is not None and updated_at > future_limit:
        raise RejectError("future_timestamp:updated_at")
    row = {
        "event_id": event_id.strip(),
        "customer_id": record["customer_id"],
        "amount": amount_minor / 100,
        "amount_minor": amount_minor,
        "currency": currency,
        "status": record["status"],
        "event_time": event_time,
        "updated_at": updated_at,
    }
    unexpected = sorted(set(record) - set(REQUIRED_FIELDS))
    return row, unexpected
