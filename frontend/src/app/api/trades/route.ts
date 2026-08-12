import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM closed_trades ORDER BY exit_time DESC LIMIT 50');
    return NextResponse.json(rows || [], { status: 200 });
  } catch (err) {
    return NextResponse.json([], { status: 200 });
  }
}
