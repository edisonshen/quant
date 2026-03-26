# Research: Forward-Looking Chart Pattern Detection

Compiled 2026-03-25. Papers and repos relevant to Rainier's 蔡森 pattern detection pipeline.

---

## 1. Forming/Partial Pattern Detection (Pre-Breakout)

### From Patterns to Predictions: A Shapelet-Based Framework for Directional Forecasting in Noisy Financial Markets
- **Year:** 2025
- **Key Finding:** Uses **partial input sequences** (incomplete patterns) to predict what comes next. Integrates DTW-based unsupervised clustering (SIMPC) with a shapelet classifier (JISC-Net). Ranked #1-2 across 11/12 metrics on BTC + S&P 500.
- **URL:** https://arxiv.org/abs/2509.15040
- **Relevance:** Most directly applicable — detects forming patterns and predicts completion. Code available on GitHub.

### Using a Deep Learning Model to Simulate Human Stock Traders' Methods of Chart Analysis
- **Authors:** Sungwoo Kang, Jong-Kook Kim
- **Year:** 2023
- **Key Finding:** ResNet on 600-day chart windows predicts if 10% rise/fall happens within D days — mimicking how humans read charts before confirmation. Korea: 75.36% return, Sharpe 1.57; US: 27.17% return, Sharpe 0.61.
- **URL:** https://arxiv.org/abs/2304.14870
- **Relevance:** Forward-looking by design — trained to predict future moves from current chart appearance.

### Market Movement Prediction Using Chart Patterns and Attention Mechanism
- **Year:** 2024
- **Key Finding:** Groups candles into "waves" + Transformer attention to predict **next wave** characteristics (price movement range). 19.8% return vs 12.5% MACD baseline.
- **URL:** https://link.springer.com/article/10.1007/s44257-023-00007-6
- **Relevance:** Wave-based decomposition detects pattern formation in progress.

---

## 2. Actionability — Is This Pattern Still Tradeable?

### Identifying Trades Using Technical Analysis and ML/DL Models
- **Authors:** Aayush Shah et al.
- **Year:** 2023
- **Key Finding:** Two-layer approach: first detect the pattern, then ML classifies whether the trade will be **profitable or lossy**. Directly evaluates actionability.
- **URL:** https://arxiv.org/abs/2304.09936
- **Relevance:** Exactly the "should I enter this setup?" problem. Natural evolution for Rainier Phase 5.

### Improving Stock Trading Decisions Based on Pattern Recognition Using Machine Learning (PRML)
- **Authors:** Yaohu Lin, Shancun Liu, Haijun Yang, Harris Wu, Bingbing Jiang
- **Year:** 2021
- **Key Finding:** 4 ML methods × 11 feature types across all candlestick pattern combinations. **2-day patterns predicting 1 day ahead: 36.73% annual return, Sharpe 0.81, IR 2.37** — even after 0.2% transaction costs.
- **URL:** https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0255558
- **Relevance:** Quantifies which pattern lengths are most actionable (2-day beats longer).

### Can Machine Learning Make Technical Analysis Work?
- **Authors:** Andrea Rigamonti
- **Year:** 2024
- **Key Finding:** Tree-based methods using technical indicators as predictors for daily returns. Rigorous evaluation of whether ML can rescue traditional TA's poor standalone performance.
- **URL:** https://link.springer.com/article/10.1007/s11408-024-00451-8

---

## 3. Real-Time / Near-Real-Time Detection

### Candlestick Pattern Recognition Using Modified YOLOv8
- **Year:** 2024
- **Key Finding:** Modified YOLOv8 achieves **mAP@50 of 86.1%** detecting H&S, Reverse H&S, Double Top, Double Bottom in real-time from chart images.
- **URL:** https://ieeexplore.ieee.org/document/10545693/
- **Relevance:** YOLO = inherently real-time. Could process live chart screenshots.

### Stock Chart Pattern Recognition with Deep Learning
- **Authors:** Marc Velay, Fabrice Daniel
- **Year:** 2018
- **Key Finding:** Foundational paper. CNN beats LSTM for chart pattern classification. Established charts-as-images approach.
- **URL:** https://arxiv.org/abs/1808.00418

### Enhancing Market Trend Prediction Using CNNs on Japanese Candlestick Patterns
- **Year:** 2025
- **Key Finding:** CNN + candlestick patterns improves prediction, peaks ~0.7 accuracy.
- **URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11935771/

---

## 4. Volume-Price Analysis + Pattern Detection

### Interpretable Trading Pattern Designed for ML Applications (Volume-Centred Range Bars)
- **Authors:** Sokolovsky, Arnaboldi, Bacardit, Gross
- **Year:** 2023
- **Key Finding:** Volume-price-based representation (VCRB) **outperforms price-only** for pattern classification, especially on liquid instruments. Tree-based models + SHAP for interpretability. Code on Code Ocean.
- **URL:** https://www.sciencedirect.com/science/article/pii/S2666827023000014
- **Relevance:** Directly relevant to combining QU100 money flow with pattern detection. 蔡森's "量是因，价是果" validated academically.

