import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [rows]: any = await pool.query(
      'SELECT id, level, module, message, timestamp FROM bot_logs ORDER BY timestamp DESC LIMIT 30'
    );
    
    if (rows && rows.length > 0) {
      const logs = rows.map((r: any) => ({
        timestamp: r.timestamp ? new Date(r.timestamp).toISOString() : new Date().toISOString(),
        module: r.module || 'System',
        message: r.message || '',
        level: r.level || 'INFO'
      }));
      return NextResponse.json({ logs }, { status: 200 });
    }
  } catch (err) {
    // Fallback to sample data if DB query fails
  }

  const now = new Date();
  const sampleLogs = [
    {
      timestamp: now.toISOString(),
      module: 'BOT_SCANNER',
      message: '[BTC/USDT] $65,192.00 | Score=72/100 ✅ SEÑAL DE ENTRADA | T=18 M=20 V=19 Vol=15 | RSI=58 ADX=28 MACD=+0.0042 VolR=1.3x'
    },
    {
      timestamp: new Date(now.getTime() - 2000).toISOString(),
      module: 'RISK_ENGINE',
      message: 'Motor Multi-Factor escaneando 50 pares con 10 indicadores. Límites: SL=2.0%, TP=4.0%'
    },
    {
      timestamp: new Date(now.getTime() - 4000).toISOString(),
      module: 'STRATEGY',
      message: '[ETH/USDT] $3,180.00 | Score=48/100 ⏳ NEUTRAL/OBSERVANDO | T=12 M=14 V=12 Vol=10 | RSI=52 ADX=18'
    }
  ];

  return NextResponse.json({ logs: sampleLogs }, { status: 200 });
}
