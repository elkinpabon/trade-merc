import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

function parseArray(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  if (typeof value !== 'string') return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function GET(request: Request) {
  const categoryFilter = new URL(request.url).searchParams.get('category') || 'ALL';
  try {
    const response = await fetch('https://gamma-api.polymarket.com/events?limit=30&active=true&closed=false', {
      cache: 'no-store',
      headers: { 'User-Agent': 'TRADEMERC-Polymarket-Market-Viewer/1.0' },
    });
    if (!response.ok) {
      return NextResponse.json({ error: 'Polymarket market feed is unavailable' }, { status: 502 });
    }

    const events: any[] = await response.json();
    const markets = events.flatMap((event: any) => {
      const category = event.tags?.[0]?.label || null;
      return (event.markets || []).flatMap((market: any) => {
        const outcomes = parseArray(market.outcomes).map(String);
        const prices = parseArray(market.outcomePrices).map(Number);
        if (!market.id || outcomes.length < 2 || prices.length !== outcomes.length || prices.some((price) => !Number.isFinite(price))) {
          return [];
        }
        return [{
          id: String(market.id),
          question: market.question || event.title || '',
          category,
          outcomes,
          prices,
          volume: Number(market.volume ?? event.volume ?? 0),
          liquidity: Number(market.liquidity ?? event.liquidity ?? 0),
          active: Boolean(market.active),
          closed: Boolean(market.closed),
          end_date: market.endDate || event.endDate || null,
          icon: event.icon || event.image || null,
        }];
      });
    });
    const filtered = categoryFilter === 'ALL'
      ? markets
      : markets.filter((market: any) =>
          String(market.category || '').toLowerCase().includes(categoryFilter.toLowerCase()) ||
          market.question.toLowerCase().includes(categoryFilter.toLowerCase())
        );

    return NextResponse.json({ total: filtered.length, markets: filtered.slice(0, 20) }, { status: 200 });
  } catch (error) {
    console.error('Polymarket market feed unavailable:', error);
    return NextResponse.json({ error: 'Polymarket market feed is unavailable' }, { status: 502 });
  }
}
