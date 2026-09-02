import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  if (process.env.POLYMARKET_INFRASTRUCTURE_ENABLED !== 'true') {
    return NextResponse.json({ error: 'Polymarket infrastructure is not configured' }, { status: 503 });
  }
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query(
      'SELECT id, level, module, message, timestamp FROM polymarket_logs ORDER BY id DESC LIMIT 30'
    );
    return NextResponse.json({ logs: rows || [] }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Polymarket logs', error);
  }
}
