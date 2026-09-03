import os

DEFAULT_50_SYMBOLS = list(dict.fromkeys([
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT",
    "LINK/USDT", "DOT/USDT", "MATIC/USDT", "NEAR/USDT", "SHIB/USDT", "LTC/USDT", "UNI/USDT", "ATOM/USDT",
    "ETC/USDT", "BCH/USDT", "APT/USDT", "SUI/USDT", "FET/USDT", "RNDR/USDT", "INJ/USDT", "TIA/USDT",
    "OP/USDT", "ARB/USDT", "STX/USDT", "FIL/USDT", "ICP/USDT", "PEPE/USDT", "WIF/USDT",
    "FLOKI/USDT", "BONK/USDT", "AAVE/USDT", "GRT/USDT", "THETA/USDT", "RUNE/USDT", "LDO/USDT", "ALGO/USDT",
    "EGLD/USDT", "FLOW/USDT", "CHZ/USDT", "EOS/USDT", "QNT/USDT", "GALA/USDT", "SAND/USDT", "MANA/USDT",
    "AXS/USDT", "KSM/USDT"
]))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trademerc-secret-key-2026-prod')
    
    DB_USER = os.environ.get('DB_USER', '3RWNAdLev5dv3er.root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'VSGF3kkVfo4CEIu9')
    DB_HOST = os.environ.get('DB_HOST', 'gateway01.us-east-1.prod.aws.tidbcloud.com')
    DB_PORT = os.environ.get('DB_PORT', '4000')
    DB_NAME = os.environ.get('DB_NAME', 'trademerc_db')
    
    ca_cert_path = os.path.join(os.path.dirname(__file__), '..', 'CA_cert', 'isrgrootx1.pem')
    has_ca = os.path.exists(ca_cert_path)
    
    db_url = os.environ.get(
        'DATABASE_URL',
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    SQLALCHEMY_DATABASE_URI = db_url
    
    ssl_config = {}
    if has_ca and db_url.startswith('mysql'):
        ssl_config = {"ssl": {"ca": ca_cert_path, "check_hostname": False}}
    elif "tidbcloud.com" in db_url:
        ssl_config = {"ssl": {"ssl_mode": "VERIFY_IDENTITY"}}
        
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": ssl_config
    } if ssl_config else {}
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAPER_TRADING_ENABLED = os.environ.get('PAPER_TRADING_ENABLED', 'true').lower() == 'true'
    LIVE_TRADING_ENABLED = os.environ.get('LIVE_TRADING_ENABLED', 'false').lower() == 'true'
    WORKER_TRIGGER_TOKEN = os.environ.get('WORKER_TRIGGER_TOKEN')
    
    DEFAULT_EXCHANGE = 'binance'
    DEFAULT_SYMBOLS = ",".join(DEFAULT_50_SYMBOLS)
    DEFAULT_TIMEFRAME = '5m'
    DEFAULT_VIRTUAL_BALANCE = 100.00
