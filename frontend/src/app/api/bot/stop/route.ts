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
