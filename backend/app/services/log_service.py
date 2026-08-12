from app.extensions import db
from app.models import BotLog
from app.utils.helpers import utc_now

class LogService:
    """
    Centralized Bot & System Logging Service.
    Persists structured logs to MySQL and formats them for websocket streaming.
    """

    @staticmethod
    def log(level: str, module: str, message: str) -> BotLog:
        level = level.upper()
        log_entry = BotLog(
            level=level,
            module=module,
            message=message,
            timestamp=utc_now()
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry

    @staticmethod
    def get_recent_logs(limit: int = 100, level: str = None) -> list[dict]:
        query = BotLog.query
        if level:
            query = query.filter_by(level=level.upper())
        logs = query.order_by(BotLog.timestamp.desc()).limit(limit).all()
        return [l.to_dict() for l in logs]
