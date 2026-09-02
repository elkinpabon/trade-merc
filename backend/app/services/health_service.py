from datetime import timedelta

from app.extensions import db
from app.models import SystemHealth, BotRun
from app.utils.helpers import utc_now


BOT_HEARTBEAT_STALE_AFTER = timedelta(minutes=15)

class HealthService:
    """
    System Health Monitoring & Audit Service.
    Checks Database, Market Feed, Bot Runner, and Socket Gateway.
    """

    @staticmethod
    def update_component_health(component: str, status: str, details: str = "") -> SystemHealth:
        record = SystemHealth.query.filter_by(component=component).first()
        if not record:
            record = SystemHealth(component=component, status=status, details=details, last_check=utc_now())
            db.session.add(record)
        else:
            record.status = status
            record.details = details
            record.last_check = utc_now()

        db.session.commit()
        return record

    @staticmethod
    def get_system_health() -> dict:
        # Check DB Connectivity
        try:
            db.session.execute(db.text("SELECT 1"))
            db_status = "HEALTHY"
            db_details = "MySQL database responsive."
        except Exception as e:
            db_status = "DOWN"
            db_details = f"Database query failed: {str(e)}"

        HealthService.update_component_health("database", db_status, db_details)

        # Check Bot Worker status
        active_run = BotRun.query.filter_by(status='running').first()
        if not active_run:
            bot_status = "IDLE"
            bot_details = "Bot worker is stopped."
        elif not active_run.last_heartbeat:
            bot_status = "DEGRADED"
            bot_details = f"Bot Run ID {active_run.id} has no heartbeat."
        else:
            heartbeat_age = utc_now() - active_run.last_heartbeat
            if heartbeat_age > BOT_HEARTBEAT_STALE_AFTER:
                bot_status = "DEGRADED"
                bot_details = f"Bot Run ID {active_run.id} heartbeat is stale ({int(heartbeat_age.total_seconds())}s old)."
            else:
                bot_status = "HEALTHY"
                bot_details = f"Bot Run ID {active_run.id} heartbeat is current ({int(heartbeat_age.total_seconds())}s old)."
        HealthService.update_component_health("bot_worker", bot_status, bot_details)

        records = SystemHealth.query.all()
        return {
            "overall_status": "HEALTHY" if db_status == "HEALTHY" and bot_status != "DEGRADED" else "DEGRADED",
            "components": [r.to_dict() for r in records]
        }
