import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [experimentRows]: any = await pool.query(`SELECT id, status, started_at
      FROM strategy_runs WHERE run_type = 'EXPERIMENT' ORDER BY started_at DESC LIMIT 1`);
    const experiment = experimentRows?.[0] || null;
    const tradeFilter = experiment ? ' WHERE strategy_run_id = ?' : '';
    const snapshotFilter = experiment ? ' WHERE strategy_run_id = ?' : '';
    const params = experiment ? [experiment.id] : [];
    const [[[totals]], [snapshotRows], [symbolRows]]: any = await Promise.all([
      pool.query(`SELECT COUNT(*) AS total_trades,
        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS winning_trades,
        SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) AS losing_trades,
        COALESCE(SUM(realized_pnl), 0) AS total_pnl,
        COALESCE(SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END), 0) AS gross_profit,
        ABS(COALESCE(SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END), 0)) AS gross_loss
        FROM trades${tradeFilter}`, params),
      pool.query(`SELECT timestamp, total_equity, drawdown_pct FROM portfolio_snapshots${snapshotFilter} ORDER BY timestamp ASC`, params),
      pool.query(`SELECT symbol, COUNT(*) AS trades, COALESCE(SUM(realized_pnl), 0) AS pnl,
        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins
        FROM trades${tradeFilter} GROUP BY symbol ORDER BY symbol`, params),
    ]);

    const totalTrades = toNumber(totals.total_trades);
    const winningTrades = toNumber(totals.winning_trades);
    const grossProfit = toNumber(totals.gross_profit);
    const grossLoss = toNumber(totals.gross_loss);
    const dailyEquity = new Map<string, number>();
    for (const row of snapshotRows || []) {
      const timestamp = new Date(row.timestamp);
      const equity = Number(row.total_equity);
      if (Number.isFinite(timestamp.getTime()) && Number.isFinite(equity)) {
        dailyEquity.set(timestamp.toISOString().slice(0, 10), equity);
      }
    }
    const dailyValues = Array.from(dailyEquity.values());
    const returns = dailyValues.slice(1).flatMap((equity, index) => {
      const previousEquity = dailyValues[index];
      return previousEquity !== 0 ? [(equity - previousEquity) / previousEquity] : [];
    });
    let sharpeRatio = 0;
    if (returns.length > 1) {
      const mean = returns.reduce((sum: number, value: number) => sum + value, 0) / returns.length;
      const variance = returns.reduce((sum: number, value: number) => sum + ((value - mean) ** 2), 0) / (returns.length - 1);
      const deviation = Math.sqrt(variance);
      sharpeRatio = deviation ? (mean / deviation) * Math.sqrt(365) : 0;
    }

    return NextResponse.json({
      overview: {
        total_trades: totalTrades,
        winning_trades: winningTrades,
        losing_trades: toNumber(totals.losing_trades),
        win_rate: totalTrades ? (winningTrades / totalTrades) * 100 : 0,
        profit_factor: grossLoss ? grossProfit / grossLoss : grossProfit,
        total_pnl: toNumber(totals.total_pnl),
        max_drawdown_pct: Math.max(0, ...(snapshotRows || []).map((row: any) => toNumber(row.drawdown_pct))),
        sharpe_ratio: sharpeRatio,
      },
      equity_curve: (snapshotRows || []).map((row: any) => ({
        timestamp: row.timestamp,
        equity: toNumber(row.total_equity),
        drawdown: toNumber(row.drawdown_pct),
      })),
      symbol_breakdown: (symbolRows || []).map((row: any) => ({
        symbol: row.symbol,
        trades: toNumber(row.trades),
        pnl: toNumber(row.pnl),
        win_rate: toNumber(row.trades) ? (toNumber(row.wins) / toNumber(row.trades)) * 100 : 0,
      })),
      experiment: experiment ? {
        id: experiment.id,
        status: experiment.status,
        started_at: experiment.started_at,
      } : null,
    }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Analytics', error);
  }
}
