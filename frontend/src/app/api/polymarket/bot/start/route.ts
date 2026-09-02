import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST() {
  return NextResponse.json({
    success: false,
    error: 'Polymarket bot infrastructure is not implemented',
  }, { status: 501 });
}
