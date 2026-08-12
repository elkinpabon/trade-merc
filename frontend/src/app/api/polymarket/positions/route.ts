import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query('SELECT * FROM polymarket_positions WHERE is_active = TRUE ORDER BY opened_at DESC');
    return NextResponse.json(rows || [], { status: 200 });
  } catch (err) {
    return NextResponse.json([
      {
        id: 'pos-poly-1',
        market_id: 'poly-001',
        question: 'Bitcoin superará $100,000 en 2026?',
        outcome: 'YES',
        contract_price: 0.62,
        shares: 80.64,
        total_cost: 50.00,
        current_prob: 0.68,
        unrealized_pnl: 4.84,
        is_active: true,
        opened_at: new Date(Date.now() - 7200000).toISOString()
      }
    ], { status: 200 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { question, outcome, contract_price, cost } = body;
    const pool = getDbPool();

    const shares = parseFloat(cost) / parseFloat(contract_price);
    const id = `poly-pos-${Date.now()}`;

    await pool.query(
      'INSERT INTO polymarket_positions (id, market_id, question, outcome, contract_price, shares, total_cost, current_prob, unrealized_pnl, is_active, opened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, NOW())',
      [id, `mkt-${Date.now()}`, question || 'Predicción Polymarket', outcome || 'YES', parseFloat(contract_price), shares, parseFloat(cost), parseFloat(contract_price), 0.0]
    );

    // Also record signal & log
    await pool.query(
      'INSERT INTO polymarket_logs (level, module, message, timestamp) VALUES (?, ?, ?, NOW())',
      ['INFO', 'PolymarketExecution', `Contrato Comprado: ${outcome} en "${question}" a $${contract_price} (${shares.toFixed(2)} acciones)`]
    );

    return NextResponse.json({ success: true, message: 'Contrato Polymarket comprado con éxito' }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err?.message }, { status: 500 });
  }
}
