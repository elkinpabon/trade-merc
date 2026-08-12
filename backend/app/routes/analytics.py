from flask import Blueprint, jsonify
from app.services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics/overview', methods=['GET'])
def get_analytics():
    data = AnalyticsService.calculate_metrics()
    return jsonify(data), 200
