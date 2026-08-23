from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from app.extensions import db
from app.models import Candle, StrategyEvaluation
from app.services.evaluation_service import EvaluationService
from app.services.indicator_service import IndicatorService
from app.services.model_service import ModelService
from app.services.strategy_service import StrategyService


class BackfillService:
    """Loads public historical candles and builds an auditable research dataset."""

    @staticmethod
    def _fetch(symbol: str, timeframe: str, start_ms: int, end_ms: int) -> list[dict]:
        pair = symbol.replace('/', '').upper()
        candles = []
        cursor = start_ms
        while cursor < end_ms:
            response = requests.get(
                'https://data-api.binance.vision/api/v3/klines',
                params={'symbol': pair, 'interval': timeframe, 'startTime': cursor, 'endTime': end_ms, 'limit': 1000},
                timeout=15,
            )
            response.raise_for_status()
            rows = response.json()
            if not rows:
                break
            for row in rows:
                candles.append({
                    'symbol': symbol, 'timeframe': timeframe, 'timestamp': int(row[0]),
                    'datetime': datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc).replace(tzinfo=None),
                    'open': float(row[1]), 'high': float(row[2]), 'low': float(row[3]),
                    'close': float(row[4]), 'volume': float(row[5]),
                })
            next_cursor = int(rows[-1][0]) + 1
            if next_cursor <= cursor or len(rows) < 1000:
                break
            cursor = next_cursor
        return candles

    @classmethod
    def ingest(cls, config, days: int = 30) -> dict:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        start_ms, end_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
        summary = {'candles': 0, 'evaluations': 0, 'symbols': 0}
        model = ModelService.active_model()
        strategy = StrategyService(config)
        for symbol in config.symbols.split(','):
            raw = cls._fetch(symbol, config.timeframe, start_ms, end_ms)
            if not raw:
                continue
            existing = {row[0] for row in db.session.query(Candle.timestamp).filter_by(symbol=symbol, timeframe=config.timeframe).all()}
            for candle in raw:
                if candle['timestamp'] not in existing:
                    db.session.add(Candle(**candle))
                    summary['candles'] += 1
            db.session.commit()

            frame = pd.DataFrame(raw)
            if len(frame) < 40:
                continue
            frame = IndicatorService.apply_indicators(frame, config.ema_fast_period, config.ema_slow_period, config.rsi_period)
            existing_evaluations = {row[0] for row in db.session.query(StrategyEvaluation.decision_candle_ts).filter_by(symbol=symbol, timeframe=config.timeframe, model_version_id=model.id).all()}
            for index in range(30, len(frame)):
                latest = frame.iloc[index]
                if int(latest['timestamp']) in existing_evaluations:
                    continue
                score_data = strategy.compute_composite_score(frame.iloc[:index + 1])
                EvaluationService.record(
                    config, None, symbol, config.timeframe, latest, score_data,
                    commit=False, check_existing=False, model=model,
                )
                summary['evaluations'] += 1
                if summary['evaluations'] % 500 == 0:
                    db.session.commit()
            db.session.commit()
            summary['symbols'] += 1
        EvaluationService.resolve_pending(limit=100000)
        return summary
