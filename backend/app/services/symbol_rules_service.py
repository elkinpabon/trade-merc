import ccxt
from app.extensions import db
from app.models import SymbolRule

class SymbolRulesService:
    """
    Fetches exchange trading rules (precision, step size, min notional) via CCXT
    and updates symbol_rules table.
    """

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id

    def sync_symbol_rules(self, symbols: list[str]) -> None:
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            client = exchange_class({'enableRateLimit': True})
            markets = client.load_markets()

            for sym in symbols:
                if sym in markets:
                    m = markets[sym]
                    limits = m.get('limits', {})
                    precision = m.get('precision', {})

                    min_notional = float(limits.get('cost', {}).get('min') or 10.0)
                    min_qty = float(limits.get('amount', {}).get('min') or 0.0001)
                    qty_prec = int(precision.get('amount') or 6)
                    price_prec = int(precision.get('price') or 2)

                    rule = SymbolRule.query.filter_by(symbol=sym).first()
                    if not rule:
                        rule = SymbolRule(
                            symbol=sym,
                            min_notional=min_notional,
                            min_qty=min_qty,
                            qty_precision=qty_prec,
                            price_precision=price_prec,
                        )
                        db.session.add(rule)
                    else:
                        rule.min_notional = min_notional
                        rule.min_qty = min_qty
                        rule.qty_precision = qty_prec
                        rule.price_precision = price_prec

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Warning: Could not sync symbol rules from exchange: {e}")
