import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ valid: true }, { status: 200 });
}
