import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json({
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate_pct: 0.0,
    total_pnl: 0.00,
    profit_factor: 1.0,
    average_trade_pnl: 0.00,
    max_drawdown_pct: 0.00,
    equity_curve: [
      { timestamp: new Date(Date.now() - 86400000).toISOString(), equity: 100.00 },
      { timestamp: new Date().toISOString(), equity: 100.00 }
    ]
  }, { status: 200 });
}
