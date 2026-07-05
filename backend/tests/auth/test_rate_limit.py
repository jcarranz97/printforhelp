"""Tests for per-IP rate limiting on the auth endpoints."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.ratelimit import limiter

FORGOT = "/api/v1/auth/forgot-password"


@pytest.fixture
def rate_limit_on() -> Iterator[None]:
    """Turn the limiter on with a clean counter, then off again after."""
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


class TestRateLimit:
    def test_forgot_password_is_throttled(
        self, client: TestClient, rate_limit_on: None
    ):
        # FORGOT_PASSWORD_LIMIT is 5/minute; the 6th hit from the same IP
        # is throttled with the standard envelope.
        responses = [
            client.post(FORGOT, json={"email": "spam@example.com"}) for _ in range(6)
        ]
        assert [r.status_code for r in responses[:5]] == [200, 200, 200, 200, 200]
        assert responses[5].status_code == 429
        assert responses[5].json()["error"]["code"] == "RATE_LIMITED"

    def test_requests_under_the_limit_pass(
        self, client: TestClient, rate_limit_on: None
    ):
        for _ in range(3):
            resp = client.post(FORGOT, json={"email": "ok@example.com"})
            assert resp.status_code == 200
