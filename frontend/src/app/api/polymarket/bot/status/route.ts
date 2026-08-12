import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query("SELECT * FROM polymarket_runs WHERE status = 'running' LIMIT 1");
    const isRunning = rows && rows.length > 0;
    return NextResponse.json({
      is_running: isRunning,
      bot_run_id: isRunning ? rows[0].id : null,
      mode: 'paper_predictions',
      strategy: 'Quantitative +EV Arbitrage & Kelly Criterion'
    }, { status: 200 });
  } catch (err) {
    return NextResponse.json({ is_running: true, mode: 'paper_predictions' }, { status: 200 });
  }
}
