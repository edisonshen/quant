# AI-Driven Adaptive Trading — Research References

Compiled 2026-03-21 during design phase of the hybrid ensemble trading system.

---

## Multi-Agent LLM Trading Frameworks

- [ATLAS: Adaptive Trading with LLM AgentS](https://arxiv.org/abs/2510.15949) — Multi-agent framework with dynamic prompt optimization (Adaptive-OPRO). Addresses how to adapt LLM instructions when market rewards arrive late and noisy. Oct 2025.
- [TradingAgents: Multi-Agent LLM Framework](https://github.com/TauricResearch/TradingAgents) — Open-source framework mirroring real trading desks: fundamental analysts, sentiment experts, technical analysts, risk management. Active GitHub repo.
- [TradingAgents Paper](https://arxiv.org/pdf/2412.20138) — Academic paper behind the TradingAgents framework.

## LLM + Reinforcement Learning

- [RLMF: Reinforcement Learning from Market Feedback](https://openreview.net/forum?id=y3W1TVuJii) — Aligns LLMs using market returns as reward signals (like RLHF but for finance). Llama-2 7B improved 15% over GPT-4o. Model-agnostic, plug-and-play.
- [Advancing Algorithmic Trading with LLMs + RL](https://openreview.net/forum?id=w7BGq6ozOL) — Stock-Evol-Instruct approach bridging LLMs and RL for algorithmic trading.
- [Financial Trading with LLM Reasoning via RL](https://arxiv.org/pdf/2509.11420) — RL-based approach for LLM-driven trading decisions.
- [Alpha-R1: Alpha Screening with LLM Reasoning via RL](https://arxiv.org/html/2512.23515v1) — Reinforcement learning for alpha factor screening.

## Market Regime Detection

- [Market Regime Detection with HMM (QuantStart)](https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/) — Practical HMM implementation for regime classification with Python code.
- [Regime-Adaptive Trading with HMM + Random Forest (QuantInsti)](https://blog.quantinsti.com/regime-adaptive-trading-python/) — Step-by-step Python guide: HMM detects regime, then train specialist Random Forest per regime.
- [Multi-Model Ensemble-HMM for Regime Shift Detection](https://www.aimspress.com/article/id/69045d2fba35de34708adb5d) — Tree-based ensemble + HMM for detecting bull/bear/neutral transitions. Oct 2025.
- [HMM + RL for Portfolio Management (IEEE 2025)](https://www.cloud-conf.net/datasec/2025/proceedings/pdfs/IDS2025-3SVVEmiJ6JbFRviTl4Otnv/966100a067/966100a067.pdf) — Combining regime detection with reinforcement learning for portfolio management.
- [HMM Market Regimes (LuxAlgo)](https://www.luxalgo.com/library/indicator/hidden-markov-model-market-regimes/) — TradingView indicator implementation of HMM regimes.
- [Decoding Market Regimes (State Street 2025)](https://www.ssga.com/library-content/assets/pdf/global/pc/2025/decoding-market-regimes-with-machine-learning.pdf) — Institutional research: ML approach using 23 datasets identified 4 distinct regimes over 30 years.

## Traditional ML for Trading

- [Feature Engineering for ML Trading with Decision Trees](https://thesai.org/Publications/ViewPaper?Volume=16&Issue=12&Code=IJACSA&SerialNo=68) — Feature engineering best practices for Random Forest, XGBoost, Gradient Boosting.
- [ML Models for S&P 500 Trading (BSIC)](https://bsic.it/machine-learning-models-for-sp-500-trading-a-comparative-analysis-of-random-forest-xgboost-and-regression-techniques/) — Comparative analysis of RF, XGBoost, regression for trading.
- [Machine Learning for Trading (GitHub)](https://github.com/stefan-jansen/machine-learning-for-trading) — Code repository for "Machine Learning for Algorithmic Trading" 2nd edition. Comprehensive reference.
- [Regime Detection with HMM + SVM (GitHub)](https://github.com/theo-dim/regime_detection_ml) — Implementation of regime detection using HMM and SVM.

## Meta-Learning and Adaptive Strategies

- [Meta-Learning for Online Portfolio Selection](https://arxiv.org/html/2505.03659v2) — MAML for rapid strategy adaptation to unknown market environments.
- [Adaptive Event-Driven Labeling with Meta-Learning](https://www.mdpi.com/2076-3417/15/24/13204) — Multi-scale temporal analysis + causal inference + MAML for adaptive parameter optimization.
- [Evolution of RL in Quantitative Finance (Survey)](https://arxiv.org/pdf/2408.10932) — Comprehensive survey of RL approaches. Hybrid adoption grew from 15% (2020) to 42% (2025).

## Surveys and Overviews

- [LLMs in Equity Markets (Frontiers 2025)](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1608365/full) — Comprehensive survey: prompting, fine-tuning, multi-agent, RL, custom architectures.
- [From Deep Learning to LLMs: AI in Quantitative Investment](https://arxiv.org/html/2503.21422v1) — Survey covering evolution from DL to LLM-based quant strategies.
- [AI Trading Agents vs Expert Advisors (2026 Guide)](https://tradelikemaster.com/blog/ai-trading-agents-vs-eas) — Practical comparison of AI agents vs traditional rule-based EAs.

## Practical Implementations

- [Full-Stack AI Trading App with LLMs (Medium, Jan 2026)](https://medium.com/@ttarler/i-built-a-full-stack-ai-trading-app-with-llms-52f9cc235321) — Real-world implementation: ML models for morning watchlist, RL for execution decisions.
- [Automate Strategy Finding with LLM in Quant Investment](https://ideas.repec.org/p/arx/papers/2409.06289.html) — Using LLMs to automatically discover quantitative strategies.
- [FinRLlama: LLM-Engineered Signals (FinRL Contest 2024)](https://arxiv.org/abs/2502.01992) — Competition-winning approach combining LLMs with RL.
- [Market Regime Detector (GitHub)](https://github.com/alexistan17/market-regime-detector) — Open-source tool to detect bull/bear/sideways regimes and adapt strategies.
