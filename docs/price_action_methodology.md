# Price Action (裸K线交易法) — Complete Methodology Reference

> Source: 《裸K线交易法 — 价格行为(Price Action)全面详解》 by 许佳聪 (小酱), 2019
> Purpose: Machine-readable reference for automated trading system implementation.
> This document encodes the complete trading methodology so that an AI system can implement, backtest, and execute trades following these rules without ambiguity.

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Candlestick Fundamentals](#2-candlestick-fundamentals)
3. [Pinbar — The Primary Signal](#3-pinbar--the-primary-signal)
4. [Composite Patterns — Advanced Pinbar](#4-composite-patterns--advanced-pinbar)
5. [Key Levels — Where to Trade](#5-key-levels--where-to-trade)
6. [The 7-Point Signal Scoring System](#6-the-7-point-signal-scoring-system)
7. [Entry Methods](#7-entry-methods)
8. [Stop Loss and Take Profit](#8-stop-loss-and-take-profit)
9. [Position Sizing and Risk Management](#9-position-sizing-and-risk-management)
10. [The Three-Line Exit Method](#10-the-three-line-exit-method)
11. [Trading System Framework (3M)](#11-trading-system-framework-3m)
12. [Implementation Pseudocode](#12-implementation-pseudocode)

---

## 1. Core Philosophy

### 1.1 Naked Candlestick Trading

This is a **pure price action** methodology. No indicators (no moving averages, no MACD, no RSI, no Bollinger Bands). Only:
- Candlestick patterns (K-line shapes)
- Horizontal key levels (support/resistance)
- Price trajectory analysis

The rationale: all indicators are derived from price. By reading price directly, you eliminate lag and derivative noise.

### 1.2 Follow Institutional Money

The core insight: **price movement is driven by institutional traders** (banks, funds, large accounts), not retail. Our job is to identify where institutions are buying and selling by reading the footprints they leave on the chart:
- **Turning points (拐点):** Where price changes direction sharply — these are institutional transaction points
- **Key levels:** Horizontal lines drawn through turning points — these are prices where institutions have repeatedly acted
- **Pinbar signals:** Candles that show the market "lied" about its direction — institutional manipulation revealed

### 1.3 The 3M Framework

Successful trading requires three components, in order of importance:
1. **Mind (心态)** — 40%: Psychology, discipline, emotional control
2. **Money (资金管理)** — 30%: Position sizing, risk management, capital preservation
3. **Market (市场分析)** — 30%: Technical analysis, signal identification

Most traders focus only on Market analysis. The book emphasizes that Market analysis is the *least* important of the three — it accounts for only ~30% of trading success.

---

## 2. Candlestick Fundamentals

### 2.1 The Four Elements of a Candle

Every candle has exactly 4 data points:
- **Open price (开盘价)**
- **Close price (收盘价)**
- **High price (最高价)**
- **Low price (最低价)**

Derived measurements:
- **Body** = |Close - Open|
- **Upper wick (上影线)** = High - max(Open, Close)
- **Lower wick (下影线)** = min(Open, Close) - Low
- **Total range** = High - Low
- **Bullish candle (阳线)** = Close > Open
- **Bearish candle (阴线)** = Close < Open

### 2.2 Key Single-Candle Patterns

| Pattern | Description | Signal |
|---------|-------------|--------|
| Hammer (锤线) | Long lower wick, small body at top | Bullish reversal at support |
| Shooting Star (流星线) | Long upper wick, small body at bottom | Bearish reversal at resistance |
| Doji (十字星) | Open ≈ Close, wicks both directions | Indecision, potential reversal |
| Marubozu (光头光脚) | No wicks, full body | Strong directional momentum |
| Spinning Top (螺旋线) | Small body, long wicks both sides | Indecision (NOT a valid Pinbar) |

### 2.3 Multi-Candle Patterns

| Pattern | Candles | Description | Signal |
|---------|---------|-------------|--------|
| Three White Soldiers (红三兵) | 3 | Three consecutive bullish candles | Bullish continuation |
| Three Black Crows (黑三兵) | 3 | Three consecutive bearish candles | Bearish continuation |
| Morning Star (启明星) | 3 | Bearish + doji/small + bullish | Bullish reversal |
| Evening Star (黄昏星) | 3 | Bullish + doji/small + bearish | Bearish reversal |
| Bullish Engulfing (看涨吞没) | 2 | Bearish + bullish (body engulfs) | Bullish reversal |
| Bearish Engulfing (看空吞没) | 2 | Bullish + bearish (body engulfs) | Bearish reversal |

### 2.4 Three White Soldiers / Three Black Crows Variants

Each has 3 sub-types:
1. **Advancing (前进模式):** Bodies getting larger — momentum increasing, trend continuation likely
2. **Stalling (停滞模式):** Bodies getting smaller — momentum fading, trend may exhaust
3. **Stagnating (滞涨/滞跌模式):** First and third candles small, middle is large — rapid force release near key level, direction uncertain

### 2.5 The Essence of Candlestick Patterns — Multi-Timeframe Equivalence

**Critical concept:** The same price movement looks different on different timeframes:
- A 1H shooting star = a 30min evening star = four 15min candles forming a bearish pattern
- All represent the same underlying price trajectory
- This means: **patterns on different timeframes are interchangeable if you understand the underlying price movement**

The four elements (O, H, L, C) are identical regardless of how many sub-candles compose the pattern.

---

## 3. Pinbar — The Primary Signal

### 3.1 Definition

A Pinbar is a single candlestick where:

```
RULE: The dominant wick (主影线) must be > 2/3 of the total candle range
```

More precisely:
- **Dominant wick:** The longer of the two wicks
- **Secondary wick (副影线):** The shorter wick — must be short (not a spinning top)
- **Body:** Can be bullish or bearish — this is secondary to the wick structure

**Formal detection criteria:**
```python
total_range = high - low
if total_range == 0:
    return False  # doji with no range, skip

upper_wick = high - max(open, close)
lower_wick = min(open, close) - low
dominant_wick = max(upper_wick, lower_wick)
secondary_wick = min(upper_wick, lower_wick)

is_pinbar = (dominant_wick / total_range) > 2/3
is_not_spinning_top = secondary_wick < dominant_wick / 3  # secondary wick short enough
```

### 3.2 Direction

- **Bullish Pinbar (看涨):** Lower wick is dominant → bullish rejection at support
- **Bearish Pinbar (看空):** Upper wick is dominant → bearish rejection at resistance

### 3.3 Core Meaning — "Pinocchio's Nose"

A Pinbar represents the market **lying**:
- During the candle's formation, price moved strongly in one direction (the wick)
- But by close, it had reversed back (the body is opposite to the wick direction)
- The wick is "Pinocchio's nose" — the longer the nose, the bigger the lie
- **The market's true intent is the OPPOSITE of the wick direction**

### 3.4 The "Face and Nose" Concept

- **Nose = Pinbar** (the signal candle)
- **Face = surrounding candles** (the context)

Two conditions for a good signal:
1. **The nose must be prominent relative to the face** — a Pinbar must be large enough to stand out on the chart. A tiny Pinbar in a sea of large candles is meaningless. Minimum amplitude should be comparable to recent average candle size (at least median of last 20 bars).
2. **The nose-to-face ratio matters** — this is a visual/subjective judgment. A very obvious "nose" protruding from the chart is a better signal.

### 3.5 Left Eye and Right Eye

The candles immediately adjacent to the Pinbar:

**Left Eye (左眼) — the candle BEFORE the Pinbar:**
- Stability check: Pinbar's **body (open-to-close, NOT wicks)** should be contained within the left eye's high-to-low range
- If the Pinbar body gaps outside the left eye range, the signal is unstable (possibly caused by a sudden event, not normal market dynamics)
- Left eye amplitude should NOT be larger than the Pinbar — if it is, the preceding trend force is too strong, reducing signal reliability
- **Gapped Pinbars** (body outside left eye) require extra caution in continuous markets

**Right Eye (右眼) — the candle AFTER the Pinbar:**
- Confirmation check: When the right eye's price breaks the Pinbar's low (for bearish) or high (for bullish), the signal is **confirmed**
- Used for breakout entry timing
- Many traders enter at a preset price rather than waiting for full right-eye confirmation

### 3.6 What Pinbar is NOT

Reject these as NOT valid Pinbar signals:
- **Spinning tops (螺旋线):** Both wicks are long → indecision, not directional rejection
- **Large body with moderate wicks:** Body too large → this is just a regular candle
- **Tiny Pinbar in ranging market:** Even if shape qualifies, amplitude too small to be meaningful
- **Pinbar NOT at a key level:** A Pinbar away from support/resistance is NOT a signal — it's just a candle shape

---

## 4. Composite Patterns — Advanced Pinbar

The book treats multi-candle reversal patterns as "transformed Pinbar" (变了形的Pinbar). When you merge the component candles into one, the result is a Pinbar shape.

### 4.1 Morning Star (启明星) — Bullish

```
Candle 1: Bearish (sets the downward context)
Candle 2: Small body / doji (indecision at the bottom)
Candle 3: Bullish (reversal confirmation)

Merge: Open=C1.open, Close=C3.close, High=max(all highs), Low=min(all lows)
Result: Bullish Pinbar shape with long lower wick
```

**Validation:**
- Third candle should close above 50% of first candle's body
- Pattern appears at support / low point

### 4.2 Evening Star (黄昏星) — Bearish

Mirror of Morning Star at resistance / high point.

```
Candle 1: Bullish
Candle 2: Small body / doji
Candle 3: Bearish

Merge result: Bearish Pinbar shape with long upper wick
```

### 4.3 Bullish Engulfing (看涨吞没/阳包阴) — Bullish

```
Candle 1: Bearish
Candle 2: Bullish, body completely engulfs candle 1's body

Merge: Open=C1.open, Close=C2.close, High=max(highs), Low=min(lows)
Result: Always a bullish Pinbar (close is always above open when merged)
```

The author's **personal favorite** pattern. States: "when engulfing appears meeting the right conditions, the win rate is astonishingly high."

### 4.4 Bearish Engulfing (看空吞没/阴包阳) — Bearish

Mirror of Bullish Engulfing.

```
Candle 1: Bullish
Candle 2: Bearish, body completely engulfs candle 1's body

Merge result: Always a bearish Pinbar
```

### 4.5 Engulfing Variant — Three-Candle Engulfing

```
Candle 1: Small
Candle 2: Small
Candle 3: Large, body range > sum of candle 1 + candle 2 ranges

This is also a valid composite signal. The final large candle must be sufficiently large.
```

### 4.6 Composite Pattern Rules

**Signal strength ranking:**
1. Engulfing (吞没) — strongest
2. Morning/Evening Star (双星) — strong
3. Single Pinbar — standard

**Pinbar combination principle (Pinbar组合原则):**
When looking for composite Pinbar in lower timeframes (e.g., checking 4 x 1H candles that form a 4H Pinbar):
- The number of candles matching the trade direction should be ≤ the number of opposite candles
- Example: For a bearish composite, bearish candles ≤ bullish candles (shows the reversal force overcoming the trend)
- If bearish candles > bullish candles in a bearish composite, it's less reliable (the bears were already dominant, so the "reversal" signal is weaker)

**Composite patterns do NOT need to pass single-candle Pinbar shape criteria.** They have their own qualification rules. The merged OHLC is used for entry/exit calculations only.

---

## 5. Key Levels — Where to Trade

### 5.1 What Are Key Levels?

Key levels are **horizontal price zones** where institutional traders have repeatedly bought or sold. They are drawn through **turning points (拐点)** — prices where the market changed direction significantly.

**Key levels are ZONES, not exact prices.** When price approaches the zone, we consider it "touching" the key level.

### 5.2 How to Draw Key Levels

Draw horizontal lines through:
1. **Prominent turning points** — swing highs and swing lows where price made significant reversals
2. **Consolidation zones** — areas where price traded sideways for extended periods
3. **Turning points have priority over consolidation zones**

**The "ruler conquers all" (一把尺子打天下):** In this methodology, a simple horizontal line is the most powerful tool for market analysis.

### 5.3 Key Level Strength Rules

Three rules determine which key levels are strongest:

**Rule 1: Higher timeframe turning points are stronger (拐点级别越大越有效)**
- A turning point on a daily chart is stronger than one on a 4H chart
- Higher timeframe = more candles involved in the turning point = more trading volume = more significance

**Rule 2: More recent turning points are stronger (离现价越近越有效)**
- A turning point from last week is more relevant than one from last year
- Ancient levels may still matter if they were extreme (all-time highs/lows), but generally recent levels take priority
- Adjust key levels based on the most recent turning points near current price

**Rule 3: More touches = stronger level (拐点越多越有效)**
- If price has turned at this level 5 times, it's much stronger than a level with only 2 touches
- Each touch represents another instance of institutional activity at this price
- Like truck tires — multiple wheels support more weight

### 5.4 Polarity Reversal Principle (极性转化原则)

**When a key level is broken, its role reverses:**
- Broken **resistance** becomes **support**
- Broken **support** becomes **resistance**

This happens because:
- Traders who bought at the support level and are now underwater will want to exit at breakeven when price returns
- This selling pressure at the old support creates resistance
- Conversely, short sellers who got stopped out above broken resistance will create buying support at the old resistance

**Implementation:**
```python
if level.role == SUPPORT and price closes below level for 1-2 candles:
    level.role = RESISTANCE
    level.strength += bonus  # polarity reversal confirmation increases strength
elif level.role == RESISTANCE and price closes above level for 1-2 candles:
    level.role = SUPPORT
    level.strength += bonus
```

### 5.5 False Breakout (假突破)

**Definition:** Price pierces through a key level then reverses back to the original side.

**Meaning:**
- Institutional manipulation — they push price through the level to trigger breakout traders' stops, then reverse
- The false breakout **reveals the institution's true intent** — the direction OPPOSITE to the breakout
- False breakout at a key level with a Pinbar is one of the **strongest signals in the entire system**

**Detection:**
```python
def is_false_breakout(pinbar, key_level):
    wick_tip = pinbar.high if pinbar.direction == BEARISH else pinbar.low
    close = pinbar.close

    if key_level.role == RESISTANCE:
        # Wick pierced above resistance, but closed below
        return wick_tip > key_level.price and close < key_level.price
    else:  # SUPPORT
        # Wick pierced below support, but closed above
        return wick_tip < key_level.price and close > key_level.price
```

### 5.6 Other Key Levels

**Gaps (跳空缺口):**
- Gap edges act as key levels
- Gap-up: the bottom of the gap (upper edge of the pre-gap candle) is the key price
- Gap-down: the top of the gap (lower edge of the pre-gap candle) is the key price
- Mainly relevant on daily and weekly charts

**Round Numbers (整数关口):**
- Psychological levels (e.g., 1.0000, 20000, 100.00)
- Not always reliable, but worth noting when they coincide with other key levels

**Fibonacci Levels (黄金分割):**
- 38.2%, 50%, and 61.8% retracement levels of a significant trend
- Used for both key level identification AND entry method calculations
- Draw from extreme low to extreme high (or vice versa) of a clear trend swing
- Most effective in strong trending markets; less reliable in choppy/ranging markets

---

## 6. The 7-Point Signal Scoring System

This is the core decision framework. Every Pinbar or composite pattern signal must be evaluated against these 7 criteria before trading.

### 6.1 Two Mandatory Conditions (必要条件)

**Both must be TRUE. If either fails, DO NOT TRADE — regardless of how good the signal looks.**

#### Mandatory 1: Is the signal at a clear key level?

```python
def at_key_level(signal, levels, proximity_pct=0.005):
    """Signal must be within proximity_pct of a recognized key level."""
    for level in levels:
        distance = abs(signal.wick_tip - level.price) / signal.close
        if distance <= proximity_pct:
            return True
    return False
```

**Rationale:** Price moves between key levels. Signals between key levels are noise. All tradeable signals occur AT or very near key levels. A Pinbar not at a key level is just a candle shape — not a signal.

#### Mandatory 2: Is the signal at a clear high or low?

```python
def at_high_or_low(signal, preceding_candles, min_trend_bars=3):
    """
    Signal must be at the extreme of a directional sequence.
    - Bearish signal: wick tip is the highest high of preceding N candles,
      and those candles form higher-highs (uptrend ending at this signal)
    - Bullish signal: wick tip is the lowest low of preceding N candles,
      and those candles form lower-lows (downtrend ending at this signal)
    """
    if signal.direction == BEARISH:
        is_extreme = signal.high >= max(c.high for c in preceding_candles[-min_trend_bars:])
        is_trending = all(
            preceding_candles[i].high > preceding_candles[i-1].high
            for i in range(-min_trend_bars+1, 0)
        )
    else:  # BULLISH
        is_extreme = signal.low <= min(c.low for c in preceding_candles[-min_trend_bars:])
        is_trending = all(
            preceding_candles[i].low < preceding_candles[i-1].low
            for i in range(-min_trend_bars+1, 0)
        )
    return is_extreme and is_trending
```

**Rationale:** Pinbar in the middle of a range (横盘) is NOT tradeable. In ranging markets, only trade at the range edges (support/resistance boundaries), and only with a clear mini-trend leading into the level. Pinbar must be a clear "turning point" visually.

### 6.2 Five Detail Criteria (细节项) — Star Rating

Each criterion earns 1 star. **Minimum 2 stars required to trade.** More stars = stronger signal = higher confidence.

#### Star 1: Is the Pinbar visually prominent? (明显)

```python
def is_visually_prominent(signal, recent_candles, lookback=20):
    """Signal amplitude must be >= median amplitude of recent candles."""
    signal_amplitude = signal.high - signal.low
    recent_amplitudes = [c.high - c.low for c in recent_candles[-lookback:]]
    median_amplitude = sorted(recent_amplitudes)[len(recent_amplitudes) // 2]
    return signal_amplitude >= median_amplitude
```

**Rationale:** The "nose must be visible on the face." Small Pinbar buried among large candles indicates low market interest at that level — no institutional activity, no strong rejection.

#### Star 2: Is there a false breakout? (假突破)

```python
def has_false_breakout(signal, key_levels):
    """Signal wick pierced through a key level but closed back on the original side."""
    for level in key_levels:
        if is_false_breakout(signal, level):  # See section 5.5
            return True
    return False
```

**Rationale:** False breakout = institutional manipulation revealed. This is the author's personal favorite criterion. If a signal has a false breakout, the reversal probability is very high.

#### Star 3: Left-eye containment (左眼包含)

```python
def left_eye_valid(signal, left_eye_candle):
    """
    Two sub-conditions:
    1. Pinbar body (open-to-close) is within left eye's high-low range
    2. Signal amplitude > left eye amplitude
    """
    body_high = max(signal.open, signal.close)
    body_low = min(signal.open, signal.close)

    contained = body_low >= left_eye_candle.low and body_high <= left_eye_candle.high
    larger = (signal.high - signal.low) > (left_eye_candle.high - left_eye_candle.low)

    return contained and larger
```

**Rationale:** If the Pinbar body is outside the left eye's range, the market is moving too fast (possibly a gap or strong trend), making the reversal signal unstable. If the left eye is larger than the signal, the preceding candle's force is stronger than the signal's rejection force.

#### Star 4: Trend alignment (顺势)

```python
def trend_aligned(signal, higher_tf_bias):
    """Signal direction matches the higher-timeframe trend direction."""
    if signal.direction == BULLISH and higher_tf_bias == BULLISH:
        return True  # buying at support in an uptrend
    if signal.direction == BEARISH and higher_tf_bias == BEARISH:
        return True  # selling at resistance in a downtrend
    return False
```

**Rationale:** Trading with the trend has higher win rate. Bullish signals in uptrends and bearish signals in downtrends are more reliable. Counter-trend signals can work but require more stars from other criteria. If the market is ranging, this criterion does not apply (neither pass nor fail).

#### Star 5: R:R ratio >= 1.5:1 for breakout entry (盈亏比)

```python
def rr_sufficient(signal, next_key_level, min_rr=1.5):
    """
    Using breakout entry:
    - Entry = breakout point (Pinbar high for bullish, low for bearish)
    - Stop loss = wick tip (Pinbar low for bullish, high for bearish)
    - Take profit = next key level in trade direction

    R:R = |take_profit - entry| / |entry - stop_loss| >= 1.5
    """
    if signal.direction == BULLISH:
        entry = signal.high  # breakout above pinbar high
        stop_loss = signal.low  # wick tip
        take_profit = next_key_level.price  # next resistance
    else:
        entry = signal.low
        stop_loss = signal.high
        take_profit = next_key_level.price  # next support

    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)

    if risk == 0:
        return False
    return (reward / risk) >= min_rr
```

**Rationale:** The R:R calculation uses the "worst case" scenario — breakout entry with full wick as stop loss, and only the next key level as target (not hoping for more). The author's minimum is 1.5:1, though many traders prefer 2:1+. If R:R is insufficient at breakout entry, consider retracement entry methods (see Section 7) to improve R:R.

### 6.3 Scoring Summary

```
MANDATORY: at_key_level AND at_high_or_low → both must be TRUE
STARS: sum of (visible, false_breakout, left_eye, trend_aligned, rr_sufficient)

TRADEABLE = mandatory_pass AND stars >= 2
SIGNAL_STRENGTH = "2+" + str(stars)  # e.g., "2+3" means mandatory passed + 3 stars
```

**Practical examples from the book:**
- Gold 4H: 2+3 → tradeable, chose close entry, SL=48pts, TP=117pts, R:R=2.43:1
- JPY Daily: 2+2 → tradeable, forced 61.8% retracement entry due to tight R:R
- Crude Oil Daily: 2+4 → excellent signal, chose breakout entry, SL=175pts, TP=310pts, R:R=1.77:1

---

## 7. Entry Methods

The book describes 6 entry methods. Selection depends on signal characteristics, R:R requirements, and profit space.

### 7.1 Close Entry (收线入场)

**When:** Signal candle closes → enter immediately at close price.
**Stop Loss:** Reversal of signal (price breaks opposite wick tip).
**Best for:** 4H charts (less gap risk), clean signals.
**Avoid:** Daily charts on Fridays (Monday gap risk), highly volatile markets.

```python
entry_price = signal.close
stop_loss = signal.high + buffer  # for bearish signal
# OR
stop_loss = signal.low - buffer   # for bullish signal
```

### 7.2 Breakout Entry (突破入场)

**When:** Price breaks the signal's extreme in the trade direction.
**Stop Loss Options:**
- Full wick: stop at the opposite wick tip (safest but widest)
- 50% of signal: stop at the midpoint of the signal candle (tighter, but signal already confirmed)

**This is the most commonly used entry method** — most reliable because the breakout confirms the signal.

```python
if signal.direction == BULLISH:
    entry_price = signal.high  # breakout above pinbar high triggers entry
    stop_loss_full = signal.low - buffer  # full wick stop
    stop_loss_50pct = signal.low + (signal.high - signal.low) * 0.5  # 50% stop
else:
    entry_price = signal.low
    stop_loss_full = signal.high + buffer
    stop_loss_50pct = signal.high - (signal.high - signal.low) * 0.5
```

**50% stop rationale:** Once price has broken out, it's unlikely to retrace more than 50% of the signal. If it does, the signal has probably failed.

### 7.3 38.2% Retracement Entry (回调38.2%入场)

**When:** Sufficient profit space, waiting for a pullback to get better entry.
**Entry:** At 38.2% Fibonacci retracement of the signal range.
**Stop Loss:** Wick tip (opposite end of signal).

```python
signal_range = signal.high - signal.low
if signal.direction == BULLISH:
    entry_price = signal.high - signal_range * 0.382  # 38.2% pullback from high
    stop_loss = signal.low - buffer
else:
    entry_price = signal.low + signal_range * 0.382
    stop_loss = signal.high + buffer
```

### 7.4 50% Retracement Entry (回调50%入场)

**When:** Signal is very large (wide stop loss if using breakout), or profit space is tight.
**Entry:** At 50% of the signal range.
**Stop Loss:** Wick tip.

```python
if signal.direction == BULLISH:
    entry_price = signal.low + signal_range * 0.5
    stop_loss = signal.low - buffer
else:
    entry_price = signal.high - signal_range * 0.5
    stop_loss = signal.high + buffer
```

**R:R advantage:** If using 50% retracement:
- Stop loss is halved compared to breakout entry
- Position size can nearly double (for same risk amount)
- Profit space increases by the 50% retracement distance
- Net result: potential profit ≈ 2.66x of breakout entry (book's calculation: P' = 2A × 1.33B = 2.66P)

**Trade-off:** The market may not retrace to 50%. You might miss the move entirely.

### 7.5 61.8% Retracement Entry (回调61.8%入场)

**When:** Last resort when profit space is very tight and 50% retracement still doesn't achieve 1.5:1 R:R.
**Entry:** At 61.8% of the signal range.
**Stop Loss:** Wick tip.

**Risk:** If price retraces past 61.8%, the signal is likely failing. This is the most aggressive retracement entry.

### 7.6 Scaled Entry (分批进场)

**When:** Large position planned, want to reduce average stop loss exposure.
**Method:** Place multiple limit orders at key Fibonacci levels:

```python
# Example: planned 10 contracts
entries = [
    {"level": "38.2%", "size": 2, "price": signal.low + range * 0.382},  # first fill
    {"level": "50%",   "size": 3, "price": signal.low + range * 0.5},    # second fill
    {"level": "breakout", "size": 5, "price": signal.high},              # confirmation fill
]
# ALL orders share the same stop loss: wick tip (signal.low - buffer)
```

**Cancellation rules:**
- If breakout fills → keep retracement orders open (they add to position at better prices)
- If retracement fills first → keep breakout order open
- Cancel ALL unfilled orders when: (a) price hits stop loss, or (b) signal expires (e.g., 10 bars)

**Advantage:** Even if not all orders fill, the partial position has smaller risk than a full breakout entry.

### 7.7 Dual-Order Strategy (挂两个单)

A practical hybrid:
- Order 1: Breakout entry, SL at 50% of signal
- Order 2: 50% retracement entry, SL at wick tip

When one fills, cancel the other. This captures both scenarios (direct breakout vs. pullback) without doubling exposure.

### 7.8 Entry Method Selection Logic

```python
def select_entry_method(signal, next_key_level):
    signal_range = signal.high - signal.low
    profit_space = abs(next_key_level.price - signal.breakout_price)
    atr = calculate_atr(14)

    # If profit space is very large relative to signal
    if profit_space / signal_range > 2.0:
        return "breakout"  # plenty of room, safest entry

    # If signal is very large (wide stop)
    if signal_range > 1.5 * atr:
        return "retracement_50"  # reduce stop loss distance

    # If R:R insufficient at breakout but sufficient at 50%
    breakout_rr = profit_space / signal_range
    retrace_50_rr = (profit_space + signal_range * 0.5) / (signal_range * 0.5)

    if breakout_rr < 1.5 and retrace_50_rr >= 1.5:
        return "retracement_50"

    # If even 50% doesn't work, try 61.8%
    retrace_618_rr = (profit_space + signal_range * 0.618) / (signal_range * 0.382)
    if retrace_618_rr >= 1.5:
        return "retracement_618"  # aggressive but achieves minimum R:R

    # If nothing works
    return "skip"  # insufficient profit space, do not trade
```

---

## 8. Stop Loss and Take Profit

### 8.1 Stop Loss Rules

**Fundamental rule: No stop loss = no trade. Every position MUST have a stop loss.**

| Entry Method | Stop Loss Location |
|---|---|
| Close entry | Wick tip + buffer |
| Breakout entry (conservative) | Wick tip + buffer |
| Breakout entry (aggressive) | 50% of signal + buffer |
| Retracement entry (any %) | Wick tip + buffer |
| Scaled entry | Wick tip + buffer (shared across all legs) |

**Buffer:** Small amount beyond the wick to avoid getting stopped by noise. Typically a few points (5 points for crude oil, varies by instrument).

**"Consider the worst case" (最悲观的情况):** Always calculate R:R using the maximum stop loss (wick tip) and the minimum take profit (nearest key level).

### 8.2 Take Profit Rules

**Primary target:** The next key level in the trade direction.

```python
if signal.direction == BULLISH:
    take_profit = next_resistance_level.price - buffer  # leave room before the level
else:
    take_profit = next_support_level.price + buffer
```

**Leave room before the level:** Price often doesn't reach the exact key level — it might fall short by a few points. Set take profit slightly before the level to avoid missing the fill.

**Alternative TP: Signal height multiples:**
- 1x signal height: conservative
- 2x signal height: standard
- 3x signal height: aggressive (requires excellent signal quality and large trend)

---

## 9. Position Sizing and Risk Management

### 9.1 Fixed Risk Per Trade

```python
risk_per_trade = account_balance * risk_pct  # e.g., 1% of account
point_value = instrument.point_value  # dollar value per point per contract
stop_loss_points = abs(entry - stop_loss) / instrument.tick_size

position_size = risk_per_trade / (stop_loss_points * point_value)
```

This ensures every trade risks the same dollar amount regardless of stop loss distance. Tighter stops → larger positions. Wider stops → smaller positions.

### 9.2 Risk Rules from the Book

- Maximum risk per trade: 1-2% of account
- Maximum daily loss: Defined amount (stop trading for the day)
- Maximum concurrent positions: Limit to avoid correlated exposure
- **Never risk money you can't afford to lose** — only trade with "idle money" (闲钱)

### 9.3 The Retracement Advantage

When using 50% retracement entry vs. breakout entry with the same risk amount:
- Stop loss distance is halved
- Position size doubles
- Profit space increases
- **P' = 2A × 1.33B ≈ 2.66P** (position is 2x, profit space is 1.33x)

This is why the book emphasizes retracement entries for improving risk-adjusted returns.

---

## 10. The Three-Line Exit Method (三线战法)

An advanced exit strategy for capturing extended trends while protecting profits.

### 10.1 Concept

Instead of setting a fixed take profit, use a **trailing stop based on the most recent 3 candles:**

```python
def three_line_trailing_stop(direction, recent_3_candles):
    """
    In a strong trend, pullbacks rarely exceed 3 candles.
    If they do, the trend may be reversing.
    """
    if direction == BEARISH:  # short position
        # Stop above the highest high of the most recent 3 candles
        return max(c.high for c in recent_3_candles) + buffer
    else:  # long position
        # Stop below the lowest low of the most recent 3 candles
        return min(c.low for c in recent_3_candles) - buffer
```

### 10.2 Rules

1. **Initial stop loss:** Always at the signal's wick tip (standard rule)
2. **No take profit set initially** — let the trend run
3. **After 3 candles past entry:** Start trailing stop using 3-candle extreme
4. **Update every candle:** Recalculate the 3-candle extreme stop each new bar
5. **Exit when hit:** The trailing stop gets triggered

### 10.3 When to Use

- **Use in strong, clear trends** at significant turning points (e.g., signal at all-time high/low)
- **Do NOT use in choppy markets** — the 3-candle stop will get hit quickly, possibly at a loss
- The trade-off: you might give back initial TP profits, but you capture much larger moves when trends extend

### 10.4 Example from the Book

JPY Daily: Entry via 61.8% retracement, initial stop at wick tip (50 points risk). Using three-line method, the trade ran for 170 points before the trailing stop hit — achieving 3.4:1 R:R. A fixed TP at the next key level would have captured only ~50 points (1:1).

---

## 11. Trading System Framework (3M)

### 11.1 Complete Trading System Components

A complete trading system answers 8 questions:
1. **What to trade (标的):** Which instruments/markets
2. **Position size (仓位):** How many contracts/shares
3. **Direction (方向):** Long or short
4. **Entry (入场点):** At what price
5. **Stop loss (止损):** When to exit losing trades
6. **Take profit (止盈):** When to exit winning trades
7. **Contingency (对策):** What to do with unexpected events during a trade
8. **Follow-up (后手):** What to do after a trade closes (reverse? re-enter? wait?)

### 11.2 Building Your System — Self-Assessment Questions

Before choosing a trading system, answer:
1. How much capital do you have? (Determines which markets you can trade)
2. Will this capital be needed short-term? (Determines trade holding period)
3. How much time per day for trading? (Determines timeframe: scalp, day, swing)
4. Your learning ability? (Determines system complexity)
5. Your self-discipline? (Low discipline → strict rules, tight stops; high discipline → flexible system)
6. Maximum tolerable loss? (Determines risk per trade)
7. Expected return? (Must be realistic relative to risk tolerance)

### 11.3 Key Principles

- **Systematic approach > discretionary trading:** Having rules removes emotion from decisions
- **Consistency:** The same conditions should produce the same actions every time
- **Risk management > analysis:** A 60% win rate system with good risk management beats a 70% system without it
- **Adapt your system to market conditions:** Range-bound systems and trend systems both have strengths; the best systems work in both environments
- **Practice:** "World champions are made through practice." Paper trade, backtest, review — before going live.

---

## 12. Implementation Pseudocode

### 12.1 Complete Signal Detection Pipeline

```python
def detect_signals(candles, key_levels, higher_tf_bias):
    signals = []

    # Step 1: Detect single Pinbar
    for i in range(2, len(candles)):
        candle = candles[i]
        if is_valid_pinbar(candle):
            signals.append(PinbarSignal(candle, i))

    # Step 2: Detect composite patterns
    for i in range(3, len(candles)):
        pattern = detect_composite(candles[i-2:i+1])
        if pattern:
            signals.append(CompositeSignal(pattern, i))

    # Step 3: Score each signal
    scored_signals = []
    for signal in signals:
        # Mandatory checks
        m1 = at_key_level(signal, key_levels)
        m2 = at_high_or_low(signal, candles[:signal.index])

        if not (m1 and m2):
            continue  # Skip — mandatory check failed

        # Detail stars
        left_eye = candles[signal.index - 1]
        stars = 0
        stars += is_visually_prominent(signal, candles[:signal.index])
        stars += has_false_breakout(signal, key_levels)
        stars += left_eye_valid(signal, left_eye)
        stars += trend_aligned(signal, higher_tf_bias)
        stars += rr_sufficient(signal, find_next_level(signal, key_levels))

        if stars >= 2:
            signal.score = f"2+{stars}"
            signal.stars = stars
            scored_signals.append(signal)

    # Step 4: Compute entry methods for each scored signal
    for signal in scored_signals:
        signal.entries = compute_all_entries(signal, key_levels)

    return scored_signals
```

### 12.2 Complete Entry Computation

```python
def compute_all_entries(signal, key_levels):
    entries = []
    next_level = find_next_level(signal, key_levels)
    signal_range = signal.high - signal.low
    buffer = signal_range * 0.01  # 1% of signal as buffer

    for method in [CLOSE, BREAKOUT, RETRACE_382, RETRACE_50, RETRACE_618, SCALED]:
        entry = compute_entry(signal, method, next_level, buffer)
        if entry and entry.rr >= 1.5:
            entries.append(entry)

    return sorted(entries, key=lambda e: e.rr * e.suitability, reverse=True)
```

### 12.3 Key Level Detection

```python
def detect_key_levels(candles, pivot_lookback=5):
    # Step 1: Find swing highs and swing lows
    pivots = find_pivots(candles, lookback=pivot_lookback)

    # Step 2: Cluster pivots at similar prices
    clusters = cluster_pivots(pivots, tolerance=atr * 0.3)

    # Step 3: Score each cluster
    for cluster in clusters:
        cluster.strength = score_key_level(
            timeframe_grade=cluster.max_timeframe,
            recency=cluster.most_recent_touch,
            touch_count=cluster.num_touches
        )

    # Step 4: Track polarity reversals
    for level in existing_levels:
        if is_broken(level, candles[-2:]):
            level.role = flip_role(level.role)
            level.strength += polarity_bonus

    return clusters
```

---

## Appendix A: Quick Reference — Signal Checklist

For each potential signal, run through this checklist:

```
□ MANDATORY 1: At a clear key level?
□ MANDATORY 2: At a clear high/low with preceding trend?

If both YES, continue:

☆ Star 1: Pinbar is visually prominent (stands out on chart)?
☆ Star 2: False breakout present (wick pierced level, close reversed)?
☆ Star 3: Body within left eye range AND amplitude > left eye?
☆ Star 4: Direction aligned with higher-TF trend?
☆ Star 5: Breakout entry R:R >= 1.5:1?

Total stars: ___  (minimum 2 to trade)
Signal rating: 2+___

Entry method: ___ (breakout / retracement_% / close / scaled)
Entry price: ___
Stop loss: ___
Take profit: ___
R:R ratio: ___
Position size: ___ contracts
Risk amount: $___
```

## Appendix B: Common Mistakes to Avoid

1. **Trading Pinbar not at key level** — Most common mistake. A Pinbar in no-man's-land is just a candle
2. **Trading in the middle of a range** — Only trade at range edges with a clear mini-trend
3. **Chasing breakouts** — Don't buy the new high / sell the new low immediately. Wait for confirmation or pullback
4. **Ignoring R:R** — A "perfect" signal with 0.5:1 R:R is a bad trade
5. **Over-trading** — Not every candle needs to be traded. Wait for 2+2 or better
6. **Moving stop loss** — Never move stop loss further from entry to "give it room"
7. **Revenge trading** — After a stop loss, do NOT immediately re-enter in the opposite direction
8. **Using this system during news events** — Candlestick patterns are statistical tools that work in normal market conditions. During major news (NFP, FOMC, etc.), patterns become unreliable

## Appendix C: Timeframe Recommendations

| Trading Style | Chart Timeframe | Key Level Timeframe | Signal Hold Time |
|---|---|---|---|
| Scalping | 5m, 15m | 1H, 4H | Minutes to hours |
| Day Trading | 15m, 1H | 4H, Daily | Hours |
| Swing Trading | 4H, Daily | Daily, Weekly | Days to weeks |
| Position Trading | Daily, Weekly | Weekly, Monthly | Weeks to months |

**The book's preferred setup:** 4H chart for signals, Daily chart for key levels. This balances signal frequency with signal quality.

**Multi-timeframe approach:** Use higher timeframe for key levels and trend direction, lower timeframe for entry signals. Higher TF key levels carry more weight than lower TF key levels.
