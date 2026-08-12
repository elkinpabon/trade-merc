import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST() {
  return NextResponse.json({
    success: true,
    message: 'Bot de Trading TRADEMERC iniciado con éxito.',
    run_id: 'run-tidb-001'
  }, { status: 200 });
}
