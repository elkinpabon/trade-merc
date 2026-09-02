import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

const numericFields = [
  'virtual_balance', 'rsi_entry_threshold', 'stop_loss_pct', 'take_profit_pct',
  'risk_per_trade_pct', 'slippage_pct', 'fee_pct',
] as const;

function serializeConfig(config: any) {
  return {
    ...config,
    symbols: config.symbols ? String(config.symbols).split(',') : [],
    ...Object.fromEntries(numericFields.map((field) => [field, toNumber(config[field])])),
    is_active: Boolean(config.is_active),
  };
}

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM bot_configs ORDER BY id LIMIT 1');
    if (!rows?.[0]) {
      return NextResponse.json({ error: 'Bot configuration not found' }, { status: 404 });
    }
    return NextResponse.json(serializeConfig(rows[0]), { status: 200 });
  } catch (error) {
    return serviceUnavailable('Bot configuration', error);
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const allowedFields = [
      'name', 'exchange_id', 'mode', 'symbols', 'timeframe', 'virtual_balance',
      'ema_fast_period', 'ema_slow_period', 'rsi_period', 'rsi_entry_threshold',
      'stop_loss_pct', 'take_profit_pct', 'risk_per_trade_pct', 'slippage_pct',
      'fee_pct', 'cooldown_seconds', 'candle_limit', 'polling_interval_seconds', 'is_active',
    ];
    const updates = Object.entries(body).filter(([field]) => allowedFields.includes(field));
    if (updates.length === 0) {
      return NextResponse.json({ error: 'No valid configuration fields supplied' }, { status: 400 });
    }
    const pool = getDbPool();
    const [experimentRows]: any = await pool.query(
      "SELECT id FROM strategy_runs WHERE run_type = 'EXPERIMENT' AND status = 'RUNNING' LIMIT 1"
    );
    if (experimentRows?.[0]) {
      return NextResponse.json({ error: 'La configuración está congelada durante el experimento de 30 días.' }, { status: 409 });
    }
    const [configRows]: any = await pool.query('SELECT id FROM bot_configs ORDER BY id LIMIT 1');
    if (!configRows?.[0]) {
      return NextResponse.json({ error: 'Bot configuration not found' }, { status: 404 });
    }
    const values = updates.map(([field, value]) => field === 'symbols' && Array.isArray(value) ? value.join(',') : value);
    await pool.query(
      `UPDATE bot_configs SET ${updates.map(([field]) => `\`${field}\` = ?`).join(', ')} WHERE id = ?`,
      [...values, configRows[0].id]
    );
    const [updatedRows]: any = await pool.query('SELECT * FROM bot_configs WHERE id = ?', [configRows[0].id]);
    return NextResponse.json({ success: true, config: serializeConfig(updatedRows[0]) }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Bot configuration update', error);
  }
}
