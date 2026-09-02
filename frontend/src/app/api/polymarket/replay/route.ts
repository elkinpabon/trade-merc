import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json({
    error: 'Polymarket L2 replay infrastructure is not implemented',
  }, { status: 501 });
}
