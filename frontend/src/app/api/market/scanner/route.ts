import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  const defaultMarkets = [
    { symbol: "BTC/USDT", price: 65192.00, change_pct: 0.85, volume_24h: 445800000, spread_range_pct: 1.2, anomaly_score: 85, pattern_tag: "NEUTRAL" },
    { symbol: "ETH/USDT", price: 1926.00, change_pct: 1.20, volume_24h: 319600000, spread_range_pct: 1.8, anomaly_score: 72, pattern_tag: "NEUTRAL" },
    { symbol: "SOL/USDT", price: 76.50, change_pct: 2.45, volume_24h: 224600000, spread_range_pct: 2.4, anomaly_score: 91, pattern_tag: "ACCUMULATION" },
    { symbol: "BNB/USDT", price: 580.40, change_pct: 0.15, volume_24h: 120000000, spread_range_pct: 1.1, anomaly_score: 80, pattern_tag: "NEUTRAL" },
    { symbol: "XRP/USDT", price: 1.03, change_pct: -0.50, volume_24h: 21100000, spread_range_pct: 1.2, anomaly_score: 95, pattern_tag: "NEUTRAL" }
  ];

  try {
    const resp = await fetch('https://api.binance.com/api/v3/ticker/24hr', { cache: 'no-store' });
    if (resp.ok) {
      const data = await resp.json();
      const usdtPairs = data
        .filter((t: any) => t.symbol.endsWith('USDT') && !t.symbol.includes('UP') && !t.symbol.includes('DOWN'))
        .slice(0, 30)
        .map((t: any) => ({
          symbol: `${t.symbol.replace('USDT', '')}/USDT`,
          price: parseFloat(t.lastPrice),
          change_pct: parseFloat(t.priceChangePercent),
          volume_24h: parseFloat(t.quoteVolume),
          spread_range_pct: 1.5,
          anomaly_score: Math.min(100, Math.max(50, Math.floor(Math.abs(parseFloat(t.priceChangePercent)) * 10 + 60))),
          pattern_tag: parseFloat(t.priceChangePercent) > 2 ? 'MOMENTUM_BREAKOUT' : 'NEUTRAL'
        }));
      if (usdtPairs.length > 0) {
        return NextResponse.json({ total_markets: usdtPairs.length, markets: usdtPairs }, { status: 200 });
      }
    }
  } catch (e) {
    console.warn("Scanner Binance fetch fallback:", e);
  }

  return NextResponse.json({ total_markets: defaultMarkets.length, markets: defaultMarkets }, { status: 200 });
}
