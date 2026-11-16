"""Start an explicitly authorized, isolated A/B paper experiment atomically and idempotently."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.extensions import db
from app.models import BotConfig, BotRun, PaperPosition, StrategyRun, SymbolRule
from app.services.activity_profiles import PILOT_PROFILES
from app.services.experiment_service import ExperimentService
from app.services.model_service import ModelService
from app.utils.helpers import generate_uuid, utc_now


def launch(profile, trial_key, expected_previous_run, *, acknowledge=False, sync_rules=None):
    if profile not in PILOT_PROFILES or not acknowledge:
        raise ValueError('Explicit authorization of an unvalidated PAPER hypothesis is required')
    if not trial_key or len(trial_key) > 100:
        raise ValueError('A bounded trial key is required')
    experiments = StrategyRun.query.filter_by(run_type='EXPERIMENT').order_by(StrategyRun.started_at.desc()).all()
    for previous in experiments:
        parameters = json.loads(previous.parameters_json or '{}')
        if parameters.get('pilot_metadata', {}).get('trial_key') == trial_key:
            if json.loads(previous.config_snapshot_json)['strategy_key'] != profile:
                raise ValueError('Trial key already belongs to another profile')
            return previous, False
    if not experiments or experiments[0].id != expected_previous_run or experiments[0].status != 'COMPLETED':
        raise ValueError('Expected completed predecessor does not match; refusing to replace another experiment')
    if any(e.status == 'RUNNING' for e in experiments) or PaperPosition.query.filter_by(is_open=True).count():
        raise ValueError('Account must be flat, with no active experiment')
    predecessor = experiments[0]
    source = db.session.get(BotConfig, predecessor.config_id)
    if not source or source.mode != 'paper':
        raise ValueError('Missing paper predecessor configuration')
    symbols = source.symbols
    # Create the model before any account/run/rule mutations (model creation may commit).
    model = ModelService.for_config(BotConfig(strategy_key=profile))
    try:
        if sync_rules:
            sync_rules(symbols.split(','))
        config = BotConfig(name=profile, strategy_key=profile, symbols=symbols,
                           mode='paper', timeframe='15m', virtual_balance=100.,
                           risk_per_trade_pct=.25, stop_loss_pct=2., take_profit_pct=4.,
                           fee_pct=.1, slippage_pct=.05, cooldown_seconds=3600,
                           candle_limit=200, polling_interval_seconds=900, is_active=True,
                           model_version_id=model.id)
        db.session.add(config)
        db.session.flush()
        # Freeze persisted values, including MySQL DATETIME second precision.
        db.session.refresh(config)
        now = utc_now()
        for old in BotRun.query.filter_by(status='running').all():
            old.status, old.stopped_at = 'stopped', now
        db.session.add(BotRun(id=generate_uuid(), config_id=config.id, status='running', started_at=now))
        db.session.flush()
        run = ExperimentService.start(config, allow_unvalidated_paper=True, commit=False,
                                      pilot_metadata={'trial_key': trial_key, 'predecessor_run_id': predecessor.id,
                                                      'authorization': 'operator-requested exploratory paper trial',
                                                      'source': 'historical diagnostics; not out-of-sample validation',
                                                      'rules_known_at_start': [r.to_dict() for r in SymbolRule.query.filter(SymbolRule.symbol.in_(symbols.split(','))).all()]})
        db.session.commit()
        return run, True
    except Exception:
        db.session.rollback()
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', choices=PILOT_PROFILES)
    parser.add_argument('--trial-key', required=True)
    parser.add_argument('--expected-previous-run', required=True)
    parser.add_argument('--acknowledge-unvalidated-paper', action='store_true')
    args = parser.parse_args()
    if not (os.environ.get('DATABASE_URL') or (os.environ.get('DB_HOST') and os.environ.get('DB_NAME'))):
        raise SystemExit('Explicit database environment required; no implicit database fallback')
    app = create_app()
    with app.app_context():
        lock = None
        name = os.environ.get('WORKER_LOCK_NAME', 'trademerc:bot-worker-cycle')
        try:
            if db.engine.dialect.name.startswith('mysql'):
                lock = db.engine.connect()
                if lock.execute(db.text('SELECT GET_LOCK(:name, 10)'), {'name': name}).scalar() != 1:
                    raise RuntimeError('Worker cycle lock is busy; retry without interrupting the cycle')
            from scripts.configure_strategy import sync_rules
            run, created = launch(args.profile, args.trial_key, args.expected_previous_run,
                                  acknowledge=args.acknowledge_unvalidated_paper, sync_rules=sync_rules)
            print(json.dumps({'created': created, 'run': run.to_dict()}, default=str))
        finally:
            if lock is not None:
                try:
                    lock.execute(db.text('SELECT RELEASE_LOCK(:name)'), {'name': name})
                finally:
                    lock.close()


if __name__ == '__main__':
    main()
