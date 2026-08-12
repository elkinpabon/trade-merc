import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST() {
  try {
    const pool = getDbPool();
    const runId = `poly-run-${Date.now()}`;
    await pool.query("UPDATE polymarket_runs SET status = 'stopped'");
    await pool.query("INSERT INTO polymarket_runs (id, status, started_at) VALUES (?, 'running', NOW())", [runId]);
    await pool.query("INSERT INTO polymarket_logs (level, module, message, timestamp) VALUES ('INFO', 'BotControl', 'Bot de Predicción Polymarket +EV INICIADO', NOW())");
    return NextResponse.json({ success: true, message: 'Bot de Predicción Polymarket iniciado con éxito.', run_id: runId }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err?.message }, { status: 500 });
  }
}
