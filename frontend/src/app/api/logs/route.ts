import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const requestedLimit = Number(new URL(request.url).searchParams.get('limit') || 100);
  if (!Number.isInteger(requestedLimit) || requestedLimit < 1 || requestedLimit > 200) {
    return NextResponse.json({ error: 'limit must be an integer between 1 and 200' }, { status: 400 });
  }

  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query(
      'SELECT id, level, module, message, timestamp FROM bot_logs ORDER BY timestamp DESC LIMIT ?',
      [requestedLimit]
    );
    return NextResponse.json(rows || [], { status: 200 });
  } catch (error) {
    return serviceUnavailable('Bot logs', error);
  }
}
