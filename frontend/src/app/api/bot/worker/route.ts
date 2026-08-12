import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

export const dynamic = 'force-dynamic';
export const maxDuration = 60; // Max execution time for serverless function

interface MarketTicker {
  symbol: string;
  last: number;
  high: number;
  low: number;
  volume: number;
  change_pct: number;
}

export async function GET() {
  try {
    const pool = getDbPool();

    // 1. Fetch active bot configuration
    const [configRows]: any = await pool.query('SELECT * FROM bot_configs LIMIT 1');
    if (!configRows || configRows.length === 0) {
      return NextResponse.json({ success: false, message: 'No active bot config found' }, { status: 200 });
    }
    const config = configRows[0];

    // 2. Fetch active bot run
    const [runRows]: any = await pool.query("SELECT * FROM bot_runs WHERE status = 'running' LIMIT 1");
    if (!runRows || runRows.length === 0) {
      return NextResponse.json({ success: false, message: 'Bot is currently paused' }, { status: 200 });
    }
    const activeRun = runRows[0];

    // Update heartbeat
    await pool.query('UPDATE bot_runs SET last_heartbeat = NOW() WHERE id = ?', [activeRun.id]);

    // 3. Fetch tickers from Binance REST API for top 20 symbols
    const symbols = [
      'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
      'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT',
      'NEARUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'BCHUSDT',
      'APTUSDT', 'SUIUSDT', 'FETUSDT', 'INJUSDT', 'ARBUSDT'
    ];

    const binanceRes = await fetch('https://api.binance.com/api/v3/ticker/24hr', { cache: 'no-store' });
    if (!binanceRes.ok) {
      return NextResponse.json({ success: false, message: 'Failed to fetch Binance tickers' }, { status: 500 });
    }

    const allBinanceTickers: any[] = await binanceRes.json();
    const symbolMap = new Map<string, any>();
    allBinanceTickers.forEach((t) => symbolMap.set(t.symbol, t));

    let processedCount = 0;
    const now = new Date();

    for (const sym of symbols) {
      const tickerData = symbolMap.get(sym);
      if (!tickerData) continue;

      const displaySymbol = sym.replace('USDT', '/USDT');
      const lastPrice = parseFloat(tickerData.lastPrice);
      const highPrice = parseFloat(tickerData.highPrice);
      const lowPrice = parseFloat(tickerData.lowPrice);
      const volume = parseFloat(tickerData.quoteVolume);
      const changePct = parseFloat(tickerData.priceChangePercent);

      // Simple ML prediction simulation for serverless execution
      const rsiEstimate = Math.min(80, Math.max(20, 50 + changePct * 3));
      const trendScore = changePct > 0 ? 15 + Math.min(10, changePct * 2) : Math.max(0, 10 + changePct * 2);
      const momentumScore = rsiEstimate >= 45 && rsiEstimate <= 65 ? 18 : 8;
      const volumeScore = volume > 50000000 ? 18 : 10;
      const volatilityScore = ((highPrice - lowPrice) / lastPrice) * 100 < 4 ? 14 : 6;
      const predScore = changePct > 0.5 ? 12 : 4;
      const regimeScore = changePct > 1.0 ? 8 : 4;

      const totalScore = Math.round(trendScore + momentumScore + volumeScore + volatilityScore + predScore + regimeScore);

      let conviction = 'NEUTRAL/OBSERVANDO';
      if (totalScore >= 75) conviction = 'ALTA CONVICCION';
      else if (totalScore >= 60) conviction = 'SENAL DE ENTRADA';
      else if (totalScore < 30) conviction = 'BAJISTA/SALIR';

      const logMsg = `[${displaySymbol}] $${lastPrice.toFixed(2)} | Score=${totalScore}/100 ${conviction} | T=${Math.round(trendScore)} M=${Math.round(momentumScore)} V=${Math.round(volumeScore)} Vol=${Math.round(volatilityScore)} Pred=${Math.round(predScore)} Reg=${Math.round(regimeScore)} | RSI=${rsiEstimate.toFixed(0)} ML:RANGING`;

      // Log to TiDB bot_logs table
      await pool.query(
        'INSERT INTO bot_logs (level, module, message, timestamp) VALUES (?, ?, ?, NOW())',
        ['INFO', 'BotScanner', logMsg]
      );

      processedCount++;
    }

    return NextResponse.json({
      success: true,
      message: `Vercel Serverless Bot Worker processed ${processedCount} symbols`,
      timestamp: now.toISOString()
    }, { status: 200 });

  } catch (err: any) {
    return NextResponse.json({ success: false, error: err?.message }, { status: 500 });
  }
}
