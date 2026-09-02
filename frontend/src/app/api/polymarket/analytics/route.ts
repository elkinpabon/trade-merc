import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  if (process.env.POLYMARKET_INFRASTRUCTURE_ENABLED !== 'true') {
    return NextResponse.json({ error: 'Polymarket infrastructure is not configured' }, { status: 503 });
  }
  try {
    const pool = getDbPool();
    const [[[positions]], [[trades]]]: any = await Promise.all([
      pool.query(`SELECT COUNT(*) AS active_contracts_count,
        COALESCE(SUM(shares * current_prob), 0) AS active_contracts_value,
        COALESCE(SUM(unrealized_pnl), 0) AS unrealized_pnl
        FROM polymarket_positions WHERE is_active = TRUE`),
      pool.query(`SELECT COUNT(*) AS total_predictions_resolved,
        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins,
        COALESCE(SUM(realized_pnl), 0) AS realized_pnl,
        COALESCE(SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END), 0) AS gross_profit,
        ABS(COALESCE(SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END), 0)) AS gross_loss
        FROM polymarket_trades`),
    ]);
    const resolved = toNumber(trades.total_predictions_resolved);
    const grossLoss = toNumber(trades.gross_loss);
    return NextResponse.json({
      active_contracts_count: toNumber(positions.active_contracts_count),
      active_contracts_value: toNumber(positions.active_contracts_value),
      unrealized_pnl: toNumber(positions.unrealized_pnl),
      realized_pnl: toNumber(trades.realized_pnl),
      total_predictions_resolved: resolved,
      prediction_win_rate_pct: resolved ? (toNumber(trades.wins) / resolved) * 100 : 0,
      profit_factor: grossLoss ? toNumber(trades.gross_profit) / grossLoss : toNumber(trades.gross_profit),
    }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Polymarket analytics', error);
  }
}
