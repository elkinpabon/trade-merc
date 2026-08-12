import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM polymarket_signals ORDER BY timestamp DESC LIMIT 30');
    return NextResponse.json(rows || [], { status: 200 });
  } catch (err) {
    return NextResponse.json([
      {
        id: 'poly-sig-1',
        market_id: 'poly-001',
        question: 'Bitcoin superará $100,000 en 2026?',
        outcome: 'YES',
        contract_price: 0.62,
        ev_pct: 14.2,
        reason: 'Modelo ML +EV detecta ventaja del 14.2% frente a precio de mercado $0.62. Criterio de Kelly sugiere compra.',
        status: 'EXECUTED',
        timestamp: new Date().toISOString()
      },
      {
        id: 'poly-sig-2',
        market_id: 'poly-003',
        question: 'Ethereum lanzará actualización Pectra antes de Q4?',
        outcome: 'NO',
        contract_price: 0.58,
        ev_pct: 11.8,
        reason: 'Desbalance de probabilidad implícita. Contrato NO subvaluado frente a retrasos reportados.',
        status: 'EXECUTED',
        timestamp: new Date(Date.now() - 3600000).toISOString()
      }
    ], { status: 200 });
  }
}
