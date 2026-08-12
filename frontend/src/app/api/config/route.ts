import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM bot_configs LIMIT 1');
    if (rows && rows.length > 0) {
      return NextResponse.json(rows[0], { status: 200 });
    }
  } catch (err) {
    console.warn("DB bot_config query fallback:", err);
  }

  return NextResponse.json({
    id: 'cfg-1',
    mode: 'paper',
    exchange_id: 'binance',
    symbols: 'BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT',
    timeframe: '5m',
    polling_interval_seconds: 1,
    ema_fast_period: 9,
    ema_slow_period: 21,
    rsi_period: 14,
    rsi_entry_threshold: 50,
    stop_loss_pct: 2.0,
    take_profit_pct: 4.0,
    risk_per_trade_pct: 2.0,
    max_open_positions: 5,
    candle_limit: 100,
    cooldown_seconds: 60,
    is_active: true
  }, { status: 200 });
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    return NextResponse.json({ success: true, config: body }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err?.message }, { status: 500 });
  }
}
