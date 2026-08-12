import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    is_running: true,
    mode: 'paper',
    active_run: {
      id: 'run-tidb-001',
      status: 'running',
      started_at: new Date().toISOString()
    },
    config: {
      mode: 'paper',
      timeframe: '5m',
      ema_fast_period: 9,
      ema_slow_period: 21,
      rsi_period: 14,
      stop_loss_pct: 2.0,
      take_profit_pct: 4.0
    }
  }, { status: 200 });
}
