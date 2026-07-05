"""Tests for the small SMTP email helper."""

from email.message import EmailMessage
from typing import Self

import pytest

from app.auth import email as email_mod
from app.config import settings


class _FakeSMTP:
    """Stand-in for ``smtplib.SMTP`` that records what it was asked to do."""

    last: "_FakeSMTP | None" = None

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.tls = False
        self.login_args: tuple[str, str] | None = None
        self.sent: EmailMessage | None = None
        _FakeSMTP.last = self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def starttls(self) -> None:
        self.tls = True

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.sent = message


def test_send_email_skips_when_smtp_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "")

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("SMTP should not be contacted")

    monkeypatch.setattr(email_mod.smtplib, "SMTP", _boom)
    # Does not raise; it just logs and returns.
    email_mod.send_email("a@b.com", "hi", "body")


def test_send_email_with_tls_and_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "pass")
    monkeypatch.setattr(email_mod.smtplib, "SMTP", _FakeSMTP)

    email_mod.send_email("to@example.com", "Subject", "Body")

    smtp = _FakeSMTP.last
    assert smtp is not None
    assert smtp.tls is True
    assert smtp.login_args == ("user", "pass")
    assert smtp.sent is not None
    assert smtp.sent["To"] == "to@example.com"
    assert smtp.sent["Subject"] == "Subject"


def test_send_email_with_implicit_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USE_SSL", True)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "pass")
    monkeypatch.setattr(email_mod.smtplib, "SMTP_SSL", _FakeSMTP)

    email_mod.send_email("to@example.com", "Subject", "Body")

    smtp = _FakeSMTP.last
    assert smtp is not None
    # Implicit SSL never issues STARTTLS.
    assert smtp.tls is False
    assert smtp.login_args == ("user", "pass")
    assert smtp.sent is not None


def test_send_email_without_tls_or_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(email_mod.smtplib, "SMTP", _FakeSMTP)

    email_mod.send_email("to@example.com", "Subject", "Body")

    smtp = _FakeSMTP.last
    assert smtp is not None
    assert smtp.tls is False
    assert smtp.login_args is None
    assert smtp.sent is not None


def test_send_password_reset_email_builds_a_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        email_mod,
        "send_email",
        lambda to, subject, body: captured.update(to=to, subject=subject, body=body),
    )
    email_mod.send_password_reset_email("u@example.com", "https://x/reset?token=abc")
    assert captured["to"] == "u@example.com"
    assert "https://x/reset?token=abc" in captured["body"]
