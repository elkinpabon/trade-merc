import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

const TARGET_DAYS = 30;
const MIN_COVERAGE_PCT = 99;
const MIN_CLOSED_TRADES = 100;
const CYCLE_SECONDS = 15 * 60;

function parseJson<T>(value: unknown, fallback: T): T {
  try {
    return value ? JSON.parse(String(value)) as T : fallback;
  } catch {
    return fallback;
  }
}

function sameConfigValue(current: unknown, captured: unknown) {
  if (current === null || current === undefined || captured === null || captured === undefined) {
    return current == null && captured == null;
  }
  if (current instanceof Date && typeof captured === 'string') {
    return current.getTime() === new Date(captured).getTime();
  }
  if (typeof captured === 'number') return toNumber(current) === captured;
  if (typeof captured === 'boolean') return Boolean(current) === captured;
  return String(current) === String(captured);
}

export async function GET() {
  try {
    const pool = getDbPool();
    const [runRows]: any = await pool.query(`SELECT * FROM strategy_runs
      WHERE run_type = 'EXPERIMENT' ORDER BY started_at DESC LIMIT 1`);
    const run = runRows?.[0];

    if (!run) {
      return NextResponse.json({ error: 'No current experiment exists' }, { status: 404 });
    }

    const startedAt = new Date(run.started_at);
    const plannedEndAt = run.planned_end_at
      ? new Date(run.planned_end_at)
      : new Date(startedAt.getTime() + TARGET_DAYS * 86_400_000);
    const finishedAt = run.finished_at ? new Date(run.finished_at) : null;
    const now = new Date();
    const reportEnd = finishedAt || now;
    const effectiveEnd = new Date(Math.min(reportEnd.getTime(), plannedEndAt.getTime()));
    const attributionEnd = finishedAt || now;
    const botRunFilter = ` AND bot_run_id IN (
      SELECT bot_run_id FROM worker_cycles WHERE strategy_run_id = ?
    )`;
    const evaluationParams = [run.model_version_id, startedAt, attributionEnd, run.id];
    const signalParams = [startedAt, attributionEnd, run.id];

    const [
      [[tradeTotals]], [[orderTotals]], [[fillTotals]], [[positionTotals]],
      [snapshotRows], [[dailyTotals]], [[cycleTotals]], [[evaluationTotals]],
      [[signalTotals]], [configRows],
    ]: any = await Promise.all([
      pool.query(`SELECT COUNT(*) AS closed_trades,
        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) AS losses,
        COALESCE(SUM(realized_pnl), 0) AS net_pnl,
        COALESCE(SUM(total_fee), 0) AS fees,
        COALESCE(SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END), 0) AS gross_profit,
        ABS(COALESCE(SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END), 0)) AS gross_loss
        FROM trades WHERE strategy_run_id = ?`, [run.id]),
      pool.query(`SELECT COUNT(*) AS orders,
        SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) AS filled_orders
        FROM paper_orders WHERE strategy_run_id = ?`, [run.id]),
      pool.query('SELECT COUNT(*) AS fills FROM paper_fills WHERE strategy_run_id = ?', [run.id]),
      pool.query(`SELECT COUNT(*) AS positions,
        SUM(CASE WHEN is_open = 1 THEN 1 ELSE 0 END) AS open_positions
        FROM paper_positions WHERE strategy_run_id = ?`, [run.id]),
      pool.query(`SELECT timestamp, total_equity FROM portfolio_snapshots
        WHERE strategy_run_id = ? ORDER BY timestamp ASC`, [run.id]),
      pool.query('SELECT COUNT(*) AS days_with_metrics FROM run_daily_metrics WHERE run_id = ?', [run.id]),
      pool.query(`SELECT COUNT(*) AS recorded_cycles,
        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_cycles
        FROM worker_cycles WHERE strategy_run_id = ?`, [run.id]),
      pool.query(`SELECT COUNT(*) AS evaluations FROM strategy_evaluations
        WHERE model_version_id = ? AND decision_at >= ? AND decision_at <= ?${botRunFilter}`, evaluationParams),
      pool.query(`SELECT COUNT(*) AS signals FROM signals
        WHERE timestamp >= ? AND timestamp <= ?${botRunFilter}`, signalParams),
      run.config_id ? pool.query('SELECT * FROM bot_configs WHERE id = ? LIMIT 1', [run.config_id]) : Promise.resolve([[]]),
    ]);

    let peak = 0;
    let maxDrawdown = 0;
    for (const snapshot of snapshotRows || []) {
      const equity = toNumber(snapshot.total_equity);
      peak = Math.max(peak, equity);
      if (peak > 0) maxDrawdown = Math.max(maxDrawdown, ((peak - equity) / peak) * 100);
    }

    const elapsedMilliseconds = Math.max(0, effectiveEnd.getTime() - startedAt.getTime());
    const elapsedDays = Math.max(1, Math.floor(elapsedMilliseconds / 86_400_000) + 1);
    const coveredTargetDays = Math.min(TARGET_DAYS, elapsedDays);
    const daysWithMetrics = toNumber(dailyTotals.days_with_metrics);
    const coveragePct = Math.min(100, (daysWithMetrics / coveredTargetDays) * 100);
    const expectedCycles = Math.max(1, Math.floor(elapsedMilliseconds / (CYCLE_SECONDS * 1000)) + 1);
    const successfulCycles = toNumber(cycleTotals.successful_cycles);
    const cycleCoveragePct = Math.min(100, (successfulCycles / expectedCycles) * 100);
    const closedTrades = toNumber(tradeTotals.closed_trades);
    const netPnl = toNumber(tradeTotals.net_pnl);
    const fees = toNumber(tradeTotals.fees);
    const grossProfit = toNumber(tradeTotals.gross_profit);
    const grossLoss = toNumber(tradeTotals.gross_loss);
    const capturedConfig = parseJson<Record<string, unknown>>(run.config_snapshot_json, {});
    const currentConfig = configRows?.[0];
    const configUnchanged = Boolean(currentConfig) && Object.entries(capturedConfig)
      .every(([key, value]) => key in currentConfig && sameConfigValue(currentConfig[key], value));
    const criteria = {
      duration_30_days: reportEnd.getTime() >= plannedEndAt.getTime(),
      daily_coverage_at_least_99_pct: coveragePct >= MIN_COVERAGE_PCT,
      cycle_coverage_at_least_99_pct: cycleCoveragePct >= MIN_COVERAGE_PCT,
      at_least_100_closed_trades: closedTrades >= MIN_CLOSED_TRADES,
      no_open_attributed_position: toNumber(positionTotals.open_positions) === 0,
      configuration_unchanged: configUnchanged,
    };

    return NextResponse.json({
      run: {
        id: run.id,
        status: run.status,
        model_version_id: run.model_version_id,
        symbols: parseJson<string[]>(run.symbols_json, []),
        timeframe: run.timeframe,
        started_at: startedAt,
        planned_end_at: plannedEndAt,
        finished_at: finishedAt,
      },
      coverage: {
        target_days: TARGET_DAYS,
        elapsed_days: elapsedDays,
        progress_pct: Math.min(100, (elapsedMilliseconds / (TARGET_DAYS * 86_400_000)) * 100),
        days_with_metrics: daysWithMetrics,
        coverage_pct: Number(coveragePct.toFixed(2)),
        expected_cycles: expectedCycles,
        recorded_cycles: toNumber(cycleTotals.recorded_cycles),
        successful_cycles: successfulCycles,
        cycle_coverage_pct: Number(cycleCoveragePct.toFixed(2)),
      },
      funnel: {
        evaluations: toNumber(evaluationTotals.evaluations),
        signals: toNumber(signalTotals.signals),
        orders: toNumber(orderTotals.orders),
        filled_orders: toNumber(orderTotals.filled_orders),
        fills: toNumber(fillTotals.fills),
        closed_trades: closedTrades,
      },
      performance: {
        net_pnl: netPnl,
        gross_pnl_before_fees: netPnl + fees,
        profit_factor: grossLoss ? grossProfit / grossLoss : (grossProfit ? null : 0),
        expectancy: closedTrades ? netPnl / closedTrades : 0,
        fees,
        wins: toNumber(tradeTotals.wins),
        losses: toNumber(tradeTotals.losses),
        max_drawdown_pct: maxDrawdown,
      },
      evaluability: {
        evaluable: Object.values(criteria).every(Boolean),
        criteria,
      },
    }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Experiment report', error);
  }
}
