from flask import Blueprint, jsonify, request
from app.services.credentials_service import CredentialsService
from app.services.exchange_service import ExchangeService
from app.models import BotConfig, ExchangeSettings
from app.extensions import db

exchange_bp = Blueprint('exchange', __name__)

@exchange_bp.route('/exchange/settings', methods=['GET'])
def get_exchange_settings():
    config = BotConfig.query.first() or BotConfig()
    creds = CredentialsService.get_credentials(config.exchange_id)
    
    return jsonify({
        "exchange": config.exchange_id,
        "mode": config.mode,
        "live_trading_enabled_system": False, # Fixed safety flag
        "credentials": creds,
        "message": "System currently running in Paper Trading Mode. Live trading locked by system default."
    }), 200

@exchange_bp.route('/exchange/settings', methods=['PUT'])
def update_exchange_settings():
    data = request.json or {}
    exchange_name = data.get('exchange', 'binance')
    api_key = data.get('apiKey', '')
    api_secret = data.get('apiSecret', '')
    passphrase = data.get('passphrase', '')
    testnet = data.get('testnet', True)

    creds = CredentialsService.save_credentials(
        exchange_name=exchange_name,
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        testnet=testnet
    )

    return jsonify({
        "success": True,
        "message": "Exchange credentials saved securely (Encrypted). Live mode remains INACTIVE for safety.",
        "credentials": creds
    }), 200

@exchange_bp.route('/exchange/test-connection', methods=['POST'])
def test_exchange_connection():
    data = request.json or {}
    exchange_name = data.get('exchange', 'binance')
    api_key = data.get('apiKey', '')
    api_secret = data.get('apiSecret', '')
    passphrase = data.get('passphrase', '')
    testnet = data.get('testnet', True)

    # First attempt public test
    public_res = ExchangeService(exchange_name).test_public_connection()
    
    # If API keys passed, test private auth
    if api_key and api_secret:
        private_res = CredentialsService.test_live_connection(exchange_name, api_key, api_secret, passphrase, testnet)
        return jsonify({
            "public_test": public_res,
            "private_test": private_res
        }), 200

    return jsonify({"public_test": public_res, "private_test": {"success": False, "message": "No private API keys provided for private authentication test."}}), 200
