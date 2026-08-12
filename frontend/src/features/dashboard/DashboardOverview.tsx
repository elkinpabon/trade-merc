'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { StatCard } from '@/components/common/StatCard';
import { PriceChart } from '@/components/charts/PriceChart';
import { api } from '@/lib/api';
import { useSocket } from '@/hooks/useSocket';
import { CandleData, PortfolioSummaryData, BotLogData } from '@/types';
import { Search, Terminal, Activity } from 'lucide-react';

interface ScannedMarket {
  symbol: string;
  price: number;
  change_pct: number;
  volume_24h: number;
  spread_range_pct: number;
  anomaly_score: number;
  pattern_tag: string;
}

const FALLBACK_POPULAR_COINS: ScannedMarket[] = [
  { symbol: "BTC/USDT", price: 65192.00, change_pct: 0.00, volume_24h: 445800000, spread_range_pct: 1.2, anomaly_score: 85, pattern_tag: "NEUTRAL" },
  { symbol: "ETH/USDT", price: 1926.00, change_pct: 0.00, volume_24h: 319600000, spread_range_pct: 1.8, anomaly_score: 72, pattern_tag: "NEUTRAL" },
  { symbol: "SOL/USDT", price: 76.50, change_pct: 0.00, volume_24h: 224600000, spread_range_pct: 2.4, anomaly_score: 91, pattern_tag: "NEUTRAL" },
  { symbol: "BNB/USDT", price: 580.40, change_pct: 0.15, volume_24h: 120000000, spread_range_pct: 1.1, anomaly_score: 80, pattern_tag: "NEUTRAL" },
  { symbol: "XRP/USDT", price: 1.03, change_pct: -0.01, volume_24h: 21100000, spread_range_pct: 1.2, anomaly_score: 95, pattern_tag: "NEUTRAL" }
];

