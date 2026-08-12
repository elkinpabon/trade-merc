import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class PolymarketL2ReplayEngine:
    """
    Motor de Replay Histórico L2 para Backtest de Ejecución en Polymarket.
    Simula la ejecución de órdenes contra snapshots de profundidad completa (L2 Bids/Asks)
    para auditar fill_ratio, slippage_real y EV_net_realized.
    """
    def __init__(self, taker_fee_pct: float = 0.0020, latency_ms: int = 150):
        self.taker_fee_pct = taker_fee_pct
        self.latency_ms = latency_ms

    def walk_orderbook_depth(self, asks: List[List[float]], target_size_usd: float) -> Dict[str, float]:
        """
        Camina la profundidad del libro vendedora (Asks) para calcular el precio medio
        ponderado por volumen (VWAP fill) y el ratio de llenado (fill_ratio).
        
        asks: Lista de pares [precio, volumen_disponible]
        target_size_usd: Tamaño de orden a comprar en USD
        """
        if not asks or target_size_usd <= 0:
            return {"c_exec_weighted": 0.0, "fill_ratio": 0.0, "slippage_real": 0.0, "filled_usd": 0.0}

        accumulated_cost = 0.0
        accumulated_shares = 0.0
        remaining_usd = target_size_usd
        top_ask = float(asks[0][0])

        for level in asks:
            price = float(level[0])
            volume_shares = float(level[1])
            level_cost = price * volume_shares

            if remaining_usd <= level_cost:
                shares_bought = remaining_usd / price
                accumulated_shares += shares_bought
                accumulated_cost += remaining_usd
                remaining_usd = 0.0
                break
            else:
                accumulated_shares += volume_shares
                accumulated_cost += level_cost
                remaining_usd -= level_cost

        filled_usd = target_size_usd - remaining_usd
        fill_ratio = filled_usd / target_size_usd
        c_exec_weighted = (accumulated_cost / accumulated_shares) if accumulated_shares > 0 else top_ask
        slippage_real = c_exec_weighted - top_ask

        return {
            "c_exec_weighted": float(c_exec_weighted),
            "fill_ratio": float(fill_ratio),
            "slippage_real": float(slippage_real),
            "filled_usd": float(filled_usd)
        }

    def run_replay_simulation(self, snapshot: Dict[str, Any], target_size_usd: float = 50.0) -> Dict[str, Any]:
        """
        Ejecuta la simulación de replay sobre un snapshot histórico L2.
        """
        asks = snapshot.get("asks", [[0.60, 50.0], [0.61, 100.0], [0.62, 200.0]])
        p_model = snapshot.get("p_model", 0.72)
        question = snapshot.get("question", "Evento Polymarket")

        fill_stats = self.walk_orderbook_depth(asks, target_size_usd)
        c_exec_w = fill_stats["c_exec_weighted"]
        fee_real = target_size_usd * self.taker_fee_pct
        
        # EV_net_realized = p_model - c_exec_weighted - fee - slippage
        ev_net_realized = p_model - c_exec_w - self.taker_fee_pct - fill_stats["slippage_real"]
        edge_survived = ev_net_realized > 0.015 and fill_stats["fill_ratio"] >= 0.95

        return {
            "question": question,
            "target_size_usd": target_size_usd,
            "p_model": p_model,
            "top_ask": float(asks[0][0]) if asks else 0.0,
            "c_exec_weighted": fill_stats["c_exec_weighted"],
            "fill_ratio": fill_stats["fill_ratio"],
            "slippage_real": fill_stats["slippage_real"],
            "fee_real_usd": fee_real,
            "ev_net_realized_pct": float(ev_net_realized * 100),
            "edge_survived": bool(edge_survived),
            "latency_ms": self.latency_ms
        }
