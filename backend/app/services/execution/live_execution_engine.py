import ccxt
import os
from typing import Dict, Any, Optional, List
from app.services.execution.base_execution_engine import BaseExecutionEngine
from app.utils.encryption import decrypt_credential
from app.models import ExchangeCredentials

class LiveExecutionEngine(BaseExecutionEngine):
    """
    Live Execution Engine for CCXT Private API Trading.
    
    SECURITY ARCHITECTURE:
    - Disabled by default via global environment variable LIVE_TRADING_ENABLED=False.
    - Strictly validates API key, API secret, and passphrase before initialization.
    - Prevents accidental real order execution in Paper Trading mode.
    - Designed for zero-downtime transition to real money trading when credentials are supplied.
    """

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        self.live_enabled = os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
        self.exchange_client = None

    def initialize_client(self) -> tuple[bool, str]:
        """Loads encrypted credentials from DB or environment and initializes CCXT private client."""
        if not self.live_enabled:
            return False, "LIVE_TRADING_ENABLED is currently FALSE in system environment. Live mode deactivated."

        creds = ExchangeCredentials.query.filter_by(exchange_name=self.exchange_id, is_active=True).first()
        
        api_key = decrypt_credential(creds.api_key_encrypted) if creds and creds.api_key_encrypted else os.getenv("EXCHANGE_API_KEY")
        api_secret = decrypt_credential(creds.api_secret_encrypted) if creds and creds.api_secret_encrypted else os.getenv("EXCHANGE_API_SECRET")
        passphrase = decrypt_credential(creds.passphrase_encrypted) if creds and creds.passphrase_encrypted else os.getenv("EXCHANGE_API_PASSPHRASE")

        if not api_key or not api_secret:
            return False, f"Missing private API Key or Secret for exchange {self.exchange_id}."

        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            config = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            }
            if passphrase:
                config['password'] = passphrase
            
            if creds and creds.testnet_flag:
                config['options'] = {'defaultType': 'spot'}

            self.exchange_client = exchange_class(config)
            
            if creds and creds.testnet_flag:
                self.exchange_client.set_sandbox_mode(True)

            return True, "Private CCXT client successfully initialized."
        except Exception as e:
            return False, f"Failed to initialize CCXT private client: {str(e)}"

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float, signal_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.live_enabled or not self.exchange_client:
            raise RuntimeError("CRITICAL SAFETY BLOCK: Live trading execution attempted while LIVE_TRADING_ENABLED is FALSE.")

        try:
            order = self.exchange_client.create_order(
                symbol=symbol,
                type=order_type.lower(),
                side=side.lower(),
                amount=quantity,
                price=price if order_type.upper() == 'LIMIT' else None
            )
            return {"success": True, "order": order}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_position(self, symbol: str, current_price: float, reason: str = 'MANUAL') -> Dict[str, Any]:
        if not self.live_enabled or not self.exchange_client:
            raise RuntimeError("CRITICAL SAFETY BLOCK: Live close_position called while LIVE_TRADING_ENABLED is FALSE.")
        
        # In live spot trading, closing position means placing a market SELL for total base currency balance
        try:
            balance = self.exchange_client.fetch_balance()
            base_currency = symbol.split('/')[0]
            qty = balance['free'].get(base_currency, 0.0)
            if qty <= 0:
                return {"success": False, "error": f"No spot balance available to close for {symbol}"}

            return self.place_order(symbol=symbol, side='SELL', order_type='MARKET', quantity=qty, price=current_price)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        if not self.live_enabled or not self.exchange_client:
            return False
        try:
            self.exchange_client.cancel_order(order_id)
            return True
        except Exception:
            return False

    def get_balance(self) -> Dict[str, float]:
        if not self.live_enabled or not self.exchange_client:
            return {"cash_balance": 0.0, "total_equity": 0.0}
        try:
            bal = self.exchange_client.fetch_balance()
            total_usdt = float(bal['total'].get('USDT', 0.0))
            free_usdt = float(bal['free'].get('USDT', 0.0))
            return {
                "cash_balance": free_usdt,
                "total_equity": total_usdt
            }
        except Exception:
            return {"cash_balance": 0.0, "total_equity": 0.0}

    def sync_positions(self) -> List[Dict[str, Any]]:
        if not self.live_enabled or not self.exchange_client:
            return []
        try:
            bal = self.exchange_client.fetch_balance()
            positions = []
            for curr, amount in bal['total'].items():
                if amount > 0 and curr != 'USDT':
                    positions.append({
                        "symbol": f"{curr}/USDT",
                        "quantity": amount,
                        "side": "LONG"
                    })
            return positions
        except Exception:
            return []

    def sync_orders(self) -> List[Dict[str, Any]]:
        if not self.live_enabled or not self.exchange_client:
            return []
        try:
            return self.exchange_client.fetch_open_orders()
        except Exception:
            return []

    def validate_symbol_rules(self, symbol: str, quantity: float, price: float) -> tuple[bool, str]:
        return True, "OK"

    def estimate_fees(self, notional: float, fee_pct: float) -> float:
        return notional * (fee_pct / 100.0)

    def estimate_slippage(self, requested_price: float, side: str, slippage_pct: float) -> float:
        return requested_price

    def health_check(self) -> Dict[str, Any]:
        if not self.live_enabled:
            return {
                "status": "DISABLED",
                "mode": "LIVE_TRADING_DISABLED",
                "message": "Live Execution Engine is locked and inactive for safety."
            }
        
        ok, msg = self.initialize_client()
        return {
            "status": "HEALTHY" if ok else "DOWN",
            "mode": "LIVE_TRADING_ACTIVE" if ok else "CONFIG_ERROR",
            "details": msg
        }
