import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

const numericTrade = (row: any) => row ? ({
  ...row,
  entry_price: toNumber(row.entry_price),
  exit_price: toNumber(row.exit_price),
  quantity: toNumber(row.quantity),
  realized_pnl: toNumber(row.realized_pnl),
  realized_pnl_pct: toNumber(row.realized_pnl_pct),
  total_fee: toNumber(row.total_fee),
}) : null;

const numericPosition = (row: any) => ({
  ...row,
  quantity: toNumber(row.quantity),
  entry_price: toNumber(row.entry_price),
  current_price: toNumber(row.current_price),
  unrealized_pnl: toNumber(row.unrealized_pnl),
  unrealized_pnl_pct: toNumber(row.unrealized_pnl_pct),
  stop_loss_price: row.stop_loss_price == null ? null : toNumber(row.stop_loss_price),
  take_profit_price: row.take_profit_price == null ? null : toNumber(row.take_profit_price),
  is_open: Boolean(row.is_open),
});

export async function GET() {
  try {
    const pool = getDbPool();
    const [
      [configRows], [runRows], [snapshotRows], [positionRows], [tradeRows],
      [lastSignalRows], [alertRows], [tradeStatsRows], [healthRows],
    ]: any = await Promise.all([
      pool.query('SELECT * FROM bot_configs ORDER BY id LIMIT 1'),
      pool.query("SELECT * FROM bot_runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"),
      pool.query('SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 1'),
      pool.query('SELECT * FROM paper_positions WHERE is_open = TRUE ORDER BY opened_at DESC'),
      pool.query('SELECT * FROM trades ORDER BY closed_at DESC LIMIT 10'),
      pool.query('SELECT * FROM signals ORDER BY timestamp DESC LIMIT 1'),
      pool.query('SELECT * FROM risk_events ORDER BY timestamp DESC LIMIT 5'),
      pool.query(`SELECT COUNT(*) AS total_trades,
        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS winning_trades
        FROM trades`),
      pool.query('SELECT id, component, status, details, last_check FROM system_health ORDER BY component'),
    ]);

    const config = configRows?.[0];
    if (!config) {
      return NextResponse.json({ error: 'Bot configuration not found' }, { status: 404 });
    }

    const snapshot = snapshotRows?.[0];
    const positions = (positionRows || []).map(numericPosition);
    const recentTrades = (tradeRows || []).map(numericTrade);
    const totalTrades = toNumber(tradeStatsRows?.[0]?.total_trades);
    const winningTrades = toNumber(tradeStatsRows?.[0]?.winning_trades);
    const cashBalance = snapshot ? toNumber(snapshot.cash_balance) : toNumber(config.virtual_balance);
    const positionsValue = snapshot
      ? toNumber(snapshot.positions_value)
      : positions.reduce((total: number, position: any) => total + position.quantity * position.current_price, 0);
    const components = [
      {
        id: 0,
        component: 'database',
        status: 'HEALTHY',
        details: 'Dashboard queries completed successfully.',
        last_check: new Date().toISOString(),
      },
      ...(healthRows || []).filter((row: any) => row.component !== 'database'),
    ];
    const overallStatus = components.some((component: any) => component.status === 'DOWN')
      ? 'DOWN'
      : components.some((component: any) => component.status === 'DEGRADED') ? 'DEGRADED' : 'HEALTHY';

    return NextResponse.json({
      bot_status: runRows?.[0] ? 'RUNNING' : 'STOPPED',
      mode: config.mode,
      exchange: config.exchange_id,
      active_symbols: config.symbols ? String(config.symbols).split(',') : [],
      portfolio: {
        cash_balance: cashBalance,
        positions_value: positionsValue,
        total_equity: snapshot ? toNumber(snapshot.total_equity) : cashBalance + positionsValue,
        realized_pnl: snapshot ? toNumber(snapshot.realized_pnl) : 0,
        unrealized_pnl: snapshot
          ? toNumber(snapshot.unrealized_pnl)
          : positions.reduce((total: number, position: any) => total + position.unrealized_pnl, 0),
        peak_equity: snapshot ? toNumber(snapshot.peak_equity) : cashBalance + positionsValue,
        drawdown_pct: snapshot ? toNumber(snapshot.drawdown_pct) : 0,
        total_trades: totalTrades,
        win_rate: totalTrades ? (winningTrades / totalTrades) * 100 : 0,
        open_positions_count: positions.length,
        positions,
        recent_trades: recentTrades,
      },
      last_signal: lastSignalRows?.[0] ? { ...lastSignalRows[0], price: toNumber(lastSignalRows[0].price) } : null,
      last_trade: recentTrades[0] || null,
      recent_alerts: alertRows || [],
      health: { overall_status: overallStatus, components },
    }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Dashboard data', error);
  }
}
