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
  AnalyticsOverviewData,
  ExperimentReportData,
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
    const error = new Error(`API Request Error (${res.status}): ${errText}`) as Error & { status: number };
    error.status = res.status;
    throw error;
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
  getBotStatus: () => fetcher<{ is_running: boolean; mode: string | null; config: BotConfigData | null }>('/bot/status'),
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
    const binanceTimeframe = timeframe === '1D' ? '1d' : timeframe;

    try {
      // Direct ultra-fast Binance REST fetch (<100ms)
      const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=${cleanSymbol}&interval=${binanceTimeframe}&limit=${limit}`);
      if (res.ok) {
        const raw = await res.json();
        return raw.map((c: any) => ({
          symbol,
          timeframe: binanceTimeframe,
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
      console.warn('Direct Binance candle request failed:', err);
    }

    throw new Error(`Binance candles are unavailable for ${cleanSymbol}`);
  },

  getTicker: (symbol: string) =>
    fetcher<{ symbol: string; last: number; high: number; low: number; volume: number; change_pct: number }>(
      `/market/ticker?symbol=${encodeURIComponent(symbol)}`
    ),
  getSignals: () => fetcher<SignalData[]>('/signals'),
  getOrders: () => fetcher<PaperOrderData[]>('/orders'),
  getFills: () => fetcher<PaperFillData[]>('/fills'),
  getPositions: () => fetcher<PaperPositionData[]>('/positions'),
  getTrades: (limit?: number) => fetcher<TradeData[]>(`/trades${limit ? `?limit=${limit}` : ''}`),
  getLogs: (limit?: number) => fetcher<BotLogData[]>(`/logs${limit ? `?limit=${limit}` : ''}`),
  getLiveLogs: () => fetcher<{ logs: any[] }>('/bot/live-logs'),
  getMarketScanner: () => fetcher<{ total_markets: number; markets: any[] }>('/market/scanner'),
  getAnalyticsOverview: () => fetcher<AnalyticsOverviewData>('/analytics/overview'),
  getAnalytics: () => fetcher<AnalyticsOverviewData>('/analytics/overview'),
  getCurrentExperimentReport: () =>
    fetcher<ExperimentReportData>('/experiments/current/report').catch((error: Error & { status?: number }) => {
      if (error.status === 404) return null;
      throw error;
    }),
  getExchangeSettings: () => fetcher<any>('/exchange/settings'),
  updateExchangeSettings: (data: any) =>
    fetcher<{ success: boolean; message: string }>('/exchange/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  testExchangeConnection: (data?: any) =>
    fetcher<{ success: boolean; message: string }>('/exchange/test-connection', {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  // Polymarket API Suite
  getPolymarketMarkets: (category: string = 'ALL') =>
    fetcher<{ total: number; markets: any[] }>(`/polymarket/markets?category=${encodeURIComponent(category)}`),
  getPolymarketSignals: () => fetcher<any[]>('/polymarket/signals'),
  getPolymarketPositions: () => fetcher<any[]>('/polymarket/positions'),
  buyPolymarketContract: (question: string, outcome: string, contract_price: number, cost: number = 50.0, c_exec_weighted?: number, p_model?: number, taker_fee_pct?: number) =>
    fetcher<{ success: boolean; message: string }>('/polymarket/positions', {
      method: 'POST',
      body: JSON.stringify({ question, outcome, contract_price, cost, c_exec_weighted, p_model, taker_fee_pct })
    }),
  getPolymarketLiveLogs: () => fetcher<{ logs: any[] }>('/polymarket/bot/logs'),
  getPolymarketBotStatus: () => fetcher<{ available: boolean; is_running: boolean; mode: string | null }>('/polymarket/bot/status'),
  startPolymarketBot: () => fetcher<{ success: boolean; message: string }>('/polymarket/bot/start', { method: 'POST' }),
  stopPolymarketBot: () => fetcher<{ success: boolean; message: string }>('/polymarket/bot/stop', { method: 'POST' }),
  getPolymarketAnalytics: () => fetcher<any>('/polymarket/analytics'),
  getPolymarketL2Replay: () => fetcher<any>('/polymarket/replay'),
};
