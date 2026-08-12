import os
from typing import Dict, Any
from app.extensions import db
from app.models import ExchangeCredentials
from app.utils.encryption import encrypt_credential, decrypt_credential
import ccxt

class CredentialsService:
    """
    Manages encrypted exchange credentials for future Live Trading mode.
    Includes security encryption via Fernet AES and non-destructive API connection validation.
    """

    @staticmethod
    def get_credentials(exchange_name: str = "binance") -> dict:
        creds = ExchangeCredentials.query.filter_by(exchange_name=exchange_name).first()
        if not creds:
            return {
                "exchange_name": exchange_name,
                "has_api_key": False,
                "has_api_secret": False,
                "has_passphrase": False,
                "testnet_flag": True,
                "is_active": False,
            }
        return creds.to_dict()

    @staticmethod
    def save_credentials(
        exchange_name: str,
        api_key: str,
        api_secret: str,
        passphrase: str = "",
        testnet: bool = True
    ) -> dict:
        creds = ExchangeCredentials.query.filter_by(exchange_name=exchange_name).first()
        if not creds:
            creds = ExchangeCredentials(exchange_name=exchange_name)
            db.session.add(creds)

        if api_key:
            creds.api_key_encrypted = encrypt_credential(api_key)
        if api_secret:
            creds.api_secret_encrypted = encrypt_credential(api_secret)
        if passphrase:
            creds.passphrase_encrypted = encrypt_credential(passphrase)

        creds.testnet_flag = testnet
        creds.is_active = False # Keep inactive by default for security
        db.session.commit()
        return creds.to_dict()

    @staticmethod
    def test_live_connection(exchange_name: str, api_key: str = "", api_secret: str = "", passphrase: str = "", testnet: bool = True) -> Dict[str, Any]:
        """
        Safely tests private CCXT connection without placing any orders.
        Fetches balance non-destructively to verify credentials.
        """
        # If credentials not provided in args, try loading from DB
        if not api_key:
            creds = ExchangeCredentials.query.filter_by(exchange_name=exchange_name).first()
            if creds:
                api_key = decrypt_credential(creds.api_key_encrypted)
                api_secret = decrypt_credential(creds.api_secret_encrypted)
                passphrase = decrypt_credential(creds.passphrase_encrypted)
                testnet = creds.testnet_flag

        if not api_key or not api_secret:
            return {
                "success": False,
                "message": "Missing API Key or API Secret. Credentials test failed."
            }

        try:
            exchange_class = getattr(ccxt, exchange_name)
            config = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'timeout': 7000
            }
            if passphrase:
                config['password'] = passphrase

            client = exchange_class(config)
            if testnet and hasattr(client, 'set_sandbox_mode'):
                client.set_sandbox_mode(True)

            balance = client.fetch_balance()
            return {
                "success": True,
                "message": f"Successfully authenticated with {exchange_name} (Testnet: {testnet}).",
                "account_currencies": list(balance.get('total', {}).keys())[:10]
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Authentication test failed: {str(e)}"
            }
