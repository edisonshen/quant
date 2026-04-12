"""Generic HTTP API client with auth, rate limiting, and retries."""

from __future__ import annotations

import time
from typing import Any, Self

import httpx
import structlog

log = structlog.get_logger()


class ApiError(Exception):
    """Raised when an API request fails after retries."""

    def __init__(self, status_code: int, message: str, url: str = "") -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code}: {message} ({url})")


class ApiClient:
    """Generic HTTP API client with auth, rate limiting, and retries.

    Subclasses set base_url/headers and add domain-specific methods.
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        rate_limit_delay: float = 0.0,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers or {},
            timeout=timeout,
        )
        self._rate_limit_delay = rate_limit_delay
        self._max_retries = max_retries
        self._last_request_time: float = 0.0
        self._log = log.bind(client=self.__class__.__name__)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # -- Public convenience methods ------------------------------------------

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """GET request, returns parsed JSON."""
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict:
        """POST request, returns parsed JSON."""
        return self._request("POST", path, json=json)

    # -- Internal ------------------------------------------------------------

    def _throttle(self) -> None:
        """Enforce minimum delay between requests."""
        if self._rate_limit_delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            sleep_for = self._rate_limit_delay - elapsed
            self._log.debug("rate_limit_throttle", sleep_seconds=round(sleep_for, 2))
            time.sleep(sleep_for)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Send request with throttle, retry on 5xx, and 429 handling."""
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            self._throttle()
            self._last_request_time = time.monotonic()

            try:
                resp = self._client.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                last_exc = exc
                self._log.warning(
                    "request_error", attempt=attempt, path=path, error=str(exc),
                )
                time.sleep(2 ** attempt)
                continue

            # Rate limited — honour Retry-After or x-rate-limit-reset
            if resp.status_code == 429:
                retry_after = self._parse_retry_after(resp)
                self._log.warning(
                    "rate_limited", attempt=attempt, path=path, retry_after=retry_after,
                )
                time.sleep(retry_after)
                continue

            # Server error — retry with backoff
            if resp.status_code >= 500:
                self._log.warning(
                    "server_error", attempt=attempt, path=path, status=resp.status_code,
                )
                last_exc = ApiError(resp.status_code, resp.text, path)
                time.sleep(2 ** attempt)
                continue

            # Client error — don't retry
            if resp.status_code >= 400:
                raise ApiError(resp.status_code, resp.text, path)

            return resp.json()

        # Exhausted retries
        if last_exc:
            raise last_exc
        raise ApiError(0, "max retries exhausted", path)

    @staticmethod
    def _parse_retry_after(resp: httpx.Response) -> float:
        """Extract wait time from rate-limit headers."""
        # Standard Retry-After header (seconds)
        retry_after = resp.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

        # X/Twitter: x-rate-limit-reset (unix timestamp)
        reset_ts = resp.headers.get("x-rate-limit-reset")
        if reset_ts:
            try:
                wait = float(reset_ts) - time.time()
                return max(wait, 1.0)
            except ValueError:
                pass

        return 60.0  # conservative default
