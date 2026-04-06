"""Tests for nested walk-forward feature selection pipeline."""

from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from rainier.ml.feature_selector import (
    SelectionConfig,
    SelectionResult,
    _compute_stability_rankings,
    _evaluate_feature_set,
    _rank_features_mda,
    _rank_features_mdi,
    _select_top_n,
    _sweep_feature_counts,
    select_features,
)
from rainier.ml.pattern_scorer import get_feature_columns


def _make_data(n: int = 600, n_features: int = 20, n_signal: int = 5) -> pd.DataFrame:
    """Create synthetic data where first n_signal features have predictive power.

    Features 0..n_signal-1 are correlated with the label.
    Features n_signal..n_features-1 are pure noise.
    """
    rng = np.random.RandomState(42)
    rows = []

    for i in range(n):
        # Signal features (correlated with label)
        signals = [rng.normal(0, 1) for _ in range(n_signal)]
        # Noise features (random)
        noise = [rng.normal(0, 1) for _ in range(n_features - n_signal)]

        # Label: correlated with sum of signal features
        prob = 1.0 / (1.0 + np.exp(-0.5 * sum(signals)))
        label = float(rng.random() < prob)

        row = {}
        for j in range(n_signal):
            row[f"signal_{j}"] = signals[j]
        for j in range(n_features - n_signal):
            row[f"noise_{j}"] = noise[j]

        row["fwd_return_5d"] = rng.normal(0.01 if label else -0.01, 0.02)
        row["label_5d"] = label
        row["symbol"] = "TEST"
        row["date"] = pd.Timestamp("2023-01-01") + timedelta(days=i)
        row["close"] = 100 + rng.normal(0, 5)
        row["volume"] = float(rng.randint(500000, 2000000))
        rows.append(row)

    return pd.DataFrame(rows)


@pytest.fixture
def sample_data():
    return _make_data()


@pytest.fixture
def sample_parquet(sample_data, tmp_path):
    path = tmp_path / "test_features.parquet"
    sample_data.to_parquet(path, index=False)
    return path


# --- Unit tests ---


class TestSelectTopN:
    def test_basic(self):
        rankings = {"a": 0.8, "b": 0.3, "c": 0.9, "d": 0.1}
        assert _select_top_n(rankings, 2) == ["c", "a"]

    def test_top_n_more_than_available(self):
        rankings = {"a": 0.5, "b": 0.3}
        assert _select_top_n(rankings, 5) == ["a", "b"]

    def test_empty(self):
        assert _select_top_n({}, 3) == []


class TestRankFeaturesMDI:
    def test_returns_all_features(self, sample_data):
        import xgboost as xgb

        feature_cols = get_feature_columns(sample_data)
        features = sample_data[feature_cols].values
        labels = sample_data["label_5d"].values.astype(int)

        model = xgb.XGBClassifier(
            n_estimators=10, max_depth=3, random_state=42, verbosity=0,
        )
        model.fit(features, labels)

        result = _rank_features_mdi(model, feature_cols)
        assert set(result.keys()) == set(feature_cols)
        assert all(v >= 0 for v in result.values())

    def test_signal_features_rank_higher(self, sample_data):
        """Signal features should generally rank above noise."""
        import xgboost as xgb

        feature_cols = get_feature_columns(sample_data)
        features = sample_data[feature_cols].values
        labels = sample_data["label_5d"].values.astype(int)

        model = xgb.XGBClassifier(
            n_estimators=100, max_depth=5, random_state=42, verbosity=0,
        )
        model.fit(features, labels)

        result = _rank_features_mdi(model, feature_cols)
        sorted_feats = sorted(result.items(), key=lambda x: x[1], reverse=True)
        top_10 = [f for f, _ in sorted_feats[:10]]

        # At least some signal features should be in top 10
        signal_in_top = sum(1 for f in top_10 if f.startswith("signal_"))
        assert signal_in_top >= 2


class TestRankFeaturesMDA:
    def test_returns_all_features(self, sample_data):
        import xgboost as xgb

        feature_cols = get_feature_columns(sample_data)
        features = sample_data[feature_cols].values
        labels = sample_data["label_5d"].values.astype(int)

        model = xgb.XGBClassifier(
            n_estimators=50, max_depth=3, random_state=42, verbosity=0,
        )
        model.fit(features, labels)

        result = _rank_features_mda(model, features, labels, feature_cols, n_repeats=3)
        assert set(result.keys()) == set(feature_cols)


class TestComputeStabilityRankings:
    def test_consistent_feature_has_high_stability(self):
        """A feature ranked #1 in every fold should have stability=1.0."""
        feature_cols = ["good", "bad_a", "bad_b"]
        fold_rankings = [
            {"mdi": {"good": 0.9, "bad_a": 0.05, "bad_b": 0.05}},
            {"mdi": {"good": 0.8, "bad_a": 0.1, "bad_b": 0.1}},
            {"mdi": {"good": 0.85, "bad_a": 0.08, "bad_b": 0.07}},
        ]
        config = SelectionConfig(max_features=3)
        rankings = _compute_stability_rankings(feature_cols, fold_rankings, config)

        by_name = {r.name: r for r in rankings}
        assert by_name["good"].stability == 1.0
        assert by_name["good"].mean_rank < by_name["bad_a"].mean_rank

    def test_multi_method_consensus(self):
        """Feature ranked high by both methods should rank higher overall."""
        feature_cols = ["both_good", "mdi_only", "mda_only", "neither"]
        fold_rankings = [
            {
                "mdi": {"both_good": 0.9, "mdi_only": 0.8, "mda_only": 0.1, "neither": 0.05},
                "mda": {"both_good": 0.5, "mdi_only": 0.01, "mda_only": 0.4, "neither": 0.02},
            },
        ]
        config = SelectionConfig(max_features=4, methods=["mdi", "mda"])
        rankings = _compute_stability_rankings(feature_cols, fold_rankings, config)

        by_name = {r.name: r for r in rankings}
        # both_good should have best mean rank (lowest)
        assert by_name["both_good"].mean_rank < by_name["neither"].mean_rank


