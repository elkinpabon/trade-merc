import json
from datetime import timedelta

from sqlalchemy import text

from app.extensions import db
from app.models import Candle, StrategyEvaluation
from app.services.model_service import ModelService
from app.utils.helpers import generate_uuid, utc_now


class EvaluationService:
    horizon_candles = 12
    total_cost_pct = 0.002

    @staticmethod
    def build_features(score_data: dict) -> dict:
        indicators = score_data['indicators']
        prediction = score_data['ml_prediction']
        return {
            'score': score_data['total_score'], 'trend_score': score_data['trend_score'],
            'momentum_score': score_data['momentum_score'], 'volume_score': score_data['volume_score'],
            'volatility_score': score_data['volatility_score'], 'prediction_score': score_data['prediction_score'],
            'regime_score': score_data['regime_score'], 'rsi': indicators['rsi'], 'adx': indicators['adx'],
            'macd_histogram': indicators['macd_histogram'], 'vol_ratio': indicators['vol_ratio'],
            'lr_r_squared': prediction['lr_r_squared'], 'lr_slope_pct': prediction['lr_slope_pct'],
            'market_regime': prediction['market_regime'], 'bullish_cross': indicators['bullish_cross'],
            'bearish_cross': indicators['bearish_cross'],
        }

    @classmethod
    def record(cls, config, bot_run_id: str, symbol: str, timeframe: str, latest, score_data: dict,
               commit: bool = True, check_existing: bool = True, model=None) -> StrategyEvaluation:
        model = model or ModelService.active_model()
        if config.model_version_id != model.id:
            config.model_version_id = model.id
            db.session.commit()
        candle_ts = int(latest['timestamp'])
        if check_existing:
            existing = StrategyEvaluation.query.filter_by(symbol=symbol, timeframe=timeframe, decision_candle_ts=candle_ts, model_version_id=model.id).first()
            if existing:
                return existing
        features = cls.build_features(score_data)
        probability = ModelService.predict(features, model)
        price = float(latest['close'])
        tp_pct = float(config.take_profit_pct) / 100.0
        sl_pct = float(config.stop_loss_pct) / 100.0
        expected_value = probability * tp_pct - (1.0 - probability) * sl_pct - cls.total_cost_pct
        entry_eligible = (
            probability >= 0.60 and expected_value >= 0.0015 and
            price > float(latest.get('bb_middle', price)) and float(latest.get('vol_ratio', 1.0)) >= 0.8 and
            float(latest.get('adx', 0.0)) >= 18 and score_data['ml_prediction']['lr_direction'] >= 0 and
            score_data['ml_prediction']['market_regime'] != 'TRENDING_DOWN'
        )
        evaluation = StrategyEvaluation(
            id=generate_uuid(), model_version_id=model.id, bot_run_id=bot_run_id, symbol=symbol, timeframe=timeframe,
            decision_candle_ts=candle_ts, decision_at=latest['datetime'].to_pydatetime(), side='LONG',
            action='ENTER_LONG' if entry_eligible else 'HOLD', entry_price=price, score=score_data['total_score'],
            probability=probability, expected_value_pct=expected_value * 100.0, features_json=json.dumps(features),
            prediction_json=json.dumps({'model_version': model.version, 'intrabar_policy': 'STOP_FIRST'}),
            tp_price=price * (1.0 + tp_pct), sl_price=price * (1.0 - sl_pct), horizon_candles=cls.horizon_candles,
            created_at=utc_now(), updated_at=utc_now(),
        )
        db.session.add(evaluation)
        if commit:
            db.session.commit()
        return evaluation

    @staticmethod
    def link_signal(evaluation: StrategyEvaluation, signal_id: str) -> None:
        evaluation.signal_id = signal_id
        db.session.commit()

    @classmethod
    def resolve_pending(cls, limit: int = 200) -> int:
        evaluations = StrategyEvaluation.query.filter_by(label_status='PENDING').order_by(StrategyEvaluation.decision_candle_ts.asc()).limit(limit).all()
        if evaluations:
            return cls._resolve_batch(evaluations)
        resolved = 0
        for evaluation in evaluations:
            candles = Candle.query.filter(
                Candle.symbol == evaluation.symbol, Candle.timeframe == evaluation.timeframe,
                Candle.timestamp > evaluation.decision_candle_ts,
            ).order_by(Candle.timestamp.asc()).limit(evaluation.horizon_candles).all()
            if len(candles) < evaluation.horizon_candles:
                continue
            mfe = max((c.high - evaluation.entry_price) / evaluation.entry_price * 100.0 for c in candles)
            mae = min((c.low - evaluation.entry_price) / evaluation.entry_price * 100.0 for c in candles)
            label = 'TIMEOUT'
            label_candle = candles[-1]
            for candle in candles:
                # Conservative policy when both barriers are crossed in one OHLC candle.
                if candle.low <= evaluation.sl_price:
                    label, label_candle = 'SL_HIT', candle
                    break
                if candle.high >= evaluation.tp_price:
                    label, label_candle = 'TP_HIT', candle
                    break
            evaluation.label_status = 'RESOLVED'
            evaluation.label = label
            evaluation.label_candle_ts = label_candle.timestamp
            evaluation.label_at = label_candle.datetime
            evaluation.time_to_label_candles = candles.index(label_candle) + 1
            evaluation.max_favorable_excursion_pct = mfe
            evaluation.max_adverse_excursion_pct = mae
            evaluation.realized_return_pct = ((label_candle.close - evaluation.entry_price) / evaluation.entry_price * 100.0) - cls.total_cost_pct * 100.0
            resolved += 1
        if resolved:
            db.session.commit()
        return resolved

    @classmethod
    def _resolve_batch(cls, evaluations) -> int:
        """Resolve large historical batches using one candle query instead of one per row."""
        symbols = {evaluation.symbol for evaluation in evaluations}
        timeframes = {evaluation.timeframe for evaluation in evaluations}
        candles = Candle.query.filter(Candle.symbol.in_(symbols), Candle.timeframe.in_(timeframes)).order_by(Candle.symbol, Candle.timeframe, Candle.timestamp).all()
        grouped = {}
        indexes = {}
        for candle in candles:
            key = (candle.symbol, candle.timeframe)
            indexes.setdefault(key, {})[candle.timestamp] = len(grouped.setdefault(key, []))
            grouped[key].append(candle)
        updates = []
        for evaluation in evaluations:
            candle_list = grouped.get((evaluation.symbol, evaluation.timeframe), [])
            index = indexes.get((evaluation.symbol, evaluation.timeframe), {}).get(evaluation.decision_candle_ts)
            if index is None:
                index = next((i - 1 for i, candle in enumerate(candle_list) if candle.timestamp > evaluation.decision_candle_ts), None)
                if index is None:
                    continue
            future = candle_list[index + 1:index + 1 + evaluation.horizon_candles]
            if len(future) < evaluation.horizon_candles:
                continue
            mfe = max((candle.high - evaluation.entry_price) / evaluation.entry_price * 100.0 for candle in future)
            mae = min((candle.low - evaluation.entry_price) / evaluation.entry_price * 100.0 for candle in future)
            label, label_candle = 'TIMEOUT', future[-1]
            for candle in future:
                if candle.low <= evaluation.sl_price:
                    label, label_candle = 'SL_HIT', candle
                    break
                if candle.high >= evaluation.tp_price:
                    label, label_candle = 'TP_HIT', candle
                    break
            updates.append({
                'id': evaluation.id, 'label_status': 'RESOLVED', 'label': label,
                'label_candle_ts': label_candle.timestamp, 'label_at': label_candle.datetime,
                'time_to_label_candles': future.index(label_candle) + 1,
                'max_favorable_excursion_pct': mfe, 'max_adverse_excursion_pct': mae,
                'realized_return_pct': ((label_candle.close - evaluation.entry_price) / evaluation.entry_price * 100.0) - cls.total_cost_pct * 100.0,
                'updated_at': utc_now(),
            })
        if updates:
            if db.engine.dialect.name == 'mysql':
                connection = db.session.connection()
                connection.execute(text('''
                    CREATE TEMPORARY TABLE evaluation_label_updates (
                        id VARCHAR(64) PRIMARY KEY, label_status VARCHAR(20), label VARCHAR(20),
                        label_candle_ts BIGINT, label_at DATETIME, time_to_label_candles INT,
                        max_favorable_excursion_pct DOUBLE, max_adverse_excursion_pct DOUBLE,
                        realized_return_pct DOUBLE, updated_at DATETIME
                    )
                '''))
                columns = ('id', 'label_status', 'label', 'label_candle_ts', 'label_at', 'time_to_label_candles',
                           'max_favorable_excursion_pct', 'max_adverse_excursion_pct', 'realized_return_pct', 'updated_at')
                for offset in range(0, len(updates), 500):
                    batch = updates[offset:offset + 500]
                    params = {}
                    values = []
                    for row_index, update in enumerate(batch):
                        names = []
                        for column in columns:
                            parameter = f'{column}_{row_index}'
                            params[parameter] = update[column]
                            names.append(f':{parameter}')
                        values.append(f"({', '.join(names)})")
                    connection.execute(text(f"INSERT INTO evaluation_label_updates ({', '.join(columns)}) VALUES {', '.join(values)}"), params)
                connection.execute(text('''
                    UPDATE strategy_evaluations evaluation
                    INNER JOIN evaluation_label_updates update_row ON update_row.id = evaluation.id
                    SET evaluation.label_status = update_row.label_status,
                        evaluation.label = update_row.label,
                        evaluation.label_candle_ts = update_row.label_candle_ts,
                        evaluation.label_at = update_row.label_at,
                        evaluation.time_to_label_candles = update_row.time_to_label_candles,
                        evaluation.max_favorable_excursion_pct = update_row.max_favorable_excursion_pct,
                        evaluation.max_adverse_excursion_pct = update_row.max_adverse_excursion_pct,
                        evaluation.realized_return_pct = update_row.realized_return_pct,
                        evaluation.updated_at = update_row.updated_at
                '''))
            else:
                db.session.bulk_update_mappings(StrategyEvaluation, updates)
            db.session.commit()
        return len(updates)