### Encoding Candlesticks as Images for Pattern Classification Using CNNs (GAF-CNN)
- **Authors:** Chen J.H., Tsai Y.C.
- **Year:** 2020
- **Key Finding:** Gramian Angular Field encodes time series as images → CNN classifies 8 candlestick patterns with **90.7% accuracy**, beating LSTM.
- **URL:** https://jfin-swufe.springeropen.com/articles/10.1186/s40854-020-00187-0
- **Relevance:** GAF preserves temporal relationships. Could add volume as additional image channel.

### Candlestick Patterns Recognition Using CNN-LSTM Model
- **Year:** 2023
- **Key Finding:** GAF-CNN for pattern recognition (82.7%) + LSTM for price prediction (MAPE 0.97%). Combined: 82.7% profitable trade accuracy vs 60% CNN alone.
- **URL:** https://ejurnal.seminar-id.com/index.php/josyc/article/view/2133
- **Relevance:** Combining pattern recognition with price prediction improves entry timing.

---

## 5. Asian Technical Analysis / 蔡森 Methodology

No academic papers found referencing 蔡森's "多空转折一手抓" methodology specifically. The book's 12 chart patterns (W底, M头, 破底翻, 假突破, etc.) overlap with patterns studied in the papers above, but the specific synthesis — multi-timeframe confluence + 量价分析 + 涨跌幅满足 targets — has not been formally studied.

**Gap / Opportunity:** Rainier's implementation could produce the first empirical validation of this methodology on US stock data. After 3-6 months of screening, the data collected (pattern signals + outcomes) would be publishable.

---

## Open-Source Implementations

### Pre-Breakout / Forward-Looking

| Repo | Description | Relevance |
|------|-------------|-----------|
| [BennyThadikaran/stock-pattern](https://github.com/BennyThadikaran/stock-pattern) | Detects patterns **prior to breakout** at the last leg. No buy/sell signals. | Closest to forming-pattern detection. |
| [pkjmesra/PKScreener](https://github.com/pkjmesra/PKScreener) | Finds stocks **consolidating and may breakout**. Pre-breakout screening. | Screener designed for exactly our use case. |

### ML/DL-Based Detection

| Repo | Description | Relevance |
|------|-------------|-----------|
| [Omar-Karimov/ChartScanAI](https://github.com/Omar-Karimov/ChartScanAI) | YOLOv8 real-time chart pattern detection. Buy/Sell signals. | Real-time detection with deep learning. |
| [foduucom/stockmarket-pattern-detection-yolov8](https://huggingface.co/foduucom/stockmarket-pattern-detection-yolov8) | Pre-trained YOLOv8 model, ready to use. | Plug-and-play CNN detection. |
| [white07S/TradingPatternScanner](https://github.com/white07S/TradingPatternScanner) | Kalman Filter + Wavelet Denoising for noise-reduced detection. | Could detect forming patterns via evolving state estimates. |

### Rule-Based Detection

| Repo | Description | Relevance |
|------|-------------|-----------|
| [keithorange/PatternPy](https://github.com/keithorange/PatternPy) | Fast Pandas/NumPy pattern recognition (H&S, Tops, Bottoms, S/R). | Good baseline, fast enough for real-time. |
| [zeta-zetra/chart_patterns](https://github.com/zeta-zetra/chart_patterns) | Ascending triangles, H&S, flags, standard patterns. | Reference implementations. |

---

## Key Takeaways for Rainier Roadmap

1. **Short-term (now):** The rule-based actionability filter we built (forming patterns within 5% of breakout, confirmed within 10 bars) is a solid v1 — matches the approach in BennyThadikaran/stock-pattern.

2. **Phase 5 — LLM Vision (already planned):** Send chart PNG to Claude Sonnet for pattern validation. Papers #7 and #8 show CNN/YOLO can achieve 86%+ accuracy on chart images — LLM vision should be comparable or better.

3. **Phase 6 — ML Actionability Classifier:** Build a second-stage model (Shah et al., 2023) that takes a detected pattern and predicts if the trade will be profitable. Train on 3-6 months of Rainier screening data + actual outcomes.

4. **Phase 7 — Shapelet-Based Forming Detection:** Replace rule-based forming detection with the shapelet approach (2025 paper) that uses partial sequences to predict pattern completion probability.

5. **Volume Integration:** The VCRB paper (Sokolovsky, 2023) validates 蔡森's "量是因，价是果" — volume-based features should be weighted heavily. Our current volume_confirmed flag is a crude version; ML features from volume profile would improve accuracy.
