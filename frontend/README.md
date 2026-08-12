# TradeMerc Frontend (Next.js / TypeScript / Tailwind CSS / TradingView Lightweight Charts)

High-Performance Quantitative Trading Terminal UI.

## Features
- **Trading Control Center**: Start/Stop engine, Paper Trading badge, real-time Socket.IO gateway connection status.
- **Financial Terminal Dashboard**: Real-time Equity, PnL, Drawdown, Win Rate, and open paper positions.
- **Public Market Charting**: Interactive Lightweight Charts candlesticks for BTC/USDT & ETH/USDT.
- **Bot Strategy & Risk Controls**: Fine-tune EMA periods, RSI thresholds, Stop-Loss, Take-Profit, and position sizing.
- **Exchange Settings & Encryption**: Interface for testing API keys and private connectivity with Fernet AES local encryption.
- **Analytics & Equity Curves**: Cumulative return, drawdown curves, Profit Factor, and Sharpe Ratio.

## Setup Instructions
1. Install Node.js 18+
2. Install dependencies:
   ```bash
   npm install
   ```
3. Copy `.env.local.example` to `.env.local`.
4. Run development server:
   ```bash
   npm run dev
   ```
5. Open [http://localhost:3000](http://localhost:3000) in your browser.
