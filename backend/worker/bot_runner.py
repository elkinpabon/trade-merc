import time
import traceback
from datetime import datetime, timedelta
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import BotConfig, BotRun, PaperPosition, PaperOrder, Signal, WorkerCycle
from app.services import (
    MarketDataService,
    SymbolRulesService,
    StrategyService,
    RiskService,
    PortfolioService,
    LogService,
    HealthService,
    ScannerService,
    IndicatorService,
    EvaluationService,
    ModelService,
    ResearchMetricsService,
)
from app.services.execution import PaperExecutionEngine, LiveExecutionEngine
from app.sockets import broadcast_event
from app.utils.helpers import utc_now
from app.services.experiment_service import ExperimentService
from app.utils.helpers import generate_uuid


def recover_stale_submitted_signals(max_age_minutes: int = 15) -> int:
    """Moves interrupted submissions out of the execution state machine."""
    cutoff = utc_now() - timedelta(minutes=max_age_minutes)
    stale = Signal.query.filter(Signal.status == 'SUBMITTED', Signal.timestamp < cutoff).all()
    recovered = 0
    for signal in stale:
        order = PaperOrder.query.filter_by(signal_id=signal.id).first()
        if order:
            if order.status == 'FILLED':
                signal.status = 'EXECUTED'
                recovered += 1
            elif order.status in ('REJECTED', 'CANCELLED'):
                signal.status = 'REJECTED'
                signal.reason = (signal.reason or '') + f' | Reconciliada con orden {order.status}.'
                recovered += 1
            continue
        signal.status = 'REJECTED'
        signal.reason = (signal.reason or '') + ' | Recuperada: no existia orden asociada.'
        recovered += 1
    if recovered:
        db.session.commit()
    return recovered

