import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [healthRows]: any = await pool.query(
      'SELECT id, component, status, details, last_check FROM system_health ORDER BY component'
    );
    const [runRows]: any = await pool.query(
      "SELECT id, last_heartbeat FROM bot_runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
    );

    const storedComponents = (healthRows || []).filter((row: any) => row.component !== 'database' && row.component !== 'bot_worker');
    const activeRun = runRows?.[0];
    const nowDate = new Date();
    const now = nowDate.toISOString();
    const heartbeatDate = activeRun?.last_heartbeat ? new Date(activeRun.last_heartbeat) : null;
    const hasValidHeartbeat = heartbeatDate !== null && Number.isFinite(heartbeatDate.getTime());
    const heartbeatIsStale = hasValidHeartbeat && nowDate.getTime() - heartbeatDate.getTime() > 15 * 60 * 1000;
    const workerStatus = !activeRun ? 'IDLE' : !hasValidHeartbeat || heartbeatIsStale ? 'DEGRADED' : 'HEALTHY';
    const workerDetails = !activeRun
      ? 'Bot worker is stopped.'
      : !hasValidHeartbeat
        ? `Bot run ${activeRun.id} has no heartbeat.`
        : heartbeatIsStale
          ? `Bot run ${activeRun.id} heartbeat is older than 15 minutes.`
          : `Bot run ${activeRun.id} heartbeat is current.`;
    const components = [
      {
        id: 0,
        component: 'database',
        status: 'HEALTHY',
        details: 'Database query completed successfully.',
        last_check: now,
      },
      {
        id: -1,
        component: 'bot_worker',
        status: workerStatus,
        details: workerDetails,
        last_check: hasValidHeartbeat && heartbeatDate ? heartbeatDate.toISOString() : now,
      },
      ...storedComponents.map((row: any) => ({
        ...row,
        last_check: row.last_check ? new Date(row.last_check).toISOString() : now,
      })),
    ];
    const overallStatus = components.some((component) => component.status === 'DOWN')
      ? 'DOWN'
      : components.some((component) => component.status === 'DEGRADED')
        ? 'DEGRADED'
        : 'HEALTHY';

    return NextResponse.json({ overall_status: overallStatus, components }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Database health check', error);
  }
}
