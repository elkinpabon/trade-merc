import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json({
    error: 'The simulated frontend bot worker has been disabled; use the real backend worker.',
  }, { status: 501 });
}
