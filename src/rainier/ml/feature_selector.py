"""Feature selection with nested walk-forward CV and stability analysis.

Implements De Prado's feature importance consensus + Meinshausen & Buhlmann
stability selection, adapted for time-series with walk-forward cross-validation.

The key insight: feature selection must happen INSIDE the training fold to avoid
overfitting. Features that appear consistently across multiple folds are robust;
features that appear sporadically are noise.

Importance methods:
- MDI (Mean Decrease Impurity): XGBoost's built-in gain-based importance. Fast
  but biased toward high-cardinality / continuous features.
- MDA (Mean Decrease Accuracy): Permutation importance — shuffle one feature,
  measure accuracy drop. Slower, less biased.
- SHAP (SHapley Additive exPlanations): Most principled, slowest. Measures each
  feature's marginal contribution.

References:
- De Prado (2018) "Advances in Financial Machine Learning", Ch. 8
- Meinshausen & Buhlmann (2010) "Stability selection", JRSS-B
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score

from rainier.ml.pattern_scorer import (
    _compute_profit_factor,
    get_feature_columns,
    walk_forward_split,
)

logger = logging.getLogger(__name__)


@dataclass
class SelectionConfig:
    """Configuration for feature selection."""

    label_col: str = "label_5d"
    n_folds: int = 5
    test_ratio: float = 0.2
    min_features: int = 5
    max_features: int = 40
    stability_threshold: float = 0.6
    methods: list[str] = field(default_factory=lambda: ["mdi", "mda"])
    xgb_params: dict | None = None

    def get_xgb_params(self) -> dict:
        if self.xgb_params:
            return self.xgb_params
        return {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": 5,
            "learning_rate": 0.05,
            "n_estimators": 300,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "verbosity": 0,
        }


@dataclass
class FeatureRanking:
    """Per-feature ranking results across all folds and methods."""

    name: str
    stability: float  # fraction of folds where feature was selected (0-1)
    mean_rank: float  # average rank across folds (lower = better)
    mdi_scores: list[float] = field(default_factory=list)
    mda_scores: list[float] = field(default_factory=list)
    shap_scores: list[float] = field(default_factory=list)


@dataclass
class SelectionResult:
    """Result of feature selection pipeline."""

    selected_features: list[str]
    rankings: list[FeatureRanking]
    sweep_results: list[dict]  # {n_features, profit_factor, accuracy, f1, features}
    optimal_n: int
    stability_threshold: float
    n_folds: int
    total_features: int


def _rank_features_mdi(
    model: xgb.XGBClassifier,
    feature_cols: list[str],
) -> dict[str, float]:
    """Rank features by Mean Decrease Impurity (XGBoost gain)."""
    importance = model.feature_importances_
    return dict(zip(feature_cols, importance))


def _rank_features_mda(
    model: xgb.XGBClassifier,
    x_test: np.ndarray,
    y_test: np.ndarray,
    feature_cols: list[str],
    n_repeats: int = 5,
) -> dict[str, float]:
    """Rank features by Mean Decrease Accuracy (permutation importance)."""
    result = permutation_importance(
        model, x_test, y_test,
        n_repeats=n_repeats,
        random_state=42,
        scoring="accuracy",
    )
    return dict(zip(feature_cols, result.importances_mean))


def _rank_features_shap(
    model: xgb.XGBClassifier,
    x_test: np.ndarray,
    feature_cols: list[str],
    max_samples: int = 500,
) -> dict[str, float]:
    """Rank features by mean absolute SHAP value."""
    import shap

    sample_size = min(max_samples, len(x_test))
    idx = np.random.RandomState(42).choice(len(x_test), sample_size, replace=False)
    x_sample = x_test[idx]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x_sample)
    mean_abs = np.abs(shap_values).mean(axis=0)
    return dict(zip(feature_cols, mean_abs))


def _select_top_n(rankings: dict[str, float], n: int) -> list[str]:
    """Select top N features from an importance ranking."""
    sorted_feats = sorted(rankings.items(), key=lambda x: x[1], reverse=True)
    return [f for f, _ in sorted_feats[:n]]


def _evaluate_feature_set(
    df: pd.DataFrame,
    feature_cols: list[str],
    config: SelectionConfig,
) -> dict:
    """Evaluate a feature set using walk-forward CV. Returns metrics dict."""
    xgb_params = config.get_xgb_params()
    folds = walk_forward_split(df, n_folds=config.n_folds, test_ratio=config.test_ratio)

    fold_accuracies = []
    fold_pfs = []

    fwd_col = f"fwd_return_{config.label_col.replace('label_', '').replace('d', '')}d"

    for train_df, test_df in folds:
        x_train = train_df[feature_cols].values
        y_train = train_df[config.label_col].values.astype(int)
        x_test = test_df[feature_cols].values
        y_test = test_df[config.label_col].values.astype(int)

        model = xgb.XGBClassifier(**xgb_params)
        model.fit(x_train, y_train, eval_set=[(x_test, y_test)], verbose=False)

        y_pred = model.predict(x_test)
        fold_accuracies.append(accuracy_score(y_test, y_pred))

        if fwd_col in test_df.columns:
            pf = _compute_profit_factor(test_df, y_pred, fwd_col)
            fold_pfs.append(pf)

    return {
        "accuracy": float(np.mean(fold_accuracies)),
        "accuracy_std": float(np.std(fold_accuracies)),
        "profit_factor": (
            float(np.mean([p for p in fold_pfs if np.isfinite(p)]))
            if fold_pfs else 0.0
        ),
        "fold_accuracies": fold_accuracies,
    }


def select_features(
    parquet_path: Path,
    config: SelectionConfig | None = None,
    output_path: Path | None = None,
) -> SelectionResult:
    """Run nested walk-forward feature selection.

    Outer loop: walk-forward folds for honest evaluation.
    Inner loop: feature importance computed on training data only.

    Features are ranked by stability (% of folds selected) and consensus
    across multiple importance methods.

    Args:
        parquet_path: Path to feature store Parquet.
        config: Selection configuration.
        output_path: Optional path to save results JSON.

    Returns:
        SelectionResult with selected features and full rankings.
    """
    config = config or SelectionConfig()
    df = pd.read_parquet(parquet_path)
    logger.info("Loaded %d rows from %s", len(df), parquet_path)

    # Drop rows without labels
    df = df.dropna(subset=[config.label_col]).reset_index(drop=True)
    all_feature_cols = get_feature_columns(df)
    logger.info("Total features: %d", len(all_feature_cols))

    # --- Phase 1: Nested walk-forward importance ---
    # Outer folds for feature selection (inner training)
    outer_folds = walk_forward_split(
        df, n_folds=config.n_folds, test_ratio=config.test_ratio,
    )
    xgb_params = config.get_xgb_params()

    # Track per-feature importance across folds and methods
    fold_rankings: list[dict[str, dict[str, float]]] = []

    for fold_idx, (train_df, test_df) in enumerate(outer_folds):
        logger.info(
            "Fold %d/%d: train=%d, test=%d",
            fold_idx + 1, len(outer_folds), len(train_df), len(test_df),
        )

        x_train = train_df[all_feature_cols].values
        y_train = train_df[config.label_col].values.astype(int)
        x_test = test_df[all_feature_cols].values
        y_test = test_df[config.label_col].values.astype(int)

        model = xgb.XGBClassifier(**xgb_params)
        model.fit(x_train, y_train, eval_set=[(x_test, y_test)], verbose=False)

        fold_result: dict[str, dict[str, float]] = {}

        if "mdi" in config.methods:
            fold_result["mdi"] = _rank_features_mdi(model, all_feature_cols)

        if "mda" in config.methods:
            fold_result["mda"] = _rank_features_mda(
                model, x_test, y_test, all_feature_cols,
            )

        if "shap" in config.methods:
            fold_result["shap"] = _rank_features_shap(
                model, x_test, all_feature_cols,
            )

        fold_rankings.append(fold_result)

    # --- Phase 2: Compute stability and consensus rankings ---
    rankings = _compute_stability_rankings(
        all_feature_cols, fold_rankings, config,
    )

    # Sort by stability desc, then mean_rank asc
    rankings.sort(key=lambda r: (-r.stability, r.mean_rank))

    # --- Phase 3: Sweep feature counts to find optimal N ---
    stable_features = [r.name for r in rankings if r.stability >= config.stability_threshold]
    logger.info(
        "Stable features (>%.0f%% of folds): %d / %d",
        config.stability_threshold * 100, len(stable_features), len(all_feature_cols),
    )

    # Order stable features by mean_rank for incremental addition
    stable_ranked = [r.name for r in rankings]  # already sorted by stability + rank
    sweep_results = _sweep_feature_counts(df, stable_ranked, config)

    # Find optimal N by best profit factor (tie-break by fewer features)
    optimal = max(
        sweep_results,
        key=lambda r: (r["profit_factor"], -r["n_features"]),
    )
    optimal_n = optimal["n_features"]
    selected = optimal["features"]

    logger.info(
        "Optimal: %d features, profit_factor=%.2f, accuracy=%.3f",
        optimal_n, optimal["profit_factor"], optimal["accuracy"],
    )

    result = SelectionResult(
        selected_features=selected,
        rankings=rankings,
        sweep_results=sweep_results,
        optimal_n=optimal_n,
        stability_threshold=config.stability_threshold,
        n_folds=config.n_folds,
        total_features=len(all_feature_cols),
    )

    if output_path:
        _save_results(result, output_path)

    return result


def _compute_stability_rankings(
    feature_cols: list[str],
    fold_rankings: list[dict[str, dict[str, float]]],
    config: SelectionConfig,
) -> list[FeatureRanking]:
    """Compute per-feature stability and consensus across folds/methods."""
    n_folds = len(fold_rankings)
    top_n_per_fold = max(config.max_features, len(feature_cols) // 2)

    feature_data: dict[str, FeatureRanking] = {
        col: FeatureRanking(name=col, stability=0.0, mean_rank=len(feature_cols))
        for col in feature_cols
    }

    # Count how often each feature appears in top-N across folds
    selection_counts: dict[str, int] = {col: 0 for col in feature_cols}
    all_ranks: dict[str, list[float]] = {col: [] for col in feature_cols}

    for fold_result in fold_rankings:
        # Consensus: average rank across methods in this fold
        fold_consensus: dict[str, float] = {col: 0.0 for col in feature_cols}
        n_methods = 0

        for method, scores in fold_result.items():
            n_methods += 1
            # Convert scores to ranks (1 = best)
            sorted_feats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            for rank, (feat, _score) in enumerate(sorted_feats, 1):
                fold_consensus[feat] += rank

                # Track per-method scores
                fr = feature_data[feat]
                if method == "mdi":
                    fr.mdi_scores.append(_score)
                elif method == "mda":
                    fr.mda_scores.append(_score)
                elif method == "shap":
                    fr.shap_scores.append(_score)

        # Average rank across methods
        for feat in feature_cols:
            avg_rank = fold_consensus[feat] / max(n_methods, 1)
            all_ranks[feat].append(avg_rank)

            # Was this feature in top-N for this fold?
            if avg_rank <= top_n_per_fold:
                selection_counts[feat] += 1

    # Compute final stability and mean rank
    for col in feature_cols:
        fr = feature_data[col]
        fr.stability = selection_counts[col] / max(n_folds, 1)
        fr.mean_rank = float(np.mean(all_ranks[col])) if all_ranks[col] else len(feature_cols)

    return list(feature_data.values())


def _sweep_feature_counts(
    df: pd.DataFrame,
    ranked_features: list[str],
    config: SelectionConfig,
) -> list[dict]:
    """Evaluate model performance at different feature counts.

    Tests feature sets of increasing size using walk-forward CV.
    """
    results = []
    step = max(1, (config.max_features - config.min_features) // 7)
    upper = min(config.max_features + 1, len(ranked_features) + 1)
    counts = list(range(config.min_features, upper, step))

    # Always include the max
    if counts and counts[-1] != min(config.max_features, len(ranked_features)):
        counts.append(min(config.max_features, len(ranked_features)))

    for n in counts:
        if n > len(ranked_features):
            break

        features = ranked_features[:n]
        logger.info("Evaluating with %d features...", n)

        metrics = _evaluate_feature_set(df, features, config)
        results.append({
            "n_features": n,
            "features": features,
            "accuracy": metrics["accuracy"],
            "accuracy_std": metrics["accuracy_std"],
            "profit_factor": metrics["profit_factor"],
        })
        logger.info(
            "  n=%d: accuracy=%.3f (+-%.3f), pf=%.2f",
            n, metrics["accuracy"], metrics["accuracy_std"], metrics["profit_factor"],
        )

    return results


def _save_results(result: SelectionResult, path: Path) -> None:
    """Save selection results to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "selected_features": result.selected_features,
        "optimal_n": result.optimal_n,
        "stability_threshold": result.stability_threshold,
        "n_folds": result.n_folds,
        "total_features": result.total_features,
        "rankings": [
            {
                "name": r.name,
                "stability": r.stability,
                "mean_rank": round(r.mean_rank, 2),
                "mdi_mean": round(float(np.mean(r.mdi_scores)), 6) if r.mdi_scores else None,
                "mda_mean": round(float(np.mean(r.mda_scores)), 6) if r.mda_scores else None,
                "shap_mean": round(float(np.mean(r.shap_scores)), 6) if r.shap_scores else None,
            }
            for r in result.rankings
        ],
        "sweep": [
            {
                "n_features": s["n_features"],
                "accuracy": round(s["accuracy"], 4),
                "accuracy_std": round(s["accuracy_std"], 4),
                "profit_factor": round(s["profit_factor"], 4),
                "features": s["features"],
            }
            for s in result.sweep_results
        ],
    }

    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Results saved to %s", path)
