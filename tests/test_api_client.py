"""Tests for the generic ApiClient base class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from rainier.apis.base import ApiClient, ApiError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_response():
    """Factory for mock httpx.Response objects."""
    def _make(status_code: int = 200, json_data: dict | None = None, headers: dict | None = None):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = str(json_data or {})
        resp.headers = headers or {}
        return resp
    return _make


@pytest.fixture
def client():
    """ApiClient with rate limiting disabled for fast tests."""
    c = ApiClient(
        base_url="https://api.example.com",
        headers={"Authorization": "Bearer test"},
        rate_limit_delay=0.0,
        max_retries=3,
    )
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApiClientInit:
    def test_context_manager(self):
        with ApiClient(base_url="https://example.com") as client:
            assert client is not None

    def test_default_params(self):
        client = ApiClient(base_url="https://example.com")
        assert client._rate_limit_delay == 0.0
        assert client._max_retries == 3
        client.close()


class TestSuccessfulRequests:
    def test_get_returns_json(self, client, mock_response):
        expected = {"data": {"id": "123", "text": "hello"}}
        with patch.object(client._client, "request", return_value=mock_response(200, expected)):
            result = client.get("/tweets/123")
        assert result == expected

    def test_post_returns_json(self, client, mock_response):
        expected = {"ok": True}
        with patch.object(client._client, "request", return_value=mock_response(200, expected)):
            result = client.post("/endpoint", json={"key": "value"})
        assert result == expected

    def test_get_with_params(self, client, mock_response):
        expected = {"data": []}
        resp = mock_response(200, expected)
        with patch.object(client._client, "request", return_value=resp) as mock_req:
            client.get("/search", params={"q": "test"})
            mock_req.assert_called_once_with("GET", "/search", params={"q": "test"})


class TestClientErrors:
    def test_4xx_raises_api_error(self, client, mock_response):
        with patch.object(
            client._client, "request",
            return_value=mock_response(401, {"error": "unauthorized"}),
        ):
            with pytest.raises(ApiError) as exc_info:
                client.get("/protected")
            assert exc_info.value.status_code == 401

    def test_404_raises_api_error(self, client, mock_response):
        with patch.object(
            client._client, "request",
            return_value=mock_response(404, {"error": "not found"}),
        ):
            with pytest.raises(ApiError) as exc_info:
                client.get("/missing")
            assert exc_info.value.status_code == 404

    def test_4xx_no_retry(self, client, mock_response):
        """Client errors should fail immediately, not retry."""
        with patch.object(
            client._client, "request",
            return_value=mock_response(403, {"error": "forbidden"}),
        ) as mock_req:
            with pytest.raises(ApiError):
                client.get("/forbidden")
            assert mock_req.call_count == 1


class TestRetries:
    @patch("rainier.apis.base.time.sleep")
    def test_5xx_retries_then_raises(self, mock_sleep, client, mock_response):
        with patch.object(
            client._client, "request",
            return_value=mock_response(500, {"error": "server error"}),
        ) as mock_req:
            with pytest.raises(ApiError) as exc_info:
                client.get("/flaky")
            assert exc_info.value.status_code == 500
            assert mock_req.call_count == 3

    @patch("rainier.apis.base.time.sleep")
    def test_5xx_recovers_on_second_attempt(self, mock_sleep, client, mock_response):
        fail = mock_response(503, {"error": "unavailable"})
        success = mock_response(200, {"data": "ok"})
        with patch.object(client._client, "request", side_effect=[fail, success]) as mock_req:
            result = client.get("/flaky")
        assert result == {"data": "ok"}
        assert mock_req.call_count == 2

    @patch("rainier.apis.base.time.sleep")
    def test_connection_error_retries(self, mock_sleep, client):
        with patch.object(
            client._client, "request",
            side_effect=httpx.ConnectError("connection refused"),
        ) as mock_req:
            with pytest.raises(httpx.ConnectError):
                client.get("/down")
            assert mock_req.call_count == 3


class TestRateLimiting:
    @patch("rainier.apis.base.time.sleep")
    def test_429_retries_with_retry_after(self, mock_sleep, client, mock_response):
        rate_limited = mock_response(429, {}, headers={"retry-after": "5"})
        success = mock_response(200, {"data": "ok"})
        with patch.object(client._client, "request", side_effect=[rate_limited, success]):
            result = client.get("/rate-limited")
        assert result == {"data": "ok"}
        # Should have slept for 5 seconds (from Retry-After header)
        mock_sleep.assert_any_call(5.0)

    @patch("rainier.apis.base.time.sleep")
    def test_429_default_wait_when_no_header(self, mock_sleep, client, mock_response):
        rate_limited = mock_response(429, {}, headers={})
        success = mock_response(200, {"data": "ok"})
        with patch.object(client._client, "request", side_effect=[rate_limited, success]):
            result = client.get("/rate-limited")
        assert result == {"data": "ok"}
        mock_sleep.assert_any_call(60.0)

    @patch("rainier.apis.base.time.sleep")
    def test_throttle_enforces_delay(self, mock_sleep, mock_response):
        """Client with rate_limit_delay should sleep between requests."""
        client = ApiClient(
            base_url="https://example.com",
            rate_limit_delay=16.0,
        )
        # Make first request (no throttle — _last_request_time is 0 in the past)
        success = mock_response(200, {"ok": True})
        with patch.object(client._client, "request", return_value=success):
            client.get("/first")
            # Second request immediately after — should trigger throttle
            client.get("/second")

        # At least one sleep call should have been made for throttling
        assert mock_sleep.call_count >= 1
        # The sleep duration should be close to rate_limit_delay
        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert any(s > 10.0 for s in sleep_args), f"Expected throttle sleep >10s, got {sleep_args}"
        client.close()


class TestParseRetryAfter:
    def test_retry_after_header(self):
        resp = MagicMock()
        resp.headers = {"retry-after": "30"}
        assert ApiClient._parse_retry_after(resp) == 30.0

    def test_x_rate_limit_reset_header(self):
        import time as _time
        future_ts = str(_time.time() + 120)
        resp = MagicMock()
        resp.headers = {"x-rate-limit-reset": future_ts}
        wait = ApiClient._parse_retry_after(resp)
        assert 118.0 <= wait <= 122.0  # ~120 seconds

    def test_no_headers_returns_default(self):
        resp = MagicMock()
        resp.headers = {}
        assert ApiClient._parse_retry_after(resp) == 60.0
