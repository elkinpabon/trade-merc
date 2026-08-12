'use client';

import React, { useEffect, useState } from 'react';
import { PriceChart } from '@/components/charts/PriceChart';
import { api } from '@/lib/api';
import { CandleData } from '@/types';
import { Zap } from 'lucide-react';

export const MarketView: React.FC = () => {
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [timeframe, setTimeframe] = useState('15m');
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [ticker, setTicker] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getCandles(symbol, timeframe, 100),
      api.getTicker(symbol),
    ])
      .then(([cData, tData]) => {
        setCandles(cData);
        setTicker(tData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
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
          ${ticker?.last ? ticker.last.toFixed(2) : '65,192.00'}
        </div>
      </div>

      {/* Chart Panel */}
      <div className="win95-panel p-3 space-y-2">
        <PriceChart candles={candles} height={340} />

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

        <button className="win95-button w-full py-2 text-xs font-bold flex items-center justify-center gap-1.5">
          <Zap className="h-3.5 w-3.5 fill-current" />
          <span>Copy trade</span>
        </button>
      </div>

      {/* Signal Confidence Card */}
      <div className="win95-panel p-3 space-y-2">
        <div className="win95-inset bg-white p-2 text-center font-bold text-xs font-mono text-[#008000]">
          LONG AI signal · {timeframe} · R:R 1:3
        </div>

        <div className="win95-inset bg-white p-2 text-center font-bold text-xs font-mono">
          confidence 60%
        </div>

        {/* Signal Levels Table */}
        <div className="win95-inset bg-white p-2 font-mono text-xs space-y-1.5 divide-y divide-[#e5e5e5]">
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Entry</span>
            <span className="font-bold">${ticker?.last ? ticker.last.toFixed(2) : '65,191.30'}</span>
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Stop</span>
            <div className="text-right">
              <div className="font-bold text-[#cc0000]">
                ${ticker?.last ? (ticker.last * 0.98).toFixed(2) : '64,831.20'}
              </div>
              <div className="text-[10px] text-[#cc0000]">-0.55%</div>
            </div>
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Take 1</span>
            <div className="text-right">
              <div className="font-bold text-[#008000]">
                ${ticker?.last ? (ticker.last * 1.02).toFixed(2) : '65,551.40'}
              </div>
              <div className="text-[10px] text-[#008000]">+0.55%</div>
            </div>
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Take 2</span>
            <div className="text-right">
              <div className="font-bold text-[#008000]">
                ${ticker?.last ? (ticker.last * 1.04).toFixed(2) : '65,911.00'}
              </div>
              <div className="text-[10px] text-[#008000]">+1.1%</div>
            </div>
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[#808080]">Take 3</span>
            <div className="text-right">
              <div className="font-bold text-[#008000]">
                ${ticker?.last ? (ticker.last * 1.06).toFixed(2) : '66,272.00'}
              </div>
              <div className="text-[10px] text-[#008000]">+1.65%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
