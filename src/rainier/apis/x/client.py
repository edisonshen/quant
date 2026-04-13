"""X/Twitter API v2 client built on the generic ApiClient."""

from __future__ import annotations

from datetime import datetime

from rainier.apis.base import ApiClient
from rainier.apis.x.types import Tweet, TweetMetrics, XUser


class XClient(ApiClient):
    """X/Twitter API v2 client.

    Uses Bearer Token authentication (app-only).
    Free tier allows ~1 request per 15 seconds.
    """

    TWEET_FIELDS = "created_at,public_metrics,entities,referenced_tweets"
    USER_FIELDS = "id,name,username,public_metrics"

    def __init__(self, bearer_token: str, rate_limit_delay: float = 16.0) -> None:
        super().__init__(
            base_url="https://api.twitter.com/2",
            headers={"Authorization": f"Bearer {bearer_token}"},
            rate_limit_delay=rate_limit_delay,
        )

    # -- Public API methods --------------------------------------------------

    def get_tweet(self, tweet_id: str) -> Tweet:
        """Fetch a single tweet by ID."""
        data = self.get(
            f"/tweets/{tweet_id}",
            params={"tweet.fields": self.TWEET_FIELDS},
        )
        return self._parse_tweet(data["data"])

    def get_user_by_username(self, username: str) -> XUser:
        """Resolve a username to a user profile."""
        data = self.get(
            f"/users/by/username/{username}",
            params={"user.fields": self.USER_FIELDS},
        )
        return self._parse_user(data["data"])

    def get_user_tweets(
        self,
        user_id: str,
        *,
        max_results: int = 10,
        since_id: str | None = None,
    ) -> list[Tweet]:
        """Fetch recent tweets from a user's timeline.

        Args:
            user_id: The user's numeric ID.
            max_results: Number of tweets to return (5-100).
            since_id: Only return tweets newer than this ID (for incremental polling).
        """
        params: dict[str, str | int] = {
            "tweet.fields": self.TWEET_FIELDS,
            "max_results": max(5, min(max_results, 100)),
        }
        if since_id:
            params["since_id"] = since_id

        data = self.get(f"/users/{user_id}/tweets", params=params)

        # API returns {"meta": {"result_count": 0}} when no new tweets
        tweets_data = data.get("data", [])
        return [self._parse_tweet(t) for t in tweets_data]

    def search_recent(self, query: str, max_results: int = 10) -> list[Tweet]:
        """Search recent tweets (last 7 days).

        Useful for cashtag searches like '$AAPL' or '$TSLA'.
        """
        params: dict[str, str | int] = {
            "query": query,
            "tweet.fields": self.TWEET_FIELDS,
            "max_results": max(10, min(max_results, 100)),
        }
        data = self.get("/tweets/search/recent", params=params)
        tweets_data = data.get("data", [])
        return [self._parse_tweet(t) for t in tweets_data]

    # -- Parsing helpers -----------------------------------------------------

    @staticmethod
    def _parse_tweet(data: dict) -> Tweet:
        """Parse an X API v2 tweet object into our Tweet dataclass."""
        # Public metrics
        pm = data.get("public_metrics", {})
        metrics = TweetMetrics(
            retweet_count=pm.get("retweet_count", 0),
            reply_count=pm.get("reply_count", 0),
            like_count=pm.get("like_count", 0),
            quote_count=pm.get("quote_count", 0),
        )

        # Extract $CASHTAG symbols from entities
        entities = data.get("entities", {})
        cashtags = entities.get("cashtags", [])
        symbols = [ct["tag"].upper() for ct in cashtags]

        # Extract URLs
        url_entities = entities.get("urls", [])
        urls = [u.get("expanded_url", u.get("url", "")) for u in url_entities]

        # Referenced tweets (retweet / reply detection)
        refs = data.get("referenced_tweets") or []
        is_retweet = any(r.get("type") == "retweeted" for r in refs)
        is_reply = any(r.get("type") == "replied_to" for r in refs)
        ref_id = refs[0]["id"] if refs else None

        # Parse created_at (ISO 8601)
        created_at = datetime.fromisoformat(
            data["created_at"].replace("Z", "+00:00")
        )

        return Tweet(
            id=data["id"],
            text=data["text"],
            author_id=data.get("author_id", ""),
            author_username=data.get("author_username", ""),
            created_at=created_at,
            metrics=metrics,
            symbols_mentioned=symbols,
            urls=urls,
            is_retweet=is_retweet,
            is_reply=is_reply,
            referenced_tweet_id=ref_id,
        )

    @staticmethod
    def _parse_user(data: dict) -> XUser:
        """Parse an X API v2 user object into our XUser dataclass."""
        pm = data.get("public_metrics", {})
        return XUser(
            id=data["id"],
            username=data["username"],
            name=data["name"],
            followers_count=pm.get("followers_count", 0),
        )