def run_bot_loop(app: Flask, max_cycles: int | None = None):
    """
    Advanced Multi-Factor Multi-Market Execution Loop.
    Scans 50+ pairs, computes composite scores using 10+ indicators,
    detects high-conviction setups (score >= 65/100), enforces risk controls,
    and emits second-by-second real-time analysis logs with detailed scoring.
    """
    print("Starting Advanced Multi-Factor Trading Engine Loop...")
    with app.app_context():
        LogService.log("INFO", "BotRunner", "Motor Multi-Factor avanzado inicializado: EMA+RSI+MACD+BB+ATR+ADX+StochRSI+OBV+VWAP")

    completed_cycles = 0
    last_cycle_succeeded = False
    while max_cycles is None or completed_cycles < max_cycles:
        completed_cycles += 1
        cycle_succeeded = False
        polling_interval = 1
        active_run_id = None
        worker_cycle_id = None
        cycle_error = None
        expected_count = 0
        received_count = 0
        processed_count = 0
        lock_connection = None
        lock_acquired = False
        with app.app_context():
            try:
                active_run = BotRun.query.filter_by(status='running').first()
                if not active_run:
                    HealthService.update_component_health("bot_worker", "IDLE", "Bot worker is stopped.")
                    if max_cycles is None:
                        time.sleep(1)
                    continue
                active_run_id = active_run.id

                config = db.session.get(BotConfig, active_run.config_id)
                if not config:
                    raise RuntimeError(f'Bot run {active_run.id} has no valid configuration.')
                polling_interval = int(config.polling_interval_seconds) if config.polling_interval_seconds else 1

                experiment = ExperimentService.active_run(config.id)
                if experiment and ExperimentService.config_snapshot(config) != experiment.config_snapshot_json:
                    raise RuntimeError('Experiment configuration changed after the run was frozen.')

                if db.engine.dialect.name.startswith('mysql'):
                    try:
                        lock_connection = db.engine.connect()
                        lock_acquired = lock_connection.execute(
                            db.text("SELECT GET_LOCK(:name, 0)"),
                            {"name": "trademerc:bot-worker-cycle"},
                        ).scalar() == 1
                    except Exception as lock_error:
                        if lock_connection:
                            lock_connection.close()
                            lock_connection = None
                        raise RuntimeError(f'MySQL cycle lock unavailable: {lock_error}') from lock_error

                    if lock_connection and not lock_acquired:
                        cycle_error = "Another bot worker owns the cycle lock."
                        HealthService.update_component_health("bot_worker", "DEGRADED", cycle_error)
                        if max_cycles is None:
                            time.sleep(polling_interval)
                        continue

                recovered = recover_stale_submitted_signals()
                if recovered:
                    LogService.log('WARNING', 'ExecutionEngine', f"Señales SUBMITTED recuperadas: {recovered}")

                symbols = [symbol.strip() for symbol in config.symbols.split(",") if symbol.strip()] if config.symbols else ["BTC/USDT", "ETH/USDT"]
                timeframe = config.timeframe

                if config.mode == 'live' and app.config.get('LIVE_TRADING_ENABLED'):
                    executor = LiveExecutionEngine(config.exchange_id)
                else:
                    executor = PaperExecutionEngine(config)

                market_svc = MarketDataService(config.exchange_id)
                strategy_svc = StrategyService(config)
                risk_svc = RiskService(config)
                portfolio_svc = PortfolioService(config)

                top_candidates = list(dict.fromkeys(symbols))
                open_positions = PaperPosition.query.filter_by(is_open=True).all()
                for position in open_positions:
                    if position.symbol not in top_candidates:
                        top_candidates.append(position.symbol)

                expected_count = len(top_candidates)
                symbol_errors = []

                worker_cycle = WorkerCycle(
                    id=generate_uuid(), bot_run_id=active_run.id,
                    strategy_run_id=experiment.id if experiment else None,
                    status='RUNNING', expected_symbols=expected_count, started_at=utc_now(),
                )
                db.session.add(worker_cycle)
                db.session.commit()
                worker_cycle_id = worker_cycle.id

                # 1. BATCH FETCH ALL 50+ TICKERS IN A SINGLE ~150ms CALL
                all_tickers = market_svc.fetch_all_tickers(top_candidates)
                all_tickers = all_tickers or {}
                symbol_prices = {
                    symbol: ticker['last'] for symbol, ticker in all_tickers.items()
                    if symbol in top_candidates and ticker.get('last') and ticker['last'] > 0
                }
                received_count = len(symbol_prices)

                if all_tickers:
                    # 2. RUN MULTI-MARKET ANOMALY & PATTERN SCANNER
                    scanned_markets = ScannerService.scan_tickers(all_tickers)
                    
                    # Broadcast Scanner Telemetry to Frontend
                    broadcast_event('market_scanner_update', {
                        'timestamp': int(time.time() * 1000),
                        'total_markets': len(all_tickers),
                        'markets': scanned_markets[:30]
                    })

                    for symbol in top_candidates:
                        try:
                            current_price = symbol_prices.get(symbol, 0.0)
                            if current_price <= 0:
                                continue

                            # Check Stop Loss / Take Profit
                            sl_tp_check = risk_svc.check_stop_loss_take_profit(symbol, current_price)
                            if sl_tp_check:
                                reason = sl_tp_check['reason']
                                print(f"[RISK EXIT] {reason} for {symbol}")
                                close_res = executor.close_position(symbol, current_price, reason=reason)
                                if close_res.get('success'):
                                    LogService.log('WARNING', 'RiskEngine', f"Posición cerrada: {reason} en {symbol}")
                                    broadcast_event('trade_closed', close_res)
                                    broadcast_event('risk_alert', {'type': reason, 'symbol': symbol, 'price': current_price})
                                else:
                                    raise RuntimeError(f"Risk exit failed: {close_res.get('error', 'unknown error')}")
                                processed_count += 1
                                continue

                            # Fetch DataFrame for Multi-Factor Analysis
                            df = market_svc.get_ohlcv_dataframe(symbol, timeframe=timeframe, limit=config.candle_limit)
                            if df.empty or len(df) < 30:
                                continue

                            df = IndicatorService.apply_indicators(
                                df,
                                ema_fast=config.ema_fast_period,
                                ema_slow=config.ema_slow_period,
                                rsi_period=config.rsi_period
                            )
                            latest = df.iloc[-1]

                            # Compute composite score for logging
                            score_data = strategy_svc.compute_composite_score(df)
                            total_score = score_data['total_score']
                            t_s = score_data['trend_score']
                            m_s = score_data['momentum_score']
                            v_s = score_data['volume_score']
                            vol_s = score_data['volatility_score']
                            pred_s = score_data.get('prediction_score', 0)
                            reg_s = score_data.get('regime_score', 0)
                            ml = score_data.get('ml_prediction', {})

                            rsi_val = float(latest.get('rsi', 50.0))
                            adx_val = float(latest.get('adx', 0.0))
                            macd_h = float(latest.get('macd_histogram', 0.0))
                            vol_r = float(latest.get('vol_ratio', 1.0))

                            # Determine conviction level
                            if total_score >= 75:
                                conviction = "ALTA CONVICCION"
                            elif total_score >= 60:
                                conviction = "SENAL DE ENTRADA"
                            elif total_score >= 45:
                                conviction = "NEUTRAL/OBSERVANDO"
                            elif total_score >= 25:
                                conviction = "DEBIL"
                            else:
                                conviction = "BAJISTA/SALIR"

                            regime = ml.get('market_regime', 'N/A')
                            pattern = ml.get('candle_pattern', 'NONE')
                            lr_dir = ml.get('lr_direction', 0)
                            lr_r2 = ml.get('lr_r_squared', 0)
                            lr_arrow = "UP" if lr_dir == 1 else ("DOWN" if lr_dir == -1 else "FLAT")

                            log_msg = (
                                f"[{symbol}] ${current_price:.2f} | "
                                f"Score={total_score:.0f}/100 {conviction} | "
                                f"T={t_s:.0f} M={m_s:.0f} V={v_s:.0f} Vol={vol_s:.0f} Pred={pred_s:.0f} Reg={reg_s:.0f} | "
                                f"RSI={rsi_val:.0f} ADX={adx_val:.0f} MACD={macd_h:+.4f} VolR={vol_r:.1f}x | "
                                f"ML:{regime} LR={lr_arrow}(R2={lr_r2:.2f}) Pat={pattern}"
                            )

                            # Log to DB and Broadcast Real-time Log Event
                            LogService.log('INFO', 'BotScanner', log_msg)

                            evaluation = EvaluationService.record(
                                config, active_run.id, symbol, timeframe, latest, score_data
                            )
                            signal = None
                            if not evaluation.signal_id:
                                signal = strategy_svc.evaluate_market(
                                    df, symbol, active_run.id, score_data=score_data,
                                    probability=evaluation.probability,
                                )

                            if signal:
                                if (signal.type == 'BUY' and experiment and experiment.planned_end_at
                                        and utc_now() >= experiment.planned_end_at):
                                    EvaluationService.link_signal(evaluation, signal.id)
                                    signal.status = 'REJECTED'
                                    signal.reason = (signal.reason or '') + ' | Experimento finalizado: nuevas entradas bloqueadas.'
                                    db.session.commit()
                                    signal = None

                            if signal:
                                EvaluationService.link_signal(evaluation, signal.id)
                                broadcast_event('signal_created', signal.to_dict())
                                LogService.log('INFO', 'StrategyEngine', f"Señal multi-factor: {signal.type} {symbol} a ${signal.price:.2f} (Score={total_score:.0f})")

                                allowed, reason, qty = risk_svc.validate_signal_risk(signal, current_price)

                                if allowed and qty > 0:
                                    signal.status = 'SUBMITTED'
                                    db.session.commit()

                                    order_res = executor.place_order(
                                        symbol=symbol,
                                        side=signal.type,
                                        order_type='MARKET',
                                        quantity=qty,
                                        price=current_price,
                                        signal_id=signal.id
                                    )

                                    if order_res.get('success'):
                                        signal.status = 'EXECUTED'
                                        db.session.commit()
                                        LogService.log('INFO', 'ExecutionEngine', f"Orden ejecutada: {signal.type} {qty:.4f} {symbol} a ${current_price:.2f}")
                                        broadcast_event('order_created', order_res.get('order'))
                                        broadcast_event('fill_created', order_res.get('fill'))
                                    else:
                                        signal.status = 'REJECTED'
                                        db.session.commit()
                                        LogService.log('ERROR', 'ExecutionEngine', f"Orden fallida: {order_res.get('error')}")
                                else:
                                    signal.status = 'REJECTED'
                                    db.session.commit()
                                    LogService.log('WARNING', 'RiskEngine', f"Señal RECHAZADA por Motor de Riesgo: {reason}")
                                    broadcast_event('risk_alert', {'type': 'SIGNAL_REJECTED', 'symbol': symbol, 'reason': reason})

                            processed_count += 1
                        except Exception as symbol_error:
                            db.session.rollback()
                            error_text = f"{symbol}: {symbol_error}"
                            symbol_errors.append(error_text)
                            print(f"Error processing {error_text}")
                            traceback.print_exc()
                            try:
                                LogService.log('ERROR', 'BotScanner', error_text)
                            except Exception:
                                db.session.rollback()

                    if symbol_prices:
                        portfolio_svc.update_valuation(symbol_prices)
                        resolved = EvaluationService.resolve_pending()
                        if resolved:
                            LogService.log('INFO', 'LabelService', f"Etiquetas resueltas: {resolved}")
                        ResearchMetricsService.update_paper_daily(config, active_run)
                        broadcast_event('portfolio_updated', portfolio_svc.get_summary())

                        # Candidate training is best-effort and cannot affect paper execution.
                        try:
                            trained = ModelService.train_if_due()
                            if trained:
                                LogService.log('INFO', 'ModelService', f"Modelo candidato creado: {trained.version}")
                        except Exception as training_error:
                            db.session.rollback()
                            try:
                                LogService.log('ERROR', 'ModelService', f"Entrenamiento candidato omitido: {training_error}")
                            except Exception:
                                db.session.rollback()
                                print(f"Unable to log candidate training failure: {training_error}")
                        try:
                            LogService.prune(retention_days=90)
                        except Exception as pruning_error:
                            db.session.rollback()
                            print(f"Unable to prune old logs: {pruning_error}")

                        ExperimentService.finish_if_due(experiment)

                coverage = f"expected={expected_count}, received={received_count}, processed={processed_count}"
                if symbol_errors:
                    cycle_error = "; ".join(symbol_errors)[:4000]
                fully_covered = received_count == expected_count and processed_count == expected_count
                if fully_covered and not symbol_errors:
                    cycle_succeeded = True
                    HealthService.update_component_health("bot_worker", "HEALTHY", f"Cycle coverage: {coverage}.")
                else:
                    details = f"Partial cycle coverage: {coverage}."
                    if symbol_errors:
                        details += f" Symbol errors: {len(symbol_errors)}."
                    cycle_error = cycle_error or details
                    HealthService.update_component_health("bot_worker", "DEGRADED", details)

            except Exception as e:
                db.session.rollback()
                cycle_error = str(e)
                print(f"Error in bot loop: {e}")
                traceback.print_exc()
                try:
                    HealthService.update_component_health("bot_worker", "DEGRADED", str(e))
                except Exception:
                    db.session.rollback()
            finally:
                if lock_connection:
                    try:
                        if lock_acquired:
                            lock_connection.execute(
                                db.text("SELECT RELEASE_LOCK(:name)"),
                                {"name": "trademerc:bot-worker-cycle"},
                            )
                    except Exception as release_error:
                        print(f"Unable to release MySQL cycle lock: {release_error}")
                    finally:
                        lock_connection.close()

                if active_run_id:
                    try:
                        run = db.session.get(BotRun, active_run_id)
                        if run:
                            run.last_heartbeat = utc_now()
                            run.error_message = cycle_error
                            db.session.commit()
                    except Exception as heartbeat_error:
                        db.session.rollback()
                        print(f"Unable to persist final bot heartbeat: {heartbeat_error}")

                if worker_cycle_id:
                    try:
                        worker_cycle = db.session.get(WorkerCycle, worker_cycle_id)
                        if worker_cycle:
                            worker_cycle.expected_symbols = expected_count
                            worker_cycle.received_symbols = received_count
                            worker_cycle.processed_symbols = processed_count
                            worker_cycle.status = (
                                'SUCCESS' if cycle_succeeded and not cycle_error
                                else 'PARTIAL' if cycle_succeeded else 'FAILED'
                            )
                            worker_cycle.error_message = cycle_error
                            worker_cycle.finished_at = utc_now()
                            db.session.commit()
                    except Exception as cycle_record_error:
                        db.session.rollback()
                        print(f"Unable to persist worker cycle: {cycle_record_error}")

        last_cycle_succeeded = cycle_succeeded
        if max_cycles is None:
            time.sleep(polling_interval)

    return last_cycle_succeeded
