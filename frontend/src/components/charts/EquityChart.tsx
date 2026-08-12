'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, Time } from 'lightweight-charts';

interface EquityPoint {
  timestamp: string;
  equity: number;
  drawdown: number;
}

interface EquityChartProps {
  data: EquityPoint[];
  height?: number;
}

export const EquityChart: React.FC<EquityChartProps> = ({ data, height = 260 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);

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
      timeScale: {
        borderColor: '#808080',
        timeVisible: true,
      },
    });

    const areaSeries = chart.addAreaSeries({
      topColor: 'rgba(0, 128, 0, 0.2)',
      bottomColor: 'rgba(0, 128, 0, 0.0)',
      lineColor: '#008000',
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = areaSeries;

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
    if (!seriesRef.current || !data) return;
    const formatted = data.map((d) => ({
      time: (new Date(d.timestamp).getTime() / 1000) as Time,
      value: d.equity,
    }));
    seriesRef.current.setData(formatted);
    if (chartRef.current && data.length > 0) {
      chartRef.current.timeScale().fitContent();
    }
  }, [data]);

  return <div ref={containerRef} className="w-full win95-inset" />;
};
