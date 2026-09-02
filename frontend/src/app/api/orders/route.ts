import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM paper_orders ORDER BY created_at DESC LIMIT 50');
    return NextResponse.json((rows || []).map((row: any) => ({
      ...row,
      quantity: toNumber(row.quantity),
      requested_price: toNumber(row.requested_price),
      simulated_fee: toNumber(row.simulated_fee),
      simulated_slippage: toNumber(row.simulated_slippage),
    })), { status: 200 });
  } catch (error) {
    return serviceUnavailable('Orders', error);
  }
}
