import {
  BotConfigData,
  CandleData,
  PaperOrderData,
  PaperFillData,
  PaperPositionData,
  PortfolioSummaryData,
  SignalData,
  TradeData,
  BotLogData,
  SystemHealthData,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('trademerc_token');
  }
  return null;
}

async function fetcher<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !endpoint.includes('/auth/login')) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('trademerc_token');
      window.location.href = '/login';
    }
  }

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API Request Error (${res.status}): ${errText}`);
  }

  return res.json();
}

export const api = {
  login: (username: string, pin: string) =>
    fetcher<{ success: boolean; token: string; user: any; message: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, pin }),
    }),
  verifyAuth: () => fetcher<{ valid: boolean }>('/auth/verify'),
  getHealth: () => fetcher<SystemHealthData>('/health'),
  getBotStatus: () => fetcher<{ is_running: boolean; mode: string; config: BotConfigData }>('/bot/status'),
  startBot: () => fetcher<{ success: boolean; message: string }>('/bot/start', { method: 'POST' }),
  stopBot: () => fetcher<{ success: boolean; message: string }>('/bot/stop', { method: 'POST' }),
  getConfig: () => fetcher<BotConfigData>('/config'),
  updateConfig: (data: Partial<BotConfigData>) =>
    fetcher<{ success: boolean; config: BotConfigData }>('/config', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  getDashboardSummary: () =>
    fetcher<{
      bot_status: string;
      mode: string;
      exchange: string;
      active_symbols: string[];
      portfolio: PortfolioSummaryData;
      last_signal: SignalData | null;
      last_trade: TradeData | null;
      recent_alerts: any[];
      health: SystemHealthData;
    }>('/dashboard/summary'),

  getCandles: async (symbol: string = 'BTC/USDT', timeframe: string = '5m', limit: number = 100): Promise<CandleData[]> => {
    const cleanSym = symbol.replace('/', '').replace('%2F', '').replace('%2f', '').toUpperCase();
    const cleanSymbol = cleanSym.endsWith('USDT') ? cleanSym : `${cleanSym}USDT`;

    try {
      // Direct ultra-fast Binance REST fetch (<100ms)
      const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=${cleanSymbol}&interval=${timeframe}&limit=${limit}`);
      if (res.ok) {
        const raw = await res.json();
        return raw.map((c: any) => ({
          symbol,
          timeframe,
          timestamp: c[0],
          datetime: new Date(c[0]).toISOString(),
          open: parseFloat(c[1]),
          high: parseFloat(c[2]),
          low: parseFloat(c[3]),
          close: parseFloat(c[4]),
          volume: parseFloat(c[5])
        }));
      }
    } catch (err) {
      console.warn("Direct Binance client fetch notice, using fallback backend endpoint:", err);
    }

    try {
      return await fetcher<CandleData[]>(`/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=${limit}`);
    } catch (fallbackErr) {
      console.error("Candles fallback error:", fallbackErr);
      return [];
    }
  },

  getTicker: (symbol: string) =>
    fetcher<{ symbol: string; last: number; high: number; low: number; volume: number; change_pct: number }>(
      `/market/ticker?symbol=${encodeURIComponent(symbol)}`
    ),
  getMarketScanner: () =>
    fetcher<{ total_markets: number; markets: any[] }>('/market/scanner'),
  getSignals: (limit: number = 50) => fetcher<SignalData[]>(`/signals?limit=${limit}`),
  getOrders: (limit: number = 50) => fetcher<PaperOrderData[]>(`/orders?limit=${limit}`),
  getFills: (limit: number = 50) => fetcher<PaperFillData[]>(`/fills?limit=${limit}`),
  getTrades: (limit: number = 50) => fetcher<TradeData[]>(`/trades?limit=${limit}`),
  getPositions: () => fetcher<PaperPositionData[]>('/positions'),
  getAnalytics: () => fetcher<any>('/analytics/overview'),
  getLogs: (limit: number = 100, level?: string) =>
    fetcher<BotLogData[]>(`/logs?limit=${limit}${level ? `&level=${level}` : ''}`),
  getLiveLogs: () => fetcher<{ logs: any[] }>('/bot/live-logs'),
  getExchangeSettings: () => fetcher<any>('/exchange/settings'),
  updateExchangeSettings: (data: any) =>
    fetcher<any>('/exchange/settings', { method: 'PUT', body: JSON.stringify(data) }),
  testExchangeConnection: (data: any) =>
    fetcher<any>('/exchange/test-connection', { method: 'POST', body: JSON.stringify(data) }),
};
