import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const resp = await fetch('https://api.binance.com/api/v3/ticker/24hr', { cache: 'no-store' });
    if (!resp.ok) {
      return NextResponse.json({ error: 'Binance market feed is unavailable' }, { status: 502 });
    }

    const data = await resp.json();
    const usdtPairs = data
      .filter((ticker: any) => ticker.symbol.endsWith('USDT') && !ticker.symbol.includes('UP') && !ticker.symbol.includes('DOWN'))
      .sort((a: any, b: any) => Number(b.quoteVolume) - Number(a.quoteVolume))
      .slice(0, 30)
      .map((ticker: any) => ({
        symbol: `${ticker.symbol.slice(0, -4)}/USDT`,
        price: Number(ticker.lastPrice),
        change_pct: Number(ticker.priceChangePercent),
        volume_24h: Number(ticker.quoteVolume),
      }));
    return NextResponse.json({ total_markets: usdtPairs.length, markets: usdtPairs }, { status: 200 });
  } catch (error) {
    console.error('Binance market feed unavailable:', error);
    return NextResponse.json({ error: 'Binance market feed is unavailable' }, { status: 502 });
  }
}
