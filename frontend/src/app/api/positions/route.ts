import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM paper_positions WHERE is_open = TRUE ORDER BY opened_at DESC');
    return NextResponse.json(rows || [], { status: 200 });
  } catch (err) {
    return NextResponse.json([], { status: 200 });
  }
}
