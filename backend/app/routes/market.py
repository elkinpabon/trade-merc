from flask import Blueprint, jsonify, request
from app.services.market_data_service import MarketDataService
from app.services.scanner_service import ScannerService
from app.config import DEFAULT_50_SYMBOLS

market_bp = Blueprint('market', __name__)

@market_bp.route('/market/candles', methods=['GET'])
def get_candles():
    symbol = request.args.get('symbol', 'BTC/USDT')
    timeframe = request.args.get('timeframe', '5m')
    limit = int(request.args.get('limit', 100))

    market_svc = MarketDataService()
    try:
        candles = market_svc.fetch_public_ohlcv(symbol, timeframe, limit)
        return jsonify(candles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@market_bp.route('/market/ticker', methods=['GET'])
def get_ticker():
    symbol = request.args.get('symbol', 'BTC/USDT')
    market_svc = MarketDataService()
    try:
        ticker = market_svc.fetch_all_tickers([symbol]).get(symbol)
        if not ticker:
            return jsonify({"error": "Market ticker is unavailable."}), 503
        return jsonify(ticker), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@market_bp.route('/market/scanner', methods=['GET'])
def get_market_scanner():
    """
    REST endpoint to immediately return scanned 50+ tickers.
    Guarantees popular coins data is returned instantly on initial page load.
    """
    market_svc = MarketDataService()
    try:
        tickers = market_svc.fetch_all_tickers(DEFAULT_50_SYMBOLS[:30])
        if not tickers:
            return jsonify({"error": "Market scanner data is unavailable."}), 503

        scanned = ScannerService.scan_tickers(tickers)
        return jsonify({"total_markets": len(scanned), "markets": scanned}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
