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
    const [experimentRows]: any = await connection.query(
      "SELECT id FROM strategy_runs WHERE run_type = 'EXPERIMENT' AND status = 'RUNNING' LIMIT 1 FOR UPDATE"
    );
    if (experimentRows?.[0]) {
      await connection.rollback();
      return NextResponse.json({
        success: false,
        error: `El experimento ${experimentRows[0].id} está RUNNING; start/stop está bloqueado para preservar su validez.`,
      }, { status: 409 });
    }
    const [runRows]: any = await connection.query(
      "SELECT id FROM bot_runs WHERE status = 'running' FOR UPDATE"
    );
    await connection.query("UPDATE bot_runs SET status = 'stopped', stopped_at = NOW() WHERE status = 'running'");
    await connection.query('UPDATE bot_configs SET is_active = FALSE');
    if (runRows.length > 0) {
      await connection.query(
        'INSERT INTO bot_logs (level, module, message, timestamp) VALUES (?, ?, ?, NOW())',
        ['INFO', 'BotController', 'Bot stopped by user request.']
      );
    }
    await connection.commit();
    return NextResponse.json({
      success: true,
      message: runRows.length > 0 ? 'Bot stopped successfully.' : 'Bot was already stopped.',
    }, { status: 200 });
  } catch (error) {
    if (connection) await connection.rollback();
    return serviceUnavailable('Bot stop', error);
  } finally {
    connection?.release();
  }
}
