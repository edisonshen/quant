# Generic API Client Layer + X/Twitter Integration

## Context

We need a reusable API client infrastructure for Rainier. X/Twitter is the first integration, but the same pattern will serve Polygon, future broker APIs, news APIs, etc. The design prioritizes:
- **One generic base client** with auth, rate limiting, retry — reused across all API integrations
- **Centralized config** — all API credentials and settings in one `apis` section of settings.yaml
- **Quick setup** — get a working X client fast, built on the reusable base

## Module Structure

```
src/rainier/apis/
├── __init__.py          # Public exports
├── base.py              # ApiClient base class (httpx, auth, rate limit, retry)
├── x/
│   ├── __init__.py
│   ├── client.py        # XClient(ApiClient) — X API v2 endpoints
│   ├── types.py         # Tweet, TweetMetrics, XUser dataclasses
│   ├── store.py         # DB upsert (Tweet → TweetRecord)
│   ├── alerts.py        # Discord embeds for VIP tweets
│   └── poller.py        # Poll tracked accounts → store → alert
└── (future: polygon/, newsapi/, etc.)
```

## Implementation Steps

### Step 1: Generic ApiClient Base (`apis/base.py`)

Reusable base that any API client inherits from:

```python
class ApiClient:
    """Generic HTTP API client with auth, rate limiting, and retries."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        rate_limit_delay: float = 0.0,    # min seconds between requests
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers or {},
            timeout=timeout,
        )
        self._rate_limit_delay = rate_limit_delay
        self._max_retries = max_retries
        self._last_request_time: float = 0.0
        self._log = structlog.get_logger(client=self.__class__.__name__)

    def get(self, path: str, params: dict | None = None) -> dict: ...
    def post(self, path: str, json: dict | None = None) -> dict: ...
    def close(self) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *args) -> None: ...

    # Internal
    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Send request with throttle + retry + error handling."""
        # 1. Proactive rate limit (sleep if needed)
        # 2. Send request
        # 3. Handle 429 (read Retry-After / x-rate-limit-reset header)
        # 4. Retry on 5xx with exponential backoff
        # 5. Return parsed JSON
```

This gives every future API client: rate limiting, retries, structured logging, context manager.

### Step 2: Centralized Config (`core/config.py`)

Merge all API configs under one `apis` section:

```python
class XTrackedAccount(BaseModel):
    username: str
    label: str = ""
    vip: bool = False                    # triggers Discord alert

class XApiConfig(BaseModel):
    enabled: bool = False
    poll_interval_minutes: int = 15
    max_results_per_user: int = 10
    rate_limit_delay: float = 16.0       # X free tier: ~1 req/15s
    tracked_accounts: list[XTrackedAccount] = []

class ApisConfig(BaseModel):
    """All external API configurations in one place."""
    x: XApiConfig = XApiConfig()
    # Future: polygon, newsapi, alpaca, etc.
```

Add to Settings:
```python
x_api_bearer_token: str = ""     # secret from .env
apis: ApisConfig = ApisConfig()  # app config from YAML
```

In `settings.yaml`:
```yaml
apis:
  x:
    enabled: true
    poll_interval_minutes: 15
    tracked_accounts:
      - username: mingchikuo
        label: "Ming-Chi Kuo"
        vip: true
      - username: elonmusk
        label: "Elon Musk"
        vip: true
```

In `.env`:
```
X_API_BEARER_TOKEN=your_bearer_token
```

### Step 3: X Types (`apis/x/types.py`)

```python
@dataclass(frozen=True, slots=True)
class TweetMetrics:
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0

@dataclass(frozen=True, slots=True)
class Tweet:
    id: str                        # snowflake ID as string (>2^53)
    text: str
    author_id: str
    author_username: str
    created_at: datetime
    metrics: TweetMetrics
    symbols_mentioned: list[str]   # from $CASHTAG entities
    urls: list[str]
    is_retweet: bool
    is_reply: bool
    referenced_tweet_id: str | None = None

@dataclass(frozen=True, slots=True)
class XUser:
    id: str
    username: str
    name: str
    followers_count: int = 0
```

### Step 4: XClient (`apis/x/client.py`)

