# Strategy Ideas & Hypotheses

Collecting ideas for backtesting and strategy improvement. Each idea includes the hypothesis, how to test it, and status.

---

## 1. SPY Monthly RSI Regime Filter

**Source:** Twitter/X observation (2026-03-26)

**Hypothesis:** When SPY monthly RSI hits 75+, the following month tends to be red (-5% to -11% historically). Trading long patterns during overbought regimes may underperform.

**Historical precedent:** Last 3 times SPY monthly RSI hit 75+, next month returned -5%, -11%, -5%.

**Implementation ideas:**
- Add SPY monthly RSI check to the screener
- When RSI > 70: flag as "overbought regime" — reduce position size or skip trend-continuation patterns (Bull Flag)
- When RSI > 75: consider pausing all long entries or switching to defensive mode
- Reversal patterns (False Breakdown, False Breakdown W Bottom) may actually benefit from pullbacks — test separately

**Backtest plan:**
- [ ] Compute SPY monthly RSI for the full backtest period
- [ ] Split pattern backtest results by regime (RSI > 70 vs RSI < 70)
- [ ] Compare win rate and avg return per pattern in each regime
- [ ] Test position sizing rules: full size when RSI < 70, half size when RSI 70-75, skip when RSI > 75

**Status:** Idea — needs backtest

---

## 2. Drop Bull Flag from Pattern Filter

**Source:** Backtest results (2026-03-26)

**Hypothesis:** Bull Flag underperforms the other two patterns. Dropping it would improve overall strategy performance.

**Evidence from backtest:**
- Bull Flag: 39% win rate, -0.16% avg return (Top 5 run)
- False Breakdown: 52.6% win rate, +1.41% avg return
- False Breakdown W Bottom: 84.6% win rate, +8.56% avg return

**Backtest plan:**
- [ ] Re-run pattern backtest with only False Breakdown + False Breakdown W Bottom
- [ ] Compare Sharpe, win rate, drawdown vs 3-pattern version

**Status:** Idea — needs backtest

---

## 3. Multi-Day Consecutive "Long In" Streak Boost

**Source:** Observation (2026-03-26) — stocks appearing in QU100 "Long in" multiple consecutive days show persistent institutional money flow

**Hypothesis:** A stock showing up in "Long in" for 3+ consecutive days has stronger conviction than a one-day appearance. If it also matches a pattern (FB, FBW, Bull Flag), that's the highest confidence setup.

**Signal tiers:**
- Streak only (no pattern): highlight as "strong money flow" — worth watching
- Streak + pattern match: highest conviction — prioritize for trading
- Pattern only (no streak): current strategy, already proven
- No streak, no pattern: skip

**Implementation ideas:**
- For each stock on each day, count consecutive prior days it appeared in "Long in"
- Streak >= 3 days: flag as "persistent flow"
- Add streak count as a feature in the screener composite score
- In Discord alerts: highlight streak stocks with a special indicator (e.g. "3d streak")

**Backtest plan:**
- [ ] Compute streak length for every (symbol, date) in QU100 history
- [ ] Compare avg return for streak >= 3 vs streak == 1 (all patterns)
- [ ] Test streak + pattern combo vs pattern-only
- [ ] Test streak-only (no pattern) as a standalone signal
- [ ] Find optimal streak threshold (2, 3, 5 days)

**Status:** Idea — needs backtest

---

## 4. Combine Pattern Filter with Money Flow Rank

**Source:** Both signals exist independently, never tested together

**Hypothesis:** Stocks that are BOTH top-ranked in money flow AND have a qualifying pattern should outperform either signal alone.

**Backtest plan:**
- [ ] Filter: rank 1-20 AND pattern match (FBW or FB)
- [ ] Compare vs pattern-only and rank-only strategies

**Status:** Idea — needs backtest

---

## 5. Stop-Loss / Trailing Stop on Pattern Trades

**Source:** Current backtest uses fixed 5-day hold with no stop-loss

**Hypothesis:** Adding a stop-loss (e.g. pattern's SL level) or trailing stop could reduce max drawdown without hurting win rate much.

**Backtest plan:**
- [ ] Test fixed stop-loss at pattern's SL level
- [ ] Test trailing stop (e.g. 2x ATR from high)
- [ ] Compare drawdown and risk-adjusted returns

**Status:** Idea — needs backtest

---

## 6. Hold Period Optimization per Pattern

**Source:** Current backtest uses fixed 5-day hold for all patterns

**Hypothesis:** Different patterns may have different optimal hold periods. False Breakdown W Bottom (reversal) might benefit from longer holds; False Breakdown (quick reversal) might be better with shorter holds.

**Backtest plan:**
- [ ] Run per-pattern sweep across hold periods (3, 5, 7, 10, 15, 20 days)
- [ ] Find optimal hold per pattern type

**Status:** Idea — needs backtest

---

## 7. Sector Rotation Filter

**Source:** QU100 already has sector data

**Hypothesis:** Pattern signals in trending sectors outperform those in declining sectors.

**Backtest plan:**
- [ ] Split pattern backtest by sector trend (bullish vs bearish sectors)
- [ ] Test sector-weighted position sizing

**Status:** Idea — needs backtest

---

## 8. Multi-Timeframe Pattern Detection for QU100

**Source:** DELL analysis (2026-03-26) — massive FBW pattern spanning ~11 months invisible to daily detector due to `max_pattern_bars=120` cap

**Hypothesis:** Patterns on higher timeframes (weekly, monthly) capture larger moves with higher conviction. Daily is the lowest timeframe for QU100 stocks. Weekly/monthly patterns that align with daily signals = highest confidence.

**DELL example:**
- Daily detector: found FBW at $104 (small pattern, conf=0.73)
- Weekly view: clear FBW from $174 → $65 → $175 over 11 months — the real trade
- Daily detector missed the big one because `max_pattern_bars=120` cuts off longer patterns

**Timeframes for QU100:**
- **Daily** (current) — swing trades, 3-10 day holds
- **Weekly** — position trades, 2-8 week holds, catches patterns spanning 3-12 months
- **Monthly** — macro setups, trend direction, highest conviction but slowest

**Implementation:**
- Resample daily OHLCV to weekly/monthly bars before pattern detection
- Run same Caisen pattern detectors on each timeframe
- Score: daily pattern alone < weekly pattern alone < daily + weekly aligned
- In Discord alerts: show which timeframes confirm (e.g. "D+W" = daily and weekly)

**Backtest plan:**
- [ ] Resample daily data to weekly bars for all QU100 symbols
- [ ] Run pattern detection on weekly bars
- [ ] Compare weekly pattern signals vs daily-only (win rate, avg return)
- [ ] Test multi-TF confirmation: only trade when daily + weekly agree
- [ ] Adjust `max_pattern_bars` or remove cap for weekly/monthly

**Status:** Idea — needs implementation + backtest

---

## Future Ideas (parking lot)

- VIX regime filter (high vol vs low vol environments)
- Earnings avoidance (skip trades around earnings dates)
- Volume confirmation requirement (only trade volume-confirmed patterns)
- Multi-timeframe confirmation (weekly + daily pattern alignment)
- Walk-forward validation on all strategies to check overfitting
