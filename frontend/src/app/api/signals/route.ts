import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable, toNumber } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM signals ORDER BY timestamp DESC LIMIT 50');
    return NextResponse.json((rows || []).map((row: any) => ({
      ...row,
      price: toNumber(row.price),
    })), { status: 200 });
  } catch (error) {
    return serviceUnavailable('Signals', error);
  }
}
