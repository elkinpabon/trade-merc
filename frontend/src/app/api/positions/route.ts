import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM paper_positions WHERE is_open = TRUE ORDER BY opened_at DESC');
    return NextResponse.json((rows || []).map((row: any) => ({
      ...row,
      quantity: toNumber(row.quantity),
      entry_price: toNumber(row.entry_price),
      current_price: toNumber(row.current_price),
      unrealized_pnl: toNumber(row.unrealized_pnl),
      unrealized_pnl_pct: toNumber(row.unrealized_pnl_pct),
      stop_loss_price: row.stop_loss_price == null ? null : toNumber(row.stop_loss_price),
      take_profit_price: row.take_profit_price == null ? null : toNumber(row.take_profit_price),
      is_open: Boolean(row.is_open),
    })), { status: 200 });
  } catch (error) {
    return serviceUnavailable('Positions', error);
  }
}
