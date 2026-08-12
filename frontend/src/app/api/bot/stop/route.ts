import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST() {
  return NextResponse.json({
    success: true,
    message: 'Bot de Trading TRADEMERC detenido correctamente.'
  }, { status: 200 });
}
