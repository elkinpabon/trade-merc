# TradeMerc Backend (Python / Flask / Flask-SocketIO / CCXT / MySQL)

Production-grade Algorithmic Crypto Paper Trading Platform Backend.

## Features
- **Public CCXT Market Ingestion**: Reads live Binance candles without API keys.
- **Execution Engine Abstraction**: `PaperExecutionEngine` (active) and `LiveExecutionEngine` (inactive, safety locked).
- **Technical Analysis Engine**: EMA Fast/Slow, RSI, Volume SMA, Crossovers.
- **Risk Control Engine**: Position sizing, Stop Loss, Take Profit, Max Drawdown limits, Circuit Breakers.
- **Persistance**: Full MySQL database model via SQLAlchemy and PyMySQL.
- **Realtime Gateway**: Flask-SocketIO event push for live terminal monitoring.

## Environment Setup
1. Install Python 3.10+
2. Create and start a MySQL database named `trademerc_db` locally.
3. Import `schema.sql` into MySQL:
   ```bash
   mysql -u root -p trademerc_db < schema.sql
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and adjust database credentials.
6. Run server and background bot worker:
   ```bash
   python run.py
   ```
