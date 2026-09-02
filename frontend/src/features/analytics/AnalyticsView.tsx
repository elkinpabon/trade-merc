'use client';

import React, { useEffect, useState } from 'react';
import { StatCard } from '@/components/common/StatCard';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { api } from '@/lib/api';
import { AnalyticsOverviewData, ExperimentReportData } from '@/types';

const criteriaLabels: Record<string, string> = {
  duration_30_days: 'Duración completa de 30 días',
  daily_coverage_at_least_99_pct: 'Cobertura diaria >= 99%',
  cycle_coverage_at_least_99_pct: 'Cobertura de ciclos >= 99%',
  at_least_100_closed_trades: 'Al menos 100 trades cerrados',
  no_open_attributed_position: 'Sin posiciones atribuidas abiertas',
  configuration_unchanged: 'Configuración sin cambios',
};

const formatDate = (value: string | null) => value
  ? new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
  : '--';

const formatMoney = (value: number) => `$${value.toFixed(2)}`;

export const AnalyticsView: React.FC = () => {
  const [data, setData] = useState<AnalyticsOverviewData | null>(null);
  const [report, setReport] = useState<ExperimentReportData | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    api.getAnalytics()
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((requestError) => {
        console.error(requestError);
        setError('No se pudieron consultar las métricas de la base de datos.');
      });

    api.getCurrentExperimentReport()
      .then((result) => {
        setReport(result);
        setReportError(null);
      })
      .catch((requestError) => {
        console.error(requestError);
        setReport(undefined);
        setReportError('El reporte del experimento no está disponible en este momento.');
      });
  }, []);

  const overview = data?.overview;

  return (
    <div className="space-y-4 font-sans text-black">
      {error && <div className="win95-inset bg-white p-2 text-xs font-mono font-bold text-[#cc0000]">{error}</div>}
      {/* Title Panel */}
      <div className="win95-panel p-3">
        <div className="win95-titlebar mb-2">
          <span>Rendimiento y Crecimiento de Capital (Profile)</span>
          <span>{data?.experiment ? `Experimento ${data.experiment.id.slice(0, 8)}` : 'Histórico global'}</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <StatCard
            title="Factor de Ganancia"
            value={overview?.profit_factor?.toFixed(2) ?? '--'}
            subtitle="Ganancias vs Pérdidas"
            trend="up"
          />
          <StatCard
            title="Consistencia Sharpe"
            value={overview?.sharpe_ratio?.toFixed(2) ?? '--'}
            subtitle="Estabilidad de Retornos"
            trend="up"
          />
          <StatCard
            title="Max Drawdown"
            value={overview ? `${overview.max_drawdown_pct.toFixed(2)}%` : '--'}
            subtitle="Caída Máxima Registrada"
            trend="neutral"
          />
          <StatCard
            title="Ganancia Neta"
            value={overview ? `$${overview.total_pnl.toFixed(2)}` : '--'}
            subtitle={overview ? `Éxito: ${overview.win_rate.toFixed(0)}%` : 'Sin datos'}
            trend={overview ? (overview.total_pnl >= 0 ? 'up' : 'down') : 'neutral'}
          />
        </div>
      </div>

      <div className="win95-panel p-3 space-y-3">
        <div className="win95-titlebar">
          <span>Experimento Controlado / Reporte de 30 Días</span>
          <span>{report ? report.run.status : 'TRADEMERC Research'}</span>
        </div>

        {reportError && (
          <div className="win95-inset bg-white p-2 text-xs font-mono font-bold text-[#cc0000]">{reportError}</div>
        )}
        {!reportError && report === undefined && (
          <div className="win95-inset bg-white p-3 text-xs font-mono">Consultando trazabilidad real en TiDB...</div>
        )}
        {!reportError && report === null && (
          <div className="win95-inset bg-white p-3 text-xs font-mono">No existe un experimento de 30 días registrado.</div>
        )}

        {report && (
          <>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
              <div className="win95-inset bg-white p-3 text-xs font-mono">
                <div className="font-bold text-[#000080]">VENTANA</div>
                <div className="mt-2">Inicio: {formatDate(report.run.started_at)}</div>
                <div>Fin previsto: {formatDate(report.run.planned_end_at)}</div>
                <div>Fin real: {formatDate(report.run.finished_at)}</div>
              </div>
              <div className="win95-inset bg-white p-3 text-xs font-mono md:col-span-2">
                <div className="flex justify-between font-bold">
                  <span>Progreso temporal</span>
                  <span>{report.coverage.progress_pct.toFixed(1)}%</span>
                </div>
                <div className="win95-inset-gray mt-2 h-5 p-[2px]">
                  <div className="h-full bg-[#000080]" style={{ width: `${report.coverage.progress_pct}%` }} />
                </div>
                <div className="mt-2 flex flex-wrap justify-between gap-2">
                  <span>Día {report.coverage.elapsed_days} de {report.coverage.target_days}</span>
                  <span>{report.run.symbols.join(', ') || 'Sin símbolos'} / {report.run.timeframe}</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
              <StatCard
                title="Cobertura diaria"
                value={`${report.coverage.coverage_pct.toFixed(2)}%`}
                subtitle={`${report.coverage.days_with_metrics}/${Math.min(report.coverage.target_days, report.coverage.elapsed_days)} días con métricas`}
                trend={report.coverage.coverage_pct >= 99 ? 'up' : 'neutral'}
              />
              <StatCard
                title="Cobertura ciclos"
                value={`${report.coverage.cycle_coverage_pct.toFixed(2)}%`}
                subtitle={`${report.coverage.successful_cycles}/${report.coverage.expected_cycles} ciclos esperados`}
                trend={report.coverage.cycle_coverage_pct >= 99 ? 'up' : 'neutral'}
              />
              <StatCard
                title="Ciclos registrados"
                value={report.coverage.recorded_cycles}
                subtitle={`${report.coverage.successful_cycles} exitosos`}
                trend="neutral"
              />
              <StatCard
                title="Evaluabilidad"
                value={report.evaluability.evaluable ? 'EVALUABLE' : 'PENDIENTE'}
                subtitle={`${Object.values(report.evaluability.criteria).filter(Boolean).length}/${Object.keys(report.evaluability.criteria).length} criterios`}
                trend={report.evaluability.evaluable ? 'up' : 'neutral'}
              />
            </div>

            <div className="win95-inset bg-white p-3">
              <div className="mb-3 text-[10px] font-bold uppercase tracking-wider text-[#808080] font-mono">Funnel observado</div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                {([
                  ['Evaluaciones', report.funnel.evaluations],
                  ['Señales', report.funnel.signals],
                  ['Órdenes', report.funnel.orders],
                  ['Órd. llenadas', report.funnel.filled_orders],
                  ['Fills', report.funnel.fills],
                  ['Trades cerrados', report.funnel.closed_trades],
                ] as [string, number][]).map(([label, value]) => (
                  <div key={label} className="border border-[#808080] bg-[#f5f5f5] p-2 text-center font-mono">
                    <div className="text-lg font-bold text-[#000080]">{value}</div>
                    <div className="text-[10px] font-bold uppercase">{label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              <StatCard title="PnL neto" value={formatMoney(report.performance.net_pnl)} subtitle={`Bruto: ${formatMoney(report.performance.gross_pnl_before_fees)}`} trend={report.performance.net_pnl >= 0 ? 'up' : 'down'} />
              <StatCard title="Profit Factor" value={report.performance.profit_factor === null ? '∞' : report.performance.profit_factor.toFixed(2)} subtitle="Ganancia / pérdida bruta" trend="neutral" />
              <StatCard title="Expectancy" value={formatMoney(report.performance.expectancy)} subtitle="Por trade cerrado" trend={report.performance.expectancy >= 0 ? 'up' : 'down'} />
              <StatCard title="Fees" value={formatMoney(report.performance.fees)} subtitle="Coste atribuido" trend="neutral" />
              <StatCard title="Max Drawdown" value={`${report.performance.max_drawdown_pct.toFixed(2)}%`} subtitle="Desde snapshots" trend="neutral" />
              <StatCard title="Resultado" value={`${report.performance.wins}W / ${report.performance.losses}L`} subtitle={`${report.funnel.closed_trades} cerrados`} trend="neutral" />
            </div>

            <div className="win95-inset bg-white p-3 font-mono">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-[#000080]">CRITERIOS DE EVALUABILIDAD</span>
                <span className={`border px-2 py-1 text-xs font-bold ${report.evaluability.evaluable ? 'border-[#008000] text-[#008000]' : 'border-[#cc0000] text-[#cc0000]'}`}>
                  {report.evaluability.evaluable ? 'APTO PARA EVALUAR' : 'AÚN NO EVALUABLE'}
                </span>
              </div>
              <div className="grid grid-cols-1 gap-1 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(report.evaluability.criteria).map(([criterion, passes]) => (
                  <div key={criterion} className="flex items-center gap-2 text-xs">
                    <span className={`font-bold ${passes ? 'text-[#008000]' : 'text-[#cc0000]'}`}>[{passes ? 'OK' : 'X'}]</span>
                    <span>{criteriaLabels[criterion] || criterion}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
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
