from flask import Flask
from app.routes.health import health_bp
from app.routes.bot import bot_bp
from app.routes.config import config_bp
from app.routes.dashboard import dashboard_bp
from app.routes.market import market_bp
from app.routes.trades import trades_bp
from app.routes.analytics import analytics_bp
from app.routes.logs import logs_bp
from app.routes.exchange import exchange_bp
from app.routes.auth import auth_bp
from app.routes.cron import cron_bp

def register_routes(app: Flask):
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(bot_bp, url_prefix='/api')
    app.register_blueprint(config_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')
    app.register_blueprint(market_bp, url_prefix='/api')
    app.register_blueprint(trades_bp, url_prefix='/api')
    app.register_blueprint(analytics_bp, url_prefix='/api')
    app.register_blueprint(logs_bp, url_prefix='/api')
    app.register_blueprint(exchange_bp, url_prefix='/api')
    app.register_blueprint(cron_bp, url_prefix='/api')