```python
class XClient(ApiClient):
    """X/Twitter API v2 client."""

    TWEET_FIELDS = "created_at,public_metrics,entities,referenced_tweets"
    USER_FIELDS = "id,name,username,public_metrics"

    def __init__(self, bearer_token: str, rate_limit_delay: float = 16.0):
        super().__init__(
            base_url="https://api.twitter.com/2",
            headers={"Authorization": f"Bearer {bearer_token}"},
            rate_limit_delay=rate_limit_delay,
        )

    def get_tweet(self, tweet_id: str) -> Tweet: ...
    def get_user_by_username(self, username: str) -> XUser: ...
    def get_user_tweets(self, user_id: str, *, max_results: int = 10, since_id: str | None = None) -> list[Tweet]: ...
    def search_recent(self, query: str, max_results: int = 10) -> list[Tweet]: ...
```

### Step 5: DB Model (add to `core/models.py`)

```python
class TweetRecord(Base):
    __tablename__ = "tweets"
    __table_args__ = (
        PrimaryKeyConstraint("id", "created_at"),
        Index("ix_tweets_author", "author_username"),
        Index("ix_tweets_symbols", "symbols_mentioned", postgresql_using="gin"),
    )
    id: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[str] = mapped_column(String(30))
    author_username: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)
    symbols_mentioned: Mapped[list[str] | None] = mapped_column(ARRAY(String(10)))
    retweet_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    quote_count: Mapped[int] = mapped_column(Integer, default=0)
    is_retweet: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    sentiment: Mapped[float | None] = mapped_column(Float)
    trading_relevance: Mapped[float | None] = mapped_column(Float)
```

Add `"tweets": "created_at"` to HYPERTABLES.

### Step 6: Store + Alerts + Poller (`apis/x/store.py`, `alerts.py`, `poller.py`)

- **store.py**: Upsert Tweet → TweetRecord, dedup by tweet ID
- **alerts.py**: `send_vip_tweet_alert(tweet, label, config)` — Discord embed with tweet text, symbols, engagement, link
- **poller.py**: `poll_tracked_accounts(settings)` — for each account: get since_id from DB → fetch new → store → alert VIPs

### Step 7: CLI Commands (`cli.py`)

```
rainier x fetch <tweet_id>          # fetch + display single tweet
rainier x poll                      # one-shot poll all tracked accounts
rainier x poll --dry-run            # fetch without storing/alerting
rainier x track                     # show tracked accounts + last tweet time
```

### Step 8: Scheduler (`scheduler/service.py`)

Add X poll job in `build_scheduler()`:
```python
if settings.apis.x.enabled and settings.x_api_bearer_token:
    scheduler.add_job(run_x_poll, CronTrigger(
        day_of_week="mon-fri", hour="6-17",
        minute=f"*/{settings.apis.x.poll_interval_minutes}",
    ), id="x_api_poll")
```

## Files to Modify

| File | Change |
|------|--------|
| `src/rainier/core/config.py` | Add `ApisConfig`, `XApiConfig`, `XTrackedAccount`; add `apis` to Settings + `load_settings()` |
| `src/rainier/core/models.py` | Add `TweetRecord` + HYPERTABLES entry |
| `src/rainier/cli.py` | Add `x` command group |
| `src/rainier/scheduler/service.py` | Add `run_x_poll()` job |
| `config/settings.yaml` | Add `apis.x` section |

## New Files

| File | Purpose |
|------|---------|
| `src/rainier/apis/__init__.py` | Exports ApiClient |
| `src/rainier/apis/base.py` | Generic ApiClient (httpx, rate limit, retry) |
| `src/rainier/apis/x/__init__.py` | Exports XClient, Tweet |
| `src/rainier/apis/x/types.py` | Tweet, TweetMetrics, XUser dataclasses |
| `src/rainier/apis/x/client.py` | XClient(ApiClient) — X API v2 |
| `src/rainier/apis/x/store.py` | DB upsert logic |
| `src/rainier/apis/x/alerts.py` | Discord VIP tweet alerts |
| `src/rainier/apis/x/poller.py` | Poll orchestration |
| `tests/test_x_client.py` | Unit tests (mocked httpx) |

## Verification

1. `uv run pytest tests/test_x_client.py -v` — mock API responses, test parsing
2. `uv run rainier x fetch 2043237287644070186` — fetch Ming-Chi Kuo's tweet (needs bearer token in .env)
3. `uv run rainier x poll --dry-run` — test polling without persistence
4. `uv run rainier x poll` — full poll with DB + Discord
5. `uv run ruff check src/rainier/apis/`
