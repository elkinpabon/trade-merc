'use client';

import React, { useEffect, useState } from 'react';
import { StatCard } from '@/components/common/StatCard';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { api } from '@/lib/api';

export const AnalyticsView: React.FC = () => {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.getAnalytics().then(setData).catch(console.error);
  }, []);

  const overview = data?.overview;

  return (
    <div className="space-y-4 font-sans text-black">
      {/* Title Panel */}
      <div className="win95-panel p-3">
        <div className="win95-titlebar mb-2">
          <span>Rendimiento y Crecimiento de Capital (Profile)</span>
          <span>TRADEMERC Performance</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <StatCard
            title="Factor de Ganancia"
            value={overview?.profit_factor?.toFixed(2) || '1.00'}
            subtitle="Ganancias vs Pérdidas"
            trend="up"
          />
          <StatCard
            title="Consistencia Sharpe"
            value={overview?.sharpe_ratio?.toFixed(2) || '0.00'}
            subtitle="Estabilidad de Retornos"
            trend="up"
          />
          <StatCard
            title="Max Drawdown"
            value={`${overview?.max_drawdown_pct?.toFixed(2) || '0.00'}%`}
            subtitle="Caída Máxima Registrada"
            trend="neutral"
          />
          <StatCard
            title="Ganancia Neta"
            value={`$${overview?.total_pnl?.toFixed(2) || '0.00'}`}
            subtitle={`Éxito: ${overview?.win_rate?.toFixed(0) || '0'}%`}
            trend={overview?.total_pnl >= 0 ? 'up' : 'down'}
          />
        </div>
      </div>

      {/* Equity and Drawdown Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="win95-panel p-3 space-y-2">
          <div className="win95-titlebar">
            <span>Curva de Capital ($ USD)</span>
            <span>TRADEMERC Equity</span>
          </div>
          <EquityChart data={data?.equity_curve || []} height={250} />
        </div>

        <div className="win95-panel p-3 space-y-2">
          <div className="win95-titlebar">
            <span>Control de Drawdown (%)</span>
            <span>TRADEMERC Risk</span>
          </div>
          <DrawdownChart data={data?.equity_curve || []} height={250} />
        </div>
      </div>
    </div>
  );
};
