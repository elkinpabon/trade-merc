import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const symbolParam = searchParams.get('symbol') || 'BTC/USDT';
  const cleanSym = symbolParam.replace('/', '').replace('%2F', '').replace('%2f', '').toUpperCase();
  const symbol = cleanSym.endsWith('USDT') ? cleanSym : `${cleanSym}USDT`;

  try {
    const res = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`, { cache: 'no-store' });
    if (!res.ok) {
      return NextResponse.json({ error: 'Binance ticker is unavailable' }, { status: 502 });
    }

    const data = await res.json();
    return NextResponse.json({
      symbol: symbolParam,
      last: Number(data.lastPrice),
      high: Number(data.highPrice),
      low: Number(data.lowPrice),
      volume: Number(data.quoteVolume),
      change_pct: Number(data.priceChangePercent),
    }, { status: 200 });
  } catch (error) {
    console.error('Binance ticker unavailable:', error);
    return NextResponse.json({ error: 'Binance ticker is unavailable' }, { status: 502 });
  }
}
