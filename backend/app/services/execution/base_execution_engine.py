from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

class BaseExecutionEngine(ABC):
    """
    Abstract base class for all trade execution engines (Paper / Live).
    Guarantees pluggability so switching between simulation and real market execution
    requires zero code changes in the strategy and worker layers.
    """

    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float, signal_id: Optional[str] = None) -> Dict[str, Any]:
        """Places a market or limit order."""
        pass

    @abstractmethod
    def close_position(self, symbol: str, current_price: float, reason: str = 'MANUAL') -> Dict[str, Any]:
        """Closes an active position for a symbol."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancels a pending order."""
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """Returns virtual or real account balances (cash, positions_value, total_equity)."""
        pass

    @abstractmethod
    def sync_positions(self) -> List[Dict[str, Any]]:
        """Synchronizes and returns current open positions."""
        pass

    @abstractmethod
    def sync_orders(self) -> List[Dict[str, Any]]:
        """Synchronizes and returns recent orders."""
        pass

    @abstractmethod
    def validate_symbol_rules(self, symbol: str, quantity: float, price: float) -> tuple[bool, str]:
        """Validates minimum notional, step size, and price precision."""
        pass

    @abstractmethod
    def estimate_fees(self, notional: float, fee_pct: float) -> float:
        """Calculates estimated transaction fees."""
        pass

    @abstractmethod
    def estimate_slippage(self, requested_price: float, side: str, slippage_pct: float) -> float:
        """Calculates fill price after simulated or real market slippage."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Verifies engine connectivity and operational status."""
        pass
