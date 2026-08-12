'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';
import { CandleData } from '@/types';
import { RefreshCw } from 'lucide-react';

interface PriceChartProps {
  candles: CandleData[];
  height?: number;
  loading?: boolean;
  symbol?: string;
}

export const PriceChart: React.FC<PriceChartProps> = ({
  candles,
  height = 360,
  loading = false,
  symbol = 'BTC/USDT',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#000000',
        fontSize: 11,
        fontFamily: 'Tahoma, Arial, sans-serif',
      },
      grid: {
        vertLines: { color: '#e5e5e5' },
        horzLines: { color: '#e5e5e5' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#808080',
      },
      timeScale: {
        borderColor: '#808080',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#00a800',
      downColor: '#d00000',
      borderVisible: true,
      borderColor: '#000000',
      wickUpColor: '#00a800',
      wickDownColor: '#d00000',
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (!seriesRef.current || !candles) return;

    const formattedData: CandlestickData<Time>[] = candles.map((c) => ({
      time: (c.timestamp / 1000) as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    seriesRef.current.setData(formattedData);
    if (chartRef.current && candles.length > 0) {
      chartRef.current.timeScale().fitContent();
    }
  }, [candles]);

  const isLoading = loading || !candles || candles.length === 0;

  return (
    <div className="w-full relative min-h-[350px]">
      {isLoading && (
        <div className="absolute inset-0 z-20 bg-white/90 backdrop-blur-[1px] flex flex-col items-center justify-center space-y-3 p-4 border border-[#808080]">
          <RefreshCw className="h-8 w-8 text-[#000080] animate-spin" />
          <div className="text-xs font-mono font-bold text-[#000080] text-center">
            Cargando velas de mercado de Binance en vivo para {symbol}...
          </div>
          <div className="w-48 win95-inset bg-[#e0e0e0] h-3 p-0.5 overflow-hidden">
            <div className="bg-[#000080] h-full w-2/3 animate-pulse" />
          </div>
        </div>
      )}
      <div ref={containerRef} className="w-full win95-inset" />
    </div>
  );
};
