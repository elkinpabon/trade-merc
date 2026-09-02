import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query(
      'SELECT id, level, module, message, timestamp FROM bot_logs ORDER BY id DESC LIMIT 30'
    );
    return NextResponse.json({ logs: rows || [] }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Live bot logs', error);
  }
}
