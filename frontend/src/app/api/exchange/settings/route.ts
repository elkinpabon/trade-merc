import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json({
    exchange_id: 'binance',
    api_key_configured: false,
    testnet_enabled: true,
    sandbox_mode: true,
    message: 'Servicio de integración Binance REST listo en modo Paper Trading'
  }, { status: 200 });
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    return NextResponse.json({ success: true, message: 'Configuración de exchange actualizada', settings: body }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err?.message }, { status: 500 });
  }
}
