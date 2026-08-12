'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, Time } from 'lightweight-charts';

interface DrawdownPoint {
  timestamp: string;
  drawdown: number;
}

interface DrawdownChartProps {
  data: DrawdownPoint[];
  height?: number;
}

export const DrawdownChart: React.FC<DrawdownChartProps> = ({ data, height = 260 }) => {
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
      topColor: 'rgba(204, 0, 0, 0.0)',
      bottomColor: 'rgba(204, 0, 0, 0.2)',
      lineColor: '#cc0000',
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
      value: -Math.abs(d.drawdown),
    }));
    seriesRef.current.setData(formatted);
    if (chartRef.current && data.length > 0) {
      chartRef.current.timeScale().fitContent();
    }
  }, [data]);

  return <div ref={containerRef} className="w-full win95-inset" />;
};
