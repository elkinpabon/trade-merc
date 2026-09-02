import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  if (process.env.POLYMARKET_INFRASTRUCTURE_ENABLED !== 'true') {
    return NextResponse.json({
      available: false,
      error: 'Polymarket infrastructure is not configured',
    }, { status: 503 });
  }
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query("SELECT * FROM polymarket_runs WHERE status = 'running' LIMIT 1");
    const isRunning = rows && rows.length > 0;
    return NextResponse.json({
      is_running: isRunning,
      available: true,
      bot_run_id: isRunning ? rows[0].id : null,
      mode: isRunning ? rows[0].mode || null : null,
    }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Polymarket status', error);
  }
}
