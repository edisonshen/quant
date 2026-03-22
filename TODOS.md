# TODOS

## Chart / Visualization

(No open items)

## AI/ML Pipeline

### ScoringStrategy protocol
**What:** Build BookScorer wrapping existing `score_setup`, MLScorer interface. Pipeline-first: validate end-to-end with BookScorer before swapping in ML.
**Priority:** P1
**Depends on:** FeatureExtractor ✓

### Feature Store (Parquet export)
**What:** Export features + labels to Parquet files for ML training/backtesting.
**Priority:** P1

### HMM Regime Detector
**What:** Train on historical NQ/ES/GC data. 4 regimes: trending-up, trending-down, ranging, volatile.
**Priority:** P2

### XGBoost Pattern Scorer
**What:** Single model with regime as feature. Train on labeled features from backtest.
**Priority:** P2
**Depends on:** Feature Store, HMM

## Completed

### Wire up real multi-TF confluence scoring ✓
Replaced placeholder `confluence_score = 0.5` in scorer with `_multi_tf_confluence_score()`. Generator now passes `sr_levels` to `score_setup()`.

### Update design doc to reflect eng review decisions ✓
All 10 eng review decisions incorporated into design doc.

### FeatureExtractor ✓
Built `src/quant/features/extractor.py` — transforms AnalysisResult + OHLCV into ~30 ML-ready features. NaN policy: fill with meaningful defaults + assert clean.

### LabelGenerator ✓
Built `src/quant/features/labels.py` — generates training labels from backtest trades. TP=1, SL=0, end-of-data excluded by default.

### Strict pin bar detection (book rules) ✓
Updated `pinbar.py` to match 小酱 methodology: dominant wick > 2/3, no spinning tops (secondary wick < 1/3 of dominant), wick >= 2x body, visually prominent check. Reduced 5m pin bars from 1,673 to 178.

### Trading TF skips own S/R levels ✓
5m chart only shows S/R from 1H+ (book: higher TF for key levels, trading TF for signals only).

### Multi-TF level merging ✓
Higher TF absorbs nearby lower TF levels, refines price using lower TF precision, boosts strength for confluence.

### Tabbed multi-TF chart ✓
Built `create_tabbed_chart()` with 1D/4H/1H/5m tabs, pin bar + signal toggles, TradingView-style watermark, light/dark theme toggle. All candlestick visibility issues resolved.

### Chart redesign: TradingView-style ✓
- **Root cause fix**: Plotly CDN `plotly-latest.min.js` served v1.58.5, incompatible with plotly.py 6.6.0 (v3.4.0). Pinned to `plotly-3.4.0.min.js`.
- **Candlestick rendering**: Switched from `fig.to_html()` (binary encoding) to `fig.to_json()` + `Plotly.newPlot()` for reliable rendering.
- **Per-TF bar limits**: 1D=120, 4H=120, 1H=168, 5m=500.
- **TradingView watermark**: Large faded "MES, 5m" symbol in chart center.
- **Y-axis right-side**: Clean layout with S/R TF labels inside chart area.
- **Light/dark theme toggle**: Dark (black bg, green/red candles, cyan S/R) and Light (white bg, black/white candles, teal S/R).
- **Signal toggle**: Show/hide entry diamonds + TP/SL boxes.
- **Pin bar toggle**: Works across all TFs (1D=0, 4H=10, 1H=15, 5m=178).
- **X-axis session times**: 5m uses fixed futures session times (4:00, 6:30, 9:30, 12:30, 15:00, 23:00).
- **S/R line styling**: Cyan color, ends before TF label, no overlap with y-axis.
- **Inter font**: Clean, modern typography for title/labels.

### Data: yfinance 5m pull ✓
4 weeks of MES 5m data via yfinance. Timestamps converted to US/Pacific.

### Chart: no-gap x-axis ✓
Sequential integer x-axis eliminates weekend/maintenance gaps. Date labels on ticks.

### Config updates ✓
- `min_confidence`: 0.85 → 0.60
- `min_rr_ratio`: 2.0 → 1.5 (book minimum)
- `max_sr_levels`: 12 → 10
- `min_touches` (MES/ES): 5 → 4
- Pin bar config: strict book rules in settings.yaml
