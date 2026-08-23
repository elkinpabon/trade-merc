import json
import math
from datetime import timedelta

import numpy as np

from app.extensions import db
from app.models import ModelVersion, StrategyEvaluation
from app.utils.helpers import generate_uuid, utc_now


FEATURE_NAMES = [
    'score', 'trend_score', 'momentum_score', 'volume_score', 'volatility_score',
    'prediction_score', 'regime_score', 'rsi', 'adx', 'macd_histogram',
    'vol_ratio', 'lr_r_squared', 'lr_slope_pct',
]


class ModelService:
    """Small, persisted logistic model suitable for scheduled serverless jobs."""

    @staticmethod
    def ensure_baseline() -> ModelVersion:
        baseline = ModelVersion.query.filter_by(model_name='multifactor', version='baseline-v1').first()
        if baseline:
            return baseline
        baseline = ModelVersion(
            id=generate_uuid(), model_name='multifactor', version='baseline-v1', status='active',
            algorithm='heuristic_baseline', feature_schema_json=json.dumps(FEATURE_NAMES),
            parameters_json=json.dumps({'cost_pct': 0.002, 'entry_probability': 0.60}),
            metrics_json=json.dumps({'source': 'initial baseline'}), created_at=utc_now(),
        )
        db.session.add(baseline)
        db.session.commit()
        return baseline

    @staticmethod
    def active_model() -> ModelVersion:
        return ModelVersion.query.filter_by(status='active').order_by(ModelVersion.created_at.desc()).first() or ModelService.ensure_baseline()

    @staticmethod
    def baseline_probability(features: dict) -> float:
        return min(0.95, max(0.05, (float(features.get('score', 0)) / 100.0) * 0.85 + 0.10))

    @staticmethod
    def predict(features: dict, model: ModelVersion | None = None) -> float:
        model = model or ModelService.active_model()
        if model.algorithm != 'logistic_regression':
            return ModelService.baseline_probability(features)
        parameters = model.parameters()
        means = parameters.get('means', {})
        scales = parameters.get('scales', {})
        coefficients = parameters.get('coefficients', {})
        value = float(parameters.get('intercept', 0.0))
        for name in FEATURE_NAMES:
            scale = float(scales.get(name, 1.0)) or 1.0
            value += float(coefficients.get(name, 0.0)) * ((float(features.get(name, 0.0)) - float(means.get(name, 0.0))) / scale)
        return float(1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value)))))

    @staticmethod
    def train_if_due(minimum_samples: int = 200, minimum_days: int = 7) -> ModelVersion | None:
        active = ModelService.active_model()
        if active.algorithm == 'logistic_regression' and active.created_at > utc_now() - timedelta(days=minimum_days):
            return None
        evaluations = StrategyEvaluation.query.filter_by(label_status='RESOLVED').order_by(StrategyEvaluation.decision_at.asc()).all()
        if len(evaluations) < minimum_samples:
            return None

        x = np.array([[float(e.features().get(name, 0.0)) for name in FEATURE_NAMES] for e in evaluations], dtype=float)
        y = np.array([1.0 if e.label == 'TP_HIT' else 0.0 for e in evaluations], dtype=float)
        split = max(1, int(len(evaluations) * 0.8))
        if len(np.unique(y[:split])) < 2:
            return None
        means = x[:split].mean(axis=0)
        scales = x[:split].std(axis=0)
        scales[scales == 0] = 1.0
        x_train = (x[:split] - means) / scales
        weights = np.zeros(len(FEATURE_NAMES), dtype=float)
        intercept = 0.0
        for _ in range(400):
            logits = np.clip(x_train @ weights + intercept, -30, 30)
            probabilities = 1.0 / (1.0 + np.exp(-logits))
            error = probabilities - y[:split]
            weights -= 0.08 * ((x_train.T @ error) / len(x_train) + 0.001 * weights)
            intercept -= 0.08 * float(error.mean())

        validation_x = (x[split:] - means) / scales
        validation_y = y[split:]
        validation_p = 1.0 / (1.0 + np.exp(-np.clip(validation_x @ weights + intercept, -30, 30)))
        brier = float(np.mean((validation_p - validation_y) ** 2)) if len(validation_y) else 1.0
        log_loss = float(-np.mean(validation_y * np.log(np.clip(validation_p, 1e-9, 1)) + (1 - validation_y) * np.log(np.clip(1 - validation_p, 1e-9, 1)))) if len(validation_y) else 1.0
        if brier > 0.25:
            return None

        candidate = ModelVersion(
            id=generate_uuid(), model_name='multifactor', version=f"logistic-{utc_now().strftime('%Y%m%d%H%M%S')}",
            status='candidate', algorithm='logistic_regression', feature_schema_json=json.dumps(FEATURE_NAMES),
            parameters_json=json.dumps({
                'means': dict(zip(FEATURE_NAMES, means.tolist())),
                'scales': dict(zip(FEATURE_NAMES, scales.tolist())),
                'coefficients': dict(zip(FEATURE_NAMES, weights.tolist())),
                'intercept': float(intercept), 'cost_pct': 0.002,
            }),
            metrics_json=json.dumps({'samples': len(evaluations), 'validation_samples': len(validation_y), 'brier_score': brier, 'log_loss': log_loss}),
            training_window_start=evaluations[0].decision_at, training_window_end=evaluations[-1].decision_at,
            created_at=utc_now(),
        )
        db.session.add(candidate)
        # Promote only a validated candidate; previous versions remain auditable.
        if len(evaluations) >= 500 and brier <= 0.22:
            ModelVersion.query.filter_by(status='active').update({'status': 'retired'})
            candidate.status = 'active'
        db.session.commit()
        return candidate
