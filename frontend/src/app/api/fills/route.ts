import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM paper_fills ORDER BY timestamp DESC LIMIT 50');
    return NextResponse.json((rows || []).map((row: any) => ({
      ...row,
      fill_price: toNumber(row.fill_price),
      fill_quantity: toNumber(row.fill_quantity),
      fee_amount: toNumber(row.fee_amount),
    })), { status: 200 });
  } catch (error) {
    return serviceUnavailable('Fills', error);
  }
}
