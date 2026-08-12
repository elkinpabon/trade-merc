import ccxt
from typing import Dict, Any

class ExchangeService:
    """
    Service for public CCXT market connectivity tests and metadata discovery.
    """

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id

    def test_public_connection(self) -> Dict[str, Any]:
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            client = exchange_class({'enableRateLimit': True, 'timeout': 5000})
            time_res = client.fetch_time()
            return {
                "success": True,
                "exchange": self.exchange_id,
                "server_time": time_res,
                "message": f"Successfully connected to public {self.exchange_id} endpoints."
            }
        except Exception as e:
            return {
                "success": False,
                "exchange": self.exchange_id,
                "error": str(e),
                "message": f"Failed to connect to public {self.exchange_id} API."
            }
