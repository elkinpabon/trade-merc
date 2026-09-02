import { randomUUID } from 'crypto';
import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function POST() {
  const pool = getDbPool();
  let connection;
  try {
    connection = await pool.getConnection();
    await connection.beginTransaction();
    const [configRows]: any = await connection.query('SELECT id, mode FROM bot_configs ORDER BY id LIMIT 1 FOR UPDATE');
    if (!configRows?.[0]) {
      await connection.rollback();
      return NextResponse.json({ success: false, error: 'Bot configuration not found' }, { status: 404 });
    }
    const [runRows]: any = await connection.query(
      "SELECT id FROM bot_runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
    );
    if (runRows?.[0]) {
      await connection.rollback();
      return NextResponse.json({ success: true, message: 'Bot is already running.', run_id: runRows[0].id }, { status: 200 });
    }

    const runId = randomUUID();
    await connection.query(
      "INSERT INTO bot_runs (id, config_id, status, started_at, last_heartbeat) VALUES (?, ?, 'running', NOW(), NOW())",
      [runId, configRows[0].id]
    );
    await connection.query('UPDATE bot_configs SET is_active = TRUE WHERE id = ?', [configRows[0].id]);
    await connection.query(
      'INSERT INTO bot_logs (level, module, message, timestamp) VALUES (?, ?, ?, NOW())',
      ['INFO', 'BotController', `Bot run ${runId} started in ${configRows[0].mode} mode.`]
    );
    await connection.commit();
    return NextResponse.json({ success: true, message: 'Bot started successfully.', run_id: runId }, { status: 200 });
  } catch (error) {
    if (connection) await connection.rollback();
    return serviceUnavailable('Bot start', error);
  } finally {
    connection?.release();
  }
}
