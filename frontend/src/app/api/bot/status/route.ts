import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

const WORKER_FRESHNESS_MS = 25 * 60 * 1000;

export async function GET() {
  try {
    const pool = getDbPool();
    const [[configRows], [runRows], [experimentRows]]: any = await Promise.all([
      pool.query('SELECT * FROM bot_configs ORDER BY id LIMIT 1'),
      pool.query("SELECT * FROM bot_runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"),
      pool.query("SELECT id FROM strategy_runs WHERE run_type = 'EXPERIMENT' AND status = 'RUNNING' ORDER BY started_at DESC LIMIT 1"),
    ]);
    const config = configRows?.[0];
    const activeRun = runRows?.[0] || null;
    let latestCycle = null;
    if (activeRun) {
      const [cycleRows]: any = await pool.query(
        "SELECT id, status, started_at, finished_at, error_message FROM worker_cycles WHERE bot_run_id = ? AND status = 'SUCCESS' ORDER BY finished_at DESC LIMIT 1",
        [activeRun.id]
      );
      latestCycle = cycleRows?.[0] || null;
    }
    const now = Date.now();
    const heartbeatAt = activeRun?.last_heartbeat ? new Date(activeRun.last_heartbeat).getTime() : NaN;
    const cycleFinishedAt = latestCycle?.finished_at ? new Date(latestCycle.finished_at).getTime() : NaN;
    const heartbeatAge = now - heartbeatAt;
    const cycleAge = now - cycleFinishedAt;
    const heartbeatFresh = Number.isFinite(heartbeatAge) && heartbeatAge >= 0 && heartbeatAge <= WORKER_FRESHNESS_MS;
    const cycleFresh = latestCycle?.status === 'SUCCESS'
      && Number.isFinite(cycleAge)
      && cycleAge >= 0
      && cycleAge <= WORKER_FRESHNESS_MS;

    return NextResponse.json({
      is_running: Boolean(activeRun && heartbeatFresh && cycleFresh),
      mode: config?.mode || null,
      active_run: activeRun,
      latest_cycle: latestCycle,
      worker_status: !activeRun ? 'STOPPED' : heartbeatFresh && cycleFresh ? 'RUNNING' : 'DEGRADED',
      active_experiment_id: experimentRows?.[0]?.id || null,
      config: config ? {
        ...config,
        symbols: config.symbols ? String(config.symbols).split(',') : [],
        virtual_balance: toNumber(config.virtual_balance),
        rsi_entry_threshold: toNumber(config.rsi_entry_threshold),
        stop_loss_pct: toNumber(config.stop_loss_pct),
        take_profit_pct: toNumber(config.take_profit_pct),
        risk_per_trade_pct: toNumber(config.risk_per_trade_pct),
        slippage_pct: toNumber(config.slippage_pct),
        fee_pct: toNumber(config.fee_pct),
        is_active: Boolean(config.is_active),
      } : null,
    }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Bot status', error);
  }
}
