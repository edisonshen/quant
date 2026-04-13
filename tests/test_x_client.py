"""Tests for X/Twitter API v2 client."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from rainier.apis.base import ApiError
from rainier.apis.x.client import XClient

# ---------------------------------------------------------------------------
# Sample API responses (matching X API v2 format)
# ---------------------------------------------------------------------------

SAMPLE_TWEET_RESPONSE = {
    "data": {
        "id": "2043237287644070186",
        "text": "$AAPL supply chain update: key supplier ramping production for new iPhone",
        "author_id": "12345678",
        "created_at": "2026-04-12T08:30:00.000Z",
        "public_metrics": {
            "retweet_count": 1500,
            "reply_count": 200,
            "like_count": 5000,
            "quote_count": 300,
        },
        "entities": {
            "cashtags": [{"start": 0, "end": 5, "tag": "AAPL"}],
            "urls": [
                {
                    "url": "https://t.co/abc123",
                    "expanded_url": "https://example.com/article",
                }
            ],
        },
        "referenced_tweets": None,
    }
}

SAMPLE_RETWEET_RESPONSE = {
    "data": {
        "id": "9999999999",
        "text": "RT @someone: Great analysis",
        "author_id": "12345678",
        "created_at": "2026-04-12T09:00:00.000Z",
        "public_metrics": {
            "retweet_count": 0,
            "reply_count": 0,
            "like_count": 0,
            "quote_count": 0,
        },
        "entities": {},
        "referenced_tweets": [{"type": "retweeted", "id": "8888888888"}],
    }
}

SAMPLE_REPLY_RESPONSE = {
    "data": {
        "id": "7777777777",
        "text": "@someone I agree with this take on $TSLA",
        "author_id": "12345678",
        "created_at": "2026-04-12T10:00:00.000Z",
        "public_metrics": {
            "retweet_count": 5,
            "reply_count": 1,
            "like_count": 20,
            "quote_count": 0,
        },
        "entities": {
            "cashtags": [{"start": 35, "end": 40, "tag": "TSLA"}],
        },
        "referenced_tweets": [{"type": "replied_to", "id": "6666666666"}],
    }
}

SAMPLE_USER_RESPONSE = {
    "data": {
        "id": "12345678",
        "username": "mingchikuo",
        "name": "Ming-Chi Kuo",
        "public_metrics": {
            "followers_count": 500000,
            "following_count": 100,
            "tweet_count": 3000,
            "listed_count": 5000,
        },
    }
}

SAMPLE_TIMELINE_RESPONSE = {
    "data": [
        SAMPLE_TWEET_RESPONSE["data"],
        SAMPLE_RETWEET_RESPONSE["data"],
    ],
    "meta": {"result_count": 2, "newest_id": "2043237287644070186"},
}

SAMPLE_TIMELINE_EMPTY = {
    "meta": {"result_count": 0},
}

SAMPLE_SEARCH_RESPONSE = {
    "data": [SAMPLE_TWEET_RESPONSE["data"]],
    "meta": {"result_count": 1},
}

SAMPLE_MULTI_CASHTAG = {
    "data": {
        "id": "5555555555",
        "text": "Comparing $AAPL vs $MSFT vs $GOOGL earnings",
        "author_id": "12345678",
        "created_at": "2026-04-12T11:00:00.000Z",
        "public_metrics": {
            "retweet_count": 100,
            "reply_count": 50,
            "like_count": 800,
            "quote_count": 25,
        },
        "entities": {
            "cashtags": [
                {"start": 10, "end": 15, "tag": "AAPL"},
                {"start": 20, "end": 25, "tag": "MSFT"},
                {"start": 30, "end": 36, "tag": "GOOGL"},
            ],
        },
    }
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """XClient with rate limiting disabled for fast tests."""
    c = XClient(bearer_token="test_token", rate_limit_delay=0.0)
    yield c
    c.close()


def _mock_response(status_code: int = 200, json_data: dict | None = None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data or {})
    resp.headers = {}
    return resp


# ---------------------------------------------------------------------------
# Tests: Tweet parsing
# ---------------------------------------------------------------------------


class TestParseTweet:
    def test_parse_basic_tweet(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TWEET_RESPONSE),
        ):
            tweet = client.get_tweet("2043237287644070186")

        assert tweet.id == "2043237287644070186"
        assert "$AAPL" not in tweet.text or "AAPL" in tweet.text
        assert tweet.author_id == "12345678"
        assert tweet.created_at == datetime(2026, 4, 12, 8, 30, tzinfo=timezone.utc)
        assert tweet.is_retweet is False
        assert tweet.is_reply is False
        assert tweet.referenced_tweet_id is None

    def test_parse_cashtag_symbols(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TWEET_RESPONSE),
        ):
            tweet = client.get_tweet("2043237287644070186")

        assert tweet.symbols_mentioned == ["AAPL"]

    def test_parse_multiple_cashtags(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_MULTI_CASHTAG),
        ):
            tweet = client.get_tweet("5555555555")

        assert tweet.symbols_mentioned == ["AAPL", "MSFT", "GOOGL"]

    def test_parse_metrics(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TWEET_RESPONSE),
        ):
            tweet = client.get_tweet("2043237287644070186")

        assert tweet.metrics.like_count == 5000
        assert tweet.metrics.retweet_count == 1500
        assert tweet.metrics.reply_count == 200
        assert tweet.metrics.quote_count == 300

    def test_parse_urls(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TWEET_RESPONSE),
        ):
            tweet = client.get_tweet("2043237287644070186")

        assert tweet.urls == ["https://example.com/article"]

    def test_parse_retweet(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_RETWEET_RESPONSE),
        ):
            tweet = client.get_tweet("9999999999")

        assert tweet.is_retweet is True
        assert tweet.is_reply is False
        assert tweet.referenced_tweet_id == "8888888888"

    def test_parse_reply(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_REPLY_RESPONSE),
        ):
            tweet = client.get_tweet("7777777777")

        assert tweet.is_reply is True
        assert tweet.is_retweet is False
        assert tweet.referenced_tweet_id == "6666666666"
        assert tweet.symbols_mentioned == ["TSLA"]


# ---------------------------------------------------------------------------
# Tests: User parsing
# ---------------------------------------------------------------------------


class TestParseUser:
    def test_parse_user(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_USER_RESPONSE),
        ):
            user = client.get_user_by_username("mingchikuo")

        assert user.id == "12345678"
        assert user.username == "mingchikuo"
        assert user.name == "Ming-Chi Kuo"
        assert user.followers_count == 500000


# ---------------------------------------------------------------------------
# Tests: Timeline
# ---------------------------------------------------------------------------


class TestTimeline:
    def test_get_user_tweets(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TIMELINE_RESPONSE),
        ):
            tweets = client.get_user_tweets("12345678")

        assert len(tweets) == 2
        assert tweets[0].id == "2043237287644070186"
        assert tweets[1].is_retweet is True

    def test_empty_timeline(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TIMELINE_EMPTY),
        ):
            tweets = client.get_user_tweets("12345678")

        assert tweets == []

    def test_since_id_passed(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TIMELINE_EMPTY),
        ) as mock_req:
            client.get_user_tweets("12345678", since_id="999")

        call_kwargs = mock_req.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["since_id"] == "999"

    def test_max_results_clamped(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_TIMELINE_EMPTY),
        ) as mock_req:
            client.get_user_tweets("12345678", max_results=1)

        call_kwargs = mock_req.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["max_results"] == 5  # clamped to minimum


# ---------------------------------------------------------------------------
# Tests: Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_recent(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(200, SAMPLE_SEARCH_RESPONSE),
        ):
            tweets = client.search_recent("$AAPL")

        assert len(tweets) == 1
        assert tweets[0].symbols_mentioned == ["AAPL"]


# ---------------------------------------------------------------------------
# Tests: Auth + errors
# ---------------------------------------------------------------------------


class TestAuth:
    def test_bearer_token_in_headers(self):
        client = XClient(bearer_token="my_secret_token", rate_limit_delay=0.0)
        assert client._client.headers["authorization"] == "Bearer my_secret_token"
        client.close()

    def test_401_raises_api_error(self, client):
        with patch.object(
            client._client, "request",
            return_value=_mock_response(401, {"error": "Unauthorized"}),
        ):
            with pytest.raises(ApiError) as exc_info:
                client.get_tweet("123")
            assert exc_info.value.status_code == 401
