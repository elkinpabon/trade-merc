import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const limit = Number(new URL(request.url).searchParams.get('limit') || 50);
  if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
    return NextResponse.json({ error: 'limit must be an integer between 1 and 200' }, { status: 400 });
  }

  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM trades ORDER BY closed_at DESC LIMIT ?', [limit]);
    return NextResponse.json((rows || []).map((row: any) => ({
      ...row,
      entry_price: toNumber(row.entry_price),
      exit_price: toNumber(row.exit_price),
      quantity: toNumber(row.quantity),
      realized_pnl: toNumber(row.realized_pnl),
      realized_pnl_pct: toNumber(row.realized_pnl_pct),
      total_fee: toNumber(row.total_fee),
    })), { status: 200 });
  } catch (error) {
    return serviceUnavailable('Trades', error);
  }
}
