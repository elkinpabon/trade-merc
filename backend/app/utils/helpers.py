import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def round_qty(quantity: float, precision: int = 6) -> float:
    step = Decimal(1).scaleb(-precision)
    return float(Decimal(str(quantity)).quantize(step, rounding=ROUND_DOWN))

def round_price(price: float, precision: int = 2) -> float:
    return round(price, precision)

def format_iso(dt: datetime) -> str:
    if not dt:
        return ""
    return dt.isoformat() + "Z"
