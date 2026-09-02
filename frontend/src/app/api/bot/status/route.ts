import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [[configRows], [runRows]]: any = await Promise.all([
      pool.query('SELECT * FROM bot_configs ORDER BY id LIMIT 1'),
      pool.query("SELECT * FROM bot_runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"),
    ]);
    const config = configRows?.[0];
    const activeRun = runRows?.[0] || null;

    return NextResponse.json({
      is_running: Boolean(activeRun),
      mode: config?.mode || null,
      active_run: activeRun,
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
