from datetime import datetime, timezone

import pytest

from app.validation import RejectError, reject_category, validate_event

CUSTOMERS = {"CUST-0001"}
NOW = datetime(2026, 11, 7, tzinfo=timezone.utc)
BASE = {"event_id": "E1", "customer_id": "CUST-0001", "amount": 12.3, "currency": "INR",
        "status": "completed", "event_time": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:01:00Z"}


def reason_for(**changes):
    record = {**BASE, **changes}
    with pytest.raises(RejectError) as caught:
        validate_event(record, CUSTOMERS, NOW)
    return caught.value.reason


def test_valid_record_is_normalised():
    row, unexpected = validate_event({**BASE, "updated_at": "2026-01-01T05:31:00+05:30"}, CUSTOMERS, NOW)
    assert row["amount_minor"] == 1230 and row["amount"] == 12.3
    assert row["updated_at"] == "2026-01-01T00:01:00Z"          # converted to UTC
    assert unexpected == []


@pytest.mark.parametrize("changes,expected", [
    ({"amount": None}, "invalid_amount:not_numeric"),
    ({"amount": "12.3"}, "invalid_amount:not_numeric"),
    ({"amount": True}, "invalid_amount:not_numeric"),
    ({"amount": -1}, "invalid_amount:negative"),
    ({"amount": 1.234}, "invalid_amount:too_many_decimals"),
    ({"customer_id": "BAD"}, "invalid_customer_ref"),
    ({"customer_id": None}, "invalid_customer_ref"),
    ({"status": "bad"}, "invalid_status"),
    ({"currency": "inr"}, "invalid_currency"),
    ({"event_id": "  "}, "invalid_event_id"),
    ({"event_time": "bad"}, "invalid_timestamp:event_time"),
    ({"updated_at": "2026-01-01T00:00:00"}, "invalid_timestamp:updated_at"),     # no timezone
    ({"updated_at": "2099-01-01T00:00:00Z"}, "future_timestamp:updated_at"),
])
def test_invalid_records(changes, expected):
    assert reason_for(**changes) == expected


@pytest.mark.parametrize("bad", ["text", None, 5, [1, 2]])
def test_non_object_is_malformed(bad):
    with pytest.raises(RejectError) as caught:
        validate_event(bad, CUSTOMERS, NOW)
    assert caught.value.reason == "malformed_record"


def test_missing_required_field():
    record = dict(BASE)
    del record["currency"]
    with pytest.raises(RejectError) as caught:
        validate_event(record, CUSTOMERS, NOW)
    assert caught.value.reason == "missing_field:currency"
    assert reject_category(caught.value.reason) == "missing_field"


def test_boundary_amounts_are_accepted():
    for amount, minor in [(0, 0), (0.0, 0), (0.01, 1), (99999.99, 9999999)]:
        assert validate_event({**BASE, "amount": amount}, CUSTOMERS, NOW)[0]["amount_minor"] == minor


def test_extra_field_is_tolerated_and_reported():
    row, unexpected = validate_event({**BASE, "promo": "x"}, CUSTOMERS, NOW)
    assert unexpected == ["promo"] and row["event_id"] == "E1"
