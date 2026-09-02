from flask import Blueprint, jsonify

from app.models import StrategyRun
from app.services.experiment_service import ExperimentService


experiments_bp = Blueprint('experiments', __name__)


@experiments_bp.route('/experiments/current/report', methods=['GET'])
def current_experiment_report():
    run = StrategyRun.query.filter_by(run_type='EXPERIMENT').order_by(
        StrategyRun.started_at.desc()).first()
    if not run:
        return jsonify({'error': 'Experiment not found.'}), 404
    return jsonify(ExperimentService.report(run.id)), 200


@experiments_bp.route('/experiments/<run_id>/report', methods=['GET'])
def experiment_report(run_id):
    report = ExperimentService.report(run_id)
    if report is None:
        return jsonify({'error': 'Experiment not found.'}), 404
    return jsonify(report), 200
