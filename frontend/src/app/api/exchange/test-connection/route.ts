import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST() {
  return NextResponse.json({
    success: false,
    error: 'La prueba autenticada del exchange no está implementada en este frontend. Use el servicio backend de exchange.',
  }, { status: 501 });
}
