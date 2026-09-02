'use client';

import React, { useEffect, useState } from 'react';
import { PriceChart } from '@/components/charts/PriceChart';
import { api } from '@/lib/api';
import { CandleData, SignalData } from '@/types';
import { Zap } from 'lucide-react';

export const MarketView: React.FC = () => {
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [timeframe, setTimeframe] = useState('15m');
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [ticker, setTicker] = useState<any>(null);
  const [signal, setSignal] = useState<SignalData | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setUnavailable(false);
    setCandles([]);
    setTicker(null);
    setSignal(null);
    Promise.all([
      api.getCandles(symbol, timeframe, 100),
      api.getTicker(symbol),
      api.getSignals(),
    ])
      .then(([cData, tData, signals]) => {
        if (cancelled) return;
        setCandles(cData);
        setTicker(tData);
        setSignal(signals.find((item) => item.symbol === symbol) || null);
      })
      .catch((error) => {
        if (cancelled) return;
        console.error('Market sources unavailable:', error);
        setCandles([]);
        setTicker(null);
        setSignal(null);
        setUnavailable(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe]);

  return (
    <div className="space-y-4 font-sans text-black">
      {/* Top Bar */}
      <div className="win95-titlebar flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="win95-button text-xs px-2 py-0.5 bg-white text-black outline-none font-bold"
          >
            <option value="BTC/USDT">BTC/USDT</option>
            <option value="ETH/USDT">ETH/USDT</option>
            <option value="SOL/USDT">SOL/USDT</option>
            <option value="XRP/USDT">XRP/USDT</option>
            <option value="ADA/USDT">ADA/USDT</option>
            <option value="DOGE/USDT">DOGE/USDT</option>
            <option value="AVAX/USDT">AVAX/USDT</option>
          </select>
          <span className="font-mono text-xs">· perp · cross · 20x</span>
        </div>
        <div className="text-sm font-mono font-bold">
          {ticker ? `$${ticker.last.toFixed(2)}` : 'PRECIO NO DISPONIBLE'}
        </div>
      </div>

      {/* Chart Panel */}
      <div className="win95-panel p-3 space-y-2">
        {unavailable ? (
          <div className="win95-inset min-h-[340px] bg-white flex items-center justify-center p-6 text-center font-mono text-xs font-bold text-[#cc0000]">
            Datos de mercado no disponibles para {symbol}.
          </div>
        ) : (
          <PriceChart candles={candles} height={340} loading={loading} symbol={symbol} />
        )}

        {/* Timeframe Buttons */}
        <div className="grid grid-cols-4 gap-2 pt-2">
          {['15m', '1h', '4h', '1D'].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`win95-button py-1 text-xs font-bold ${
                timeframe === tf ? 'win95-button-active' : ''
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        <button disabled={!signal || unavailable} className="win95-button w-full py-2 text-xs font-bold flex items-center justify-center gap-1.5 disabled:text-[#808080]">
          <Zap className="h-3.5 w-3.5 fill-current" />
          <span>Copy trade</span>
        </button>
      </div>

      <div className="win95-panel p-3 space-y-2">
        <div className={`win95-inset bg-white p-2 text-center font-bold text-xs font-mono ${signal ? 'text-[#008000]' : 'text-[#808080]'}`}>
          {signal ? `${signal.action || signal.type} · ${timeframe}` : 'SEÑAL NO DISPONIBLE'}
        </div>

        <div className="win95-inset bg-white p-2 text-center font-bold text-xs font-mono">
          CONFIANZA NO DISPONIBLE
        </div>

        <div className="win95-inset bg-white p-2 font-mono text-xs space-y-1.5 divide-y divide-[#e5e5e5]">
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Entry</span>
            <span className="font-bold">{signal ? `$${signal.price.toFixed(2)}` : 'NO DISPONIBLE'}</span>
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Stop</span>
            <span className="font-bold">NO DISPONIBLE</span>
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Take profit</span>
            <span className="font-bold">NO DISPONIBLE</span>
          </div>
        </div>
      </div>
    </div>
  );
};
