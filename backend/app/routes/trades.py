from flask import Blueprint, jsonify, request
from app.models import Signal, PaperOrder, PaperFill, Trade, PaperPosition

trades_bp = Blueprint('trades', __name__)

@trades_bp.route('/signals', methods=['GET'])
def get_signals():
    limit = int(request.args.get('limit', 50))
    signals = Signal.query.order_by(Signal.timestamp.desc()).limit(limit).all()
    return jsonify([s.to_dict() for s in signals]), 200

@trades_bp.route('/orders', methods=['GET'])
def get_orders():
    limit = int(request.args.get('limit', 50))
    orders = PaperOrder.query.order_by(PaperOrder.created_at.desc()).limit(limit).all()
    return jsonify([o.to_dict() for o in orders]), 200

@trades_bp.route('/fills', methods=['GET'])
def get_fills():
    limit = int(request.args.get('limit', 50))
    fills = PaperFill.query.order_by(PaperFill.timestamp.desc()).limit(limit).all()
    return jsonify([f.to_dict() for f in fills]), 200

@trades_bp.route('/trades', methods=['GET'])
def get_trades():
    limit = int(request.args.get('limit', 50))
    trades = Trade.query.order_by(Trade.closed_at.desc()).limit(limit).all()
    return jsonify([t.to_dict() for t in trades]), 200

@trades_bp.route('/positions', methods=['GET'])
def get_positions():
    positions = PaperPosition.query.filter_by(is_open=True).all()
    return jsonify([p.to_dict() for p in positions]), 200