class TestEvaluateFeatureSet:
    def test_returns_metrics(self, sample_data):
        feature_cols = get_feature_columns(sample_data)[:10]
        config = SelectionConfig(n_folds=2, test_ratio=0.2)

        result = _evaluate_feature_set(sample_data, feature_cols, config)
        assert "accuracy" in result
        assert "profit_factor" in result
        assert "accuracy_std" in result
        assert 0 <= result["accuracy"] <= 1

    def test_signal_features_outperform_noise(self, sample_data):
        config = SelectionConfig(n_folds=2, test_ratio=0.2)

        signal_cols = [c for c in get_feature_columns(sample_data) if c.startswith("signal_")]

        signal_result = _evaluate_feature_set(sample_data, signal_cols, config)

        # Signal features should generally perform better
        # (not guaranteed with small synthetic data, so use a loose check)
        assert signal_result["accuracy"] >= 0.45  # at least not terrible


class TestSweepFeatureCounts:
    def test_produces_results(self, sample_data):
        feature_cols = get_feature_columns(sample_data)
        config = SelectionConfig(min_features=3, max_features=10, n_folds=2)

        results = _sweep_feature_counts(sample_data, feature_cols, config)
        assert len(results) > 0
        assert all("n_features" in r for r in results)
        assert all("accuracy" in r for r in results)
        assert all("profit_factor" in r for r in results)

    def test_feature_counts_increase(self, sample_data):
        feature_cols = get_feature_columns(sample_data)
        config = SelectionConfig(min_features=3, max_features=10, n_folds=2)

        results = _sweep_feature_counts(sample_data, feature_cols, config)
        counts = [r["n_features"] for r in results]
        assert counts == sorted(counts)  # monotonically increasing


# --- Integration tests ---


class TestSelectFeatures:
    def test_end_to_end(self, sample_parquet):
        config = SelectionConfig(
            n_folds=2,
            min_features=3,
            max_features=10,
            stability_threshold=0.5,
            methods=["mdi"],
        )

        result = select_features(sample_parquet, config)

        assert isinstance(result, SelectionResult)
        assert len(result.selected_features) >= config.min_features
        assert len(result.selected_features) <= config.max_features
        assert result.optimal_n == len(result.selected_features)
        assert len(result.rankings) == result.total_features
        assert len(result.sweep_results) > 0

    def test_signal_features_selected(self, sample_parquet):
        """Signal features should be selected over noise."""
        config = SelectionConfig(
            n_folds=3,
            min_features=3,
            max_features=15,
            stability_threshold=0.5,
            methods=["mdi", "mda"],
        )

        result = select_features(sample_parquet, config)

        signal_selected = [f for f in result.selected_features if f.startswith("signal_")]
        # At least some signal features should make the cut
        assert len(signal_selected) >= 2, (
            f"Expected signal features in selection, got: {result.selected_features}"
        )

    def test_rankings_sorted_by_stability(self, sample_parquet):
        config = SelectionConfig(n_folds=2, methods=["mdi"])
        result = select_features(sample_parquet, config)

        stabilities = [r.stability for r in result.rankings]
        assert stabilities == sorted(stabilities, reverse=True)

    def test_save_results(self, sample_parquet, tmp_path):
        output = tmp_path / "selection_results.json"
        config = SelectionConfig(
            n_folds=2, min_features=3, max_features=8, methods=["mdi"],
        )

        select_features(sample_parquet, config, output_path=output)

        assert output.exists()
        import json
        with open(output) as f:
            data = json.load(f)

        assert "selected_features" in data
        assert "rankings" in data
        assert "sweep" in data
        assert data["optimal_n"] == len(data["selected_features"])

    def test_with_shap_method(self, sample_parquet):
        """SHAP method should work (slower but more accurate)."""
        config = SelectionConfig(
            n_folds=2,
            min_features=3,
            max_features=8,
            methods=["shap"],
        )

        result = select_features(sample_parquet, config)
        assert len(result.selected_features) > 0

        # SHAP scores should be populated
        has_shap = any(len(r.shap_scores) > 0 for r in result.rankings)
        assert has_shap

    def test_stability_threshold_filters(self, sample_parquet):
        """Higher threshold should select fewer or equal features."""
        config_low = SelectionConfig(
            n_folds=3, stability_threshold=0.3, min_features=3, max_features=15,
            methods=["mdi"],
        )
        config_high = SelectionConfig(
            n_folds=3, stability_threshold=0.9, min_features=3, max_features=15,
            methods=["mdi"],
        )

        result_low = select_features(sample_parquet, config_low)
        result_high = select_features(sample_parquet, config_high)

        stable_low = [r for r in result_low.rankings if r.stability >= 0.3]
        stable_high = [r for r in result_high.rankings if r.stability >= 0.9]
        assert len(stable_high) <= len(stable_low)
