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
    const [rows]: any = await pool.query('SELECT * FROM polymarket_positions WHERE is_active = TRUE ORDER BY opened_at DESC');
    return NextResponse.json((rows || []).map((row: any) => ({
      ...row,
      contract_price: toNumber(row.contract_price),
      shares: toNumber(row.shares),
      total_cost: toNumber(row.total_cost),
      current_prob: toNumber(row.current_prob),
      unrealized_pnl: toNumber(row.unrealized_pnl),
      is_active: Boolean(row.is_active),
    })), { status: 200 });
  } catch (error) {
    return serviceUnavailable('Polymarket positions', error);
  }
}

export async function POST() {
  return NextResponse.json({
    success: false,
    error: 'Polymarket execution infrastructure is not implemented',
  }, { status: 501 });
}
