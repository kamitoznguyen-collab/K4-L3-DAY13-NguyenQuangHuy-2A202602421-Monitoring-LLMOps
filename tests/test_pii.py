from app.logging_config import scrub_event
from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    out = scrub_text("CCCD của tôi là 001099012345")
    assert "001099012345" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card_formats_as_card_not_phone_or_cccd() -> None:
    for card in ("4111 1111 1111 1111", "4111-1111-1111-1111", "4111111111111111"):
        out = scrub_text(f"card {card} please")
        assert card not in out
        assert out == "card [REDACTED_CREDIT_CARD] please"


def test_scrub_passport() -> None:
    out = scrub_text("Passport B1234567 hết hạn")
    assert "B1234567" not in out
    assert "REDACTED_PASSPORT" in out


def test_plain_text_is_unchanged() -> None:
    text = "Explain why metrics traces and logs work together"
    assert scrub_text(text) == text


def test_scrub_event_scrubs_nested_fields_but_keeps_system_ids() -> None:
    event = scrub_event(
        None,
        "info",
        {
            "event": "request_failed",
            "correlation_id": "req-12345678",
            "user_id_hash": "123456789012",
            "payload": {"detail": {"items": ["mail a@b.co", "call 0987654321"]}},
        },
    )
    assert event["correlation_id"] == "req-12345678"
    assert event["user_id_hash"] == "123456789012"
    assert event["payload"]["detail"]["items"] == [
        "mail [REDACTED_EMAIL]",
        "call [REDACTED_PHONE_VN]",
    ]
