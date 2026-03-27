# Stability Score & Rank Score — TQQQ Strategy Ranking Metrics

## Purpose

Rank MA crossover strategies by **consistent, pain-adjusted performance combined with high returns** — not just raw returns or a single aggregate ratio. A strategy that makes money reliably month after month with manageable drawdowns AND strong total returns wins.

## Rank Score (final ranking metric)

```
Rank Score = 0.4 × Stability + 0.3 × CAGR_percentile + 0.3 × (1 - |MaxDD|_percentile)
```

- **Stability** (0.4): consistency and pain avoidance (see below)
- **CAGR percentile** (0.3): where does this strategy's annualized return rank among all viable combos? Higher = better
- **MaxDD percentile** (0.3): where does this strategy's max drawdown rank? Lower drawdown = better (inverted)

This ensures the top-ranked strategies are stable **AND** have strong returns **AND** limited drawdowns.

## Stability Score (consistency component)

```
Stability = 0.5 × Consistency + 0.3 × Win Frequency + 0.2 × Pain Avoidance
```

Where:

| Component | Formula | Range | What it captures |
|---|---|---|---|
| **Consistency** | `1 / (1 + std(rolling_12m_sharpe))` | 0–1 | Low variance of risk-adjusted returns across overlapping 12-month windows |
| **Win Frequency** | `pct_months_positive` | 0–1 | Fraction of months with positive return (out of ~120) |
| **Pain Avoidance** | `1 / (1 + ulcer_index)` | 0–1 | Inverse of drawdown pain (depth × duration) |

### Component Details

#### 1. Rolling 12-Month Sharpe Std (weight: 0.5)

- Compute Sharpe ratio over every trailing 252-day window
- Take the standard deviation of all those Sharpe values
- Low std = the strategy performs consistently regardless of when you measure it
- Uses ~120+ overlapping windows vs only 10 calendar years
- No arbitrary year-boundary effects

#### 2. Percent Months Positive (weight: 0.3)

- Count months where strategy return > 0, divide by total months
- ~120 data points over 10 years
- Simple, intuitive: "how often do I make money?"
- A strategy with 75% positive months *feels* stable to trade vs 55%

#### 3. Ulcer Index (weight: 0.2)

- `UI = sqrt(mean(drawdown_pct^2))`
- Measures both depth and duration of drawdowns
- A -30% drawdown lasting 6 months scores much worse than -30% lasting 2 weeks
- Captures the *pain* of holding through losses, which max drawdown alone misses

## Why This Composite

| Problem with single metrics | How composite fixes it |
|---|---|
| **Yearly Calmar** — only 10 data points, one bad week ruins a year, arbitrary year boundaries | Rolling Sharpe uses 120+ overlapping windows |
| **Max Drawdown** — a single event, doesn't capture recovery time | Ulcer Index captures depth × duration |
| **Sharpe** — penalizes upside volatility equally with downside | % months positive is directional |
| **CAGR** — says nothing about the path taken | All three components measure path quality |

## Weight Rationale

- **0.5 Consistency** — most important: is the strategy *reliably* good?
- **0.3 Win Frequency** — secondary: frequent wins build confidence to stay the course
- **0.2 Pain Avoidance** — tertiary: drawdown duration matters but is partially captured by rolling Sharpe already

## Interpretation

| Score | Rating | Meaning |
|---|---|---|
| > 0.70 | Excellent | Consistent returns, high win rate, mild drawdowns |
| 0.55–0.70 | Good | Reliable with occasional rough patches |
| 0.40–0.55 | Average | Noticeable inconsistency or drawdown pain |
| < 0.40 | Poor | Unreliable, long painful drawdowns, or low win rate |

## Previous Formula (deprecated)

```
Stability = Mean Yearly Calmar / (1 + Std of Yearly Calmar)
```

Problems: only 10 yearly data points, arbitrary calendar boundaries, max-drawdown single-event sensitivity. Replaced 2026-03-26.
