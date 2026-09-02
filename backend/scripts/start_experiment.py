import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import BotConfig
from app.services.experiment_service import ExperimentService


def main():
    parser = argparse.ArgumentParser(description='Start an isolated 30-day paper experiment')
    parser.add_argument('--config-id', type=int, help='Bot config ID; defaults to the active/first config')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        config = (BotConfig.query.filter_by(id=args.config_id).first() if args.config_id
                  else BotConfig.query.filter_by(is_active=True).first() or BotConfig.query.first())
        if not config:
            raise SystemExit('No bot configuration exists.')
        try:
            run = ExperimentService.start(config)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print({
            'run_id': run.id,
            'started_at': run.started_at.isoformat(),
            'planned_end_at': run.planned_end_at.isoformat(),
            'model_version_id': run.model_version_id,
            'git_commit': run.git_commit,
        })


if __name__ == '__main__':
    main()
