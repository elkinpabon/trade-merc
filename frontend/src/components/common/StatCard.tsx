'use client';

import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon?: React.ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
}) => {
  return (
    <div className="win95-inset bg-white p-3 font-sans">
      <div className="text-[10px] font-bold text-[#808080] uppercase tracking-wider font-mono">{title}</div>
      <div className="mt-1 flex items-baseline justify-between">
        <div className={`text-base font-bold font-mono ${trend === 'up' ? 'text-[#008000]' : trend === 'down' ? 'text-[#cc0000]' : 'text-black'}`}>
          {value}
        </div>
        {trendValue && (
          <span className={`text-xs font-bold font-mono ${trend === 'up' ? 'text-[#008000]' : 'text-[#cc0000]'}`}>
            {trendValue}
          </span>
        )}
      </div>
      {subtitle && <div className="mt-1 text-[10px] text-[#404040] font-mono">{subtitle}</div>}
    </div>
  );
};
