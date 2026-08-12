from flask_socketio import emit
from app.extensions import socketio
from app.services.health_service import HealthService
from app.services.portfolio_service import PortfolioService
from app.models import BotConfig

@socketio.on('connect')
def handle_connect():
    emit('system_log', {'level': 'INFO', 'message': 'Client connected to TradeMerc WebSocket Gateway.'})
    # Emit initial system state
    health = HealthService.get_system_health()
    emit('health_update', health)

@socketio.on('disconnect')
def handle_disconnect():
    pass

@socketio.on('request_snapshot')
def handle_snapshot_request():
    config = BotConfig.query.first()
    if config:
        portfolio_svc = PortfolioService(config)
        summary = portfolio_svc.get_summary()
        emit('portfolio_updated', summary)

def broadcast_event(event_name: str, data: dict):
    """Utility to push real-time events to all connected WebSocket clients."""
    socketio.emit(event_name, data)
