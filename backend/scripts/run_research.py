import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import BotConfig
from app.services import BackfillService, BacktestService, ModelService


def main():
    parser = argparse.ArgumentParser(description='TRADEMERC research jobs')
    parser.add_argument('mode', choices=['backfill', 'backtest', 'train'])
    parser.add_argument('--days', type=int, default=30)
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        config = BotConfig.query.first()
        if not config:
            raise SystemExit('No bot configuration exists.')
        if args.mode == 'backfill':
            print(BackfillService.ingest(config, days=max(1, min(args.days, 90))))
        elif args.mode == 'backtest':
            end = datetime.utcnow()
            result = BacktestService.run(config, end - timedelta(days=max(1, min(args.days, 365))), end)
            print({'run_id': result.run_id, 'trades': result.total_trades, 'return_pct': result.total_return_pct})
        else:
            model = ModelService.train_if_due(minimum_samples=100, minimum_days=0)
            print({'model': model.version if model else None})


if __name__ == '__main__':
    main()