export const DashboardOverview: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC/USDT');
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [scannedMarkets, setScannedMarkets] = useState<ScannedMarket[]>(FALLBACK_POPULAR_COINS);
  const [searchQuery, setSearchQuery] = useState('');
  const [chartLoading, setChartLoading] = useState(false);
  const [liveLogs, setLiveLogs] = useState<any[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { socket } = useSocket();

  const loadCandles = useCallback(async (sym: string) => {
    setChartLoading(true);
    try {
      const cData = await api.getCandles(sym, '5m', 100);
      setCandles(cData || []);
    } catch (err) {
      console.error('Error al cargar velas para', sym, err);
      setCandles([]);
    } finally {
      setChartLoading(false);
    }
  }, []);

  const loadData = useCallback(async () => {
    try {
      const dashData = await api.getDashboardSummary();
      setSummary(dashData);

      const scannerData = await api.getMarketScanner();
      if (scannerData?.markets && scannerData.markets.length > 0) {
        setScannedMarkets(scannerData.markets);
      }
    } catch (err) {
      console.error('Error al cargar resumen:', err);
    }
  }, []);

  const handleSelectCoin = (sym: string) => {
    if (sym === selectedSymbol) return;
    setSelectedSymbol(sym);
    loadCandles(sym);
  };

  useEffect(() => {
    loadData();
    loadCandles(selectedSymbol);
  }, [loadData, loadCandles, selectedSymbol]);

  useEffect(() => {
    socket.on('portfolio_updated', (pData: PortfolioSummaryData) => {
      setSummary((prev: any) => (prev ? { ...prev, portfolio: pData } : prev));
    });

    socket.on('market_scanner_update', (data: { total_markets: number; markets: ScannedMarket[] }) => {
      if (data?.markets && data.markets.length > 0) {
        setScannedMarkets(data.markets);
      }
    });

    socket.on('bot_log', (logEntry: any) => {
      setLiveLogs((prev) => [logEntry, ...prev.slice(0, 49)]);
    });

    const fetchLiveLogs = async () => {
      try {
        const res = await api.getLiveLogs();
        if (res?.logs && res.logs.length > 0) {
          setLiveLogs(res.logs);
        }
      } catch (e) {
        // Fallback error ignore
      }
    };
    fetchLiveLogs();
    const pollTimer = setInterval(fetchLiveLogs, 2000);

    return () => {
      clearInterval(pollTimer);
      socket.off('portfolio_updated');
      socket.off('market_scanner_update');
      socket.off('bot_log');
    };
  }, [socket]);

  const p = summary?.portfolio;

  const filteredMarkets = scannedMarkets.filter((m) =>
    m.symbol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-4 font-sans text-black">
      {/* Top Inset Bar: PNL ALL OPEN, Margin, Today */}
      <div className="win95-panel p-3">
        <div className="flex items-center justify-between border-b border-[#808080] pb-2 mb-2">
          <div>
            <h1 className="text-xl font-bold font-sans text-[#000080]">Operaciones de Trading en Vivo</h1>
            <p className="text-xs text-[#404040] font-mono">{p?.open_positions_count || 0} posiciones abiertas</p>
          </div>
          <div className="text-xs font-mono font-bold bg-[#000080] text-white px-3 py-1">
            CAPITAL DE TRADING: ${p?.total_equity?.toFixed(2) || '100.00'} USD
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <StatCard
            title="PNL FLOTANTE (ABIERTO)"
            value={`+$${p?.unrealized_pnl?.toFixed(2) || '0.00'}`}
            trend={p?.unrealized_pnl >= 0 ? 'up' : 'down'}
          />
          <StatCard
            title="MARGEN EN POSICIONES"
            value={`$${p?.positions_value?.toFixed(2) || '0.00'}`}
            trend="neutral"
          />
          <StatCard
            title="GANANCIA REALIZADA"
            value={`+$${p?.realized_pnl?.toFixed(2) || '0.00'}`}
            trend={p?.realized_pnl >= 0 ? 'up' : 'down'}
          />
        </div>
      </div>

      {/* Main Split: Candlestick Chart (Left) + Markets List (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Chart Container */}
        <div className="lg:col-span-2 win95-panel p-3 space-y-2">
          <div className="win95-titlebar flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-3.5 w-3.5" />
              <span>Gráfico de Precios en Vivo · {selectedSymbol} · 5m</span>
            </div>
            <span>Binance API Feed</span>
          </div>
          <PriceChart candles={candles} height={350} loading={chartLoading} symbol={selectedSymbol} />
        </div>

        {/* Right: Markets List */}
        <div className="win95-panel p-3 space-y-2">
          <div className="win95-titlebar">
            <span>Mercados Cripto ({scannedMarkets.length})</span>
            <span>Binance · Realtime</span>
          </div>

          {/* Search Box */}
          <div className="win95-inset bg-white p-1 flex items-center gap-1">
            <Search className="h-3.5 w-3.5 text-[#808080] shrink-0 ml-1" />
            <input
              type="text"
              placeholder="Buscar par (ej. BTC, ETH)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs font-mono outline-none bg-transparent"
            />
          </div>

          {/* Markets Header Row */}
          <div className="grid grid-cols-3 text-[11px] font-bold font-mono text-[#808080] border-b border-[#808080] pb-1 px-1">
            <span>PAR · VOL</span>
            <span className="text-center">24H %</span>
            <span className="text-right">PRECIO</span>
          </div>

          {/* Scrollable Coin List */}
          <div className="space-y-1 max-h-[320px] overflow-y-auto pr-1">
            {filteredMarkets.map((m) => (
              <div
                key={m.symbol}
                onClick={() => handleSelectCoin(m.symbol)}
                className={`win95-panel p-2 cursor-pointer flex items-center justify-between text-xs font-mono hover:bg-[#000080] hover:text-white ${
                  selectedSymbol === m.symbol ? 'win95-button-active' : 'bg-white'
                }`}
              >
                <div>
                  <div className="font-bold">{m.symbol.replace('/USDT', '')}</div>
                  <div className="text-[10px] opacity-75">${(m.volume_24h / 1000000).toFixed(1)}M</div>
                </div>

                <div className={`font-bold text-xs ${m.change_pct >= 0 ? 'text-[#008000]' : 'text-[#cc0000]'}`}>
                  {m.change_pct >= 0 ? '+' : ''}{m.change_pct.toFixed(2)}%
                </div>

                <div className="text-right font-bold">
                  ${m.price >= 1 ? m.price.toFixed(2) : m.price.toFixed(4)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Second-by-Second Live Analysis Logs Panel */}
      <div className="win95-panel p-3 space-y-2">
        <div className="win95-titlebar flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5 text-white" />
            <span>Panel de Análisis en Vivo del Bot (Segundo a Segundo)</span>
          </div>
          <span className="animate-pulse text-[#00ff00] font-bold">SCANNING LIVE</span>
        </div>

        <div className="win95-inset bg-black p-3 font-mono text-xs text-[#00ff00] h-48 overflow-y-auto space-y-1">
          <div className="text-[#808080] text-[10px] border-b border-[#333] pb-1 mb-2">
            === CONSOLA DE MONITOREO TÁCTICO SEGUNDO A SEGUNDO · SISTEMA TRADEMERC ===
          </div>
          {liveLogs.length > 0 ? (
            liveLogs.map((log, idx) => {
              const msg = log.message || '';
              const isSignal = msg.includes('SEÑAL') || msg.includes('ENTRY') || msg.includes('Score=');
              const scoreMatch = msg.match(/Score=(\d+)/);
              const score = scoreMatch ? parseInt(scoreMatch[1]) : 0;
              let msgColor = 'text-[#00ff00]';
              if (score >= 65) msgColor = 'text-[#ffff00]';
              if (msg.includes('BAJISTA') || msg.includes('SALIR')) msgColor = 'text-[#ff4444]';
              if (msg.includes('SEÑAL DE ENTRADA') || msg.includes('ALTA CONV')) msgColor = 'text-[#00ffff]';
              if (msg.includes('Orden ejecutada') || msg.includes('EXECUTED')) msgColor = 'text-[#ffff00] font-bold';
              if (log.module === 'RiskEngine') msgColor = 'text-[#ff8800]';
              if (log.module === 'StrategyEngine') msgColor = 'text-[#00ffff]';

              return (
                <div key={idx} className="leading-tight flex items-start gap-2 hover:bg-white/10 px-1">
                  <span className="text-[#808080] shrink-0">
                    [{new Date(log.timestamp || Date.now()).toLocaleTimeString()}]
                  </span>
                  <span className="text-[#00ffff] shrink-0 font-bold">[{log.module || 'BOT'}]</span>
                  <span className={msgColor}>{msg}</span>
                </div>
              );
            })
          ) : (
            <div className="text-[#00ff00] font-mono animate-pulse">
              [TRADEMERC] Motor Multi-Factor analizando 10 indicadores en 50 pares de Binance en tiempo real...
            </div>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Trade Position Cards */}
      <div className="win95-panel p-3 space-y-3">
        <div className="win95-titlebar">
          <span>Posiciones Compradas Actualmente por el Bot</span>
          <span>{p?.positions?.length || 0} Activas</span>
        </div>

        {p?.positions && p.positions.length > 0 ? (
          <div className="space-y-3">
            {p.positions.map((pos: any) => (
              <div key={pos.id} className="win95-panel p-3 bg-white border border-[#404040]">
                <div className="flex items-center justify-between border-b border-[#c0c0c0] pb-2 mb-2">
                  <div className="font-bold text-sm font-mono text-black">
                    {pos.symbol.replace('/', '-')} <span className="text-[#008000]">LONG</span> <span className="text-xs text-[#808080]">Bot Auto</span>
                  </div>
                  <div className={`font-bold text-sm font-mono ${pos.unrealized_pnl >= 0 ? 'text-[#008000]' : 'text-[#cc0000]'}`}>
                    {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl.toFixed(2)} ({pos.unrealized_pnl_pct.toFixed(2)}%)
                  </div>
                </div>

                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-xs font-mono mb-3">
                  <div>
                    <div className="text-[10px] text-[#808080] uppercase">CANTIDAD</div>
                    <div className="font-bold">{pos.quantity}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080] uppercase">VALOR</div>
                    <div className="font-bold">${(pos.quantity * pos.current_price).toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080] uppercase">ENTRADA</div>
                    <div className="font-bold">${pos.entry_price.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080] uppercase">PRECIO ACTUAL</div>
                    <div className="font-bold">${pos.current_price.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080] uppercase">STOP LOSS</div>
                    <div className="font-bold text-[#cc0000]">${pos.stop_loss_price ? pos.stop_loss_price.toFixed(2) : '-'}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080] uppercase">TAKE PROFIT</div>
                    <div className="font-bold text-[#008000]">${pos.take_profit_price ? pos.take_profit_price.toFixed(2) : '-'}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="win95-inset bg-white p-6 text-center text-xs font-mono text-[#808080]">
            No hay posiciones abiertas actualmente. El bot está escaneando los 50 mercados para ejecutar la siguiente compra.
          </div>
        )}
      </div>
    </div>
  );
};
