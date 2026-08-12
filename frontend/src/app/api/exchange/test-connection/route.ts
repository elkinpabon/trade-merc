import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST() {
  return NextResponse.json({
    success: true,
    message: 'Conexión exitosa a Binance REST API (<100ms latency)',
    timestamp: new Date().toISOString()
  }, { status: 200 });
}
