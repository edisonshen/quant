"""Data types for X/Twitter API v2 responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TweetMetrics:
    """Public engagement metrics for a tweet."""

    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0


@dataclass(frozen=True, slots=True)
class Tweet:
    """A single tweet from the X API v2."""

    id: str  # snowflake ID as string (exceeds 2^53)
    text: str
    author_id: str
    author_username: str
    created_at: datetime
    metrics: TweetMetrics = field(default_factory=TweetMetrics)
    symbols_mentioned: list[str] = field(default_factory=list)  # from $CASHTAG entities
    urls: list[str] = field(default_factory=list)
    is_retweet: bool = False
    is_reply: bool = False
    referenced_tweet_id: str | None = None


@dataclass(frozen=True, slots=True)
class XUser:
    """An X/Twitter user profile."""

    id: str
    username: str
    name: str
    followers_count: int = 0
