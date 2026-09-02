import time
import traceback
from datetime import datetime, timedelta
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import BotConfig, BotRun, PaperPosition, PaperOrder, Signal
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


def recover_stale_submitted_signals(max_age_minutes: int = 15) -> int:
    """Moves interrupted submissions out of the execution state machine."""
    cutoff = utc_now() - timedelta(minutes=max_age_minutes)
    stale = Signal.query.filter(Signal.status == 'SUBMITTED', Signal.timestamp < cutoff).all()
    recovered = 0
    for signal in stale:
        if PaperOrder.query.filter_by(signal_id=signal.id).first():
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
        cycle_succeeded = False
        polling_interval = 1
        with app.app_context():
            try:
                config = BotConfig.query.first()
                if not config:
                    time.sleep(2)
                    continue

                polling_interval = int(config.polling_interval_seconds) if config.polling_interval_seconds else 1

                active_run = BotRun.query.filter_by(status='running').first()
                if not active_run:
                    time.sleep(1)
                    continue

                recovered = recover_stale_submitted_signals()
                if recovered:
                    LogService.log('WARNING', 'ExecutionEngine', f"Señales SUBMITTED recuperadas: {recovered}")

                active_run.last_heartbeat = utc_now()
                db.session.commit()

                symbols = config.symbols.split(",") if config.symbols else ["BTC/USDT", "ETH/USDT"]
                timeframe = config.timeframe

                if config.mode == 'live' and app.config.get('LIVE_TRADING_ENABLED'):
                    executor = LiveExecutionEngine(config.exchange_id)
                else:
                    executor = PaperExecutionEngine(config)

                market_svc = MarketDataService(config.exchange_id)
                strategy_svc = StrategyService(config)
                risk_svc = RiskService(config)
                portfolio_svc = PortfolioService(config)

                # 1. BATCH FETCH ALL 50+ TICKERS IN A SINGLE ~150ms CALL
                all_tickers = market_svc.fetch_all_tickers(symbols)

                if all_tickers:
                    # 2. RUN MULTI-MARKET ANOMALY & PATTERN SCANNER
                    scanned_markets = ScannerService.scan_tickers(all_tickers)
                    
                    # Broadcast Scanner Telemetry to Frontend
                    broadcast_event('market_scanner_update', {
                        'timestamp': int(time.time() * 1000),
                        'total_markets': len(all_tickers),
                        'markets': scanned_markets[:30]
                    })

                    symbol_prices = {s: t['last'] for s, t in all_tickers.items() if t.get('last')}

                    # Evaluate every configured liquid pair. The scanner only ranks the UI;
                    # the research dataset needs both entered and rejected decisions.
                    top_candidates = list(symbols)
                    
                    open_positions = PaperPosition.query.filter_by(is_open=True).all()
                    for p in open_positions:
                        if p.symbol not in top_candidates:
                            top_candidates.append(p.symbol)

                    for symbol in top_candidates:
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
                            continue

                        # Fetch DataFrame for Multi-Factor Analysis
                        df = market_svc.get_ohlcv_dataframe(symbol, timeframe=timeframe, limit=config.candle_limit)
                        if not df.empty and len(df) >= 30:
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
                            signal = strategy_svc.evaluate_market(
                                df, symbol, active_run.id, score_data=score_data,
                                probability=evaluation.probability,
                            )

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

                    if symbol_prices:
                        portfolio_svc.update_valuation(symbol_prices)
                        resolved = EvaluationService.resolve_pending()
                        if resolved:
                            LogService.log('INFO', 'LabelService', f"Etiquetas resueltas: {resolved}")
                        ResearchMetricsService.update_paper_daily(config, active_run)
                        trained = ModelService.train_if_due()
                        if trained:
                            LogService.log('INFO', 'ModelService', f"Modelo candidato creado: {trained.version}")
                        broadcast_event('portfolio_updated', portfolio_svc.get_summary())

                if all_tickers:
                    cycle_succeeded = True
                    HealthService.update_component_health("bot_worker", "HEALTHY", f"Motor Multi-Factor escaneando {len(symbols)} pares con 10 indicadores.")
                else:
                    HealthService.update_component_health("bot_worker", "DEGRADED", "No public market data received during this cycle.")

            except Exception as e:
                db.session.rollback()
                print(f"Error in bot loop: {e}")
                traceback.print_exc()
                HealthService.update_component_health("bot_worker", "DEGRADED", str(e))

        completed_cycles += 1
        last_cycle_succeeded = cycle_succeeded
        if max_cycles is None:
            time.sleep(polling_interval)

    return last_cycle_succeeded
