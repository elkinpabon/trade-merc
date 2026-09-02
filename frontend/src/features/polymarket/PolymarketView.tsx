'use client';

import React, { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';
import { TrendingUp, Terminal, Award } from 'lucide-react';

export const PolymarketView: React.FC = () => {
  const [category, setCategory] = useState<string>('ALL');
  const [markets, setMarkets] = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [liveLogs, setLiveLogs] = useState<any[]>([]);
  const [isBotRunning, setIsBotRunning] = useState<boolean>(false);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [gammaAvailable, setGammaAvailable] = useState<boolean | null>(null);
  const [availabilityMessage, setAvailabilityMessage] = useState('Verificando infraestructura de Polymarket...');
  const logsEndRef = useRef<HTMLDivElement>(null);

  const loadData = async (cancelled: () => boolean) => {
    const [marketsResult, statusResult, positionsResult, analyticsResult, logsResult] = await Promise.allSettled([
      api.getPolymarketMarkets(category),
      api.getPolymarketBotStatus(),
      api.getPolymarketPositions(),
      api.getPolymarketAnalytics(),
      api.getPolymarketLiveLogs(),
    ]);
    if (cancelled()) return;

    if (marketsResult.status === 'fulfilled') {
      setMarkets(marketsResult.value.markets || []);
      setGammaAvailable(true);
    } else {
      console.error('Polymarket Gamma feed unavailable:', marketsResult.reason);
      setMarkets([]);
      setGammaAvailable(false);
    }

    const infrastructureAvailable = statusResult.status === 'fulfilled' && statusResult.value.available;
    setAvailable(infrastructureAvailable);
    setIsBotRunning(infrastructureAvailable ? statusResult.value.is_running : false);
    setAvailabilityMessage(infrastructureAvailable
      ? 'Infraestructura opcional disponible.'
      : 'Infraestructura opcional de bot, ejecución y persistencia no disponible.');
    setPositions(infrastructureAvailable && positionsResult.status === 'fulfilled' ? positionsResult.value : []);
    setAnalytics(infrastructureAvailable && analyticsResult.status === 'fulfilled' ? analyticsResult.value : null);
    setLiveLogs(infrastructureAvailable && logsResult.status === 'fulfilled' ? logsResult.value.logs || [] : []);
  };

  useEffect(() => {
    let cancelled = false;
    const refresh = () => loadData(() => cancelled);
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [category]);

  const categories = [
    { id: 'ALL', label: 'TODOS LOS MERCADOS' },
    { id: 'Crypto', label: 'CRIPTO' },
    { id: 'Macro', label: 'MACROECONOMÍA' },
    { id: 'Politics', label: 'POLÍTICA' },
    { id: 'Tech', label: 'TECNOLOGÍA & IA' }
  ];

  return (
    <div className="space-y-3 font-sans text-black">
      {/* Top Banner Toolbar */}
      <div className="win95-window p-2">
        <div className="win95-titlebar flex flex-wrap sm:flex-nowrap items-center justify-between gap-1">
          <div className="flex items-center gap-1.5 shrink-0">
            <TrendingUp className="h-4 w-4 text-emerald-300" />
            <span className="font-bold text-xs font-mono">POLYMARKET</span>
          </div>
          <span className="text-emerald-300 font-mono text-[9px] sm:text-[11px] font-bold truncate max-w-full">
             FEED GAMMA: {gammaAvailable === null ? 'VERIFICANDO' : gammaAvailable ? 'DISPONIBLE' : 'NO DISPONIBLE'} · DATOS REALES
          </span>
        </div>

        <div className="p-2 bg-[#c0c0c0] flex flex-wrap items-center justify-between gap-2 border-b border-[#808080]">
          <div className="flex items-center gap-2">
            <span className={`win95-button px-4 py-1.5 text-xs font-bold font-mono ${isBotRunning ? 'text-[#008000]' : 'text-[#808080]'}`}>
              BOT: {available === null ? 'VERIFICANDO' : available ? (isBotRunning ? 'ACTIVO EN DB' : 'DETENIDO') : 'NO DISPONIBLE'}
            </span>

            <span className="text-xs font-mono text-black font-bold px-2 py-1 win95-inset bg-white">
               MODO: SOLO LECTURA
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="win95-inset px-2 py-1 bg-white font-bold text-[#000080]">
               PNL REALIZADO: ${analytics?.realized_pnl?.toFixed(2) ?? '--'} USD
            </span>
            <span className="win95-inset px-2 py-1 bg-white font-bold text-[#008000]">
               ACIERTO: {analytics?.prediction_win_rate_pct?.toFixed(1) ?? '--'}%
            </span>
          </div>
        </div>

        {available === false && (
          <div className="m-2 win95-inset bg-white p-2 text-center text-xs font-mono text-[#808080]">
            {availabilityMessage} El feed Gamma funciona de forma independiente.
          </div>
        )}

      </div>

      {/* Category Tabs & Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {/* Category Filters */}
        <div className="md:col-span-3 win95-panel p-2 flex flex-wrap gap-1 items-center">
          <span className="text-xs font-mono font-bold mr-2">CATEGORÍAS:</span>
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategory(c.id)}
              className={`win95-button px-3 py-1 text-xs font-mono font-bold ${
                category === c.id ? 'win95-button-active bg-[#008080] text-white' : 'bg-white'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Quick Stat */}
        <div className="win95-panel p-2 flex items-center justify-between bg-white font-mono text-xs">
          <div>
            <div className="text-[10px] text-[#808080] font-bold">CONTRATOS ACTIVOS</div>
            <div className="text-sm font-bold text-[#000080]">{positions.length} Posiciones</div>
          </div>
          <Award className="h-6 w-6 text-[#008080]" />
        </div>
      </div>

      {/* Main Content Grid: Active Predictions & Live Tactical Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Active Prediction Markets Grid (2 Cols) */}
        <div className="lg:col-span-2 space-y-2">
          <div className="win95-window">
            <div className="win95-titlebar flex flex-wrap sm:flex-nowrap items-center justify-between gap-1 text-[11px] sm:text-xs">
              <span className="truncate">Mercados de Predicción de Alto Volumen</span>
              <span className="shrink-0">{markets.length} Eventos Escaneados</span>
            </div>

            <div className="p-2 space-y-3 max-h-[500px] overflow-y-auto bg-[#c0c0c0]">
              {markets.length > 0 ? (
                markets.map((m) => {
                  const yesPrice = m.prices[0];
                  const noPrice = m.prices[1];
                  const yesProb = Math.round(yesPrice * 100);

                  return (
                    <div key={m.id} className="win95-panel p-3 bg-white space-y-2 border border-[#404040]">
                      <div className="flex flex-col sm:flex-row items-start justify-between gap-2">
                        <div className="space-y-1">
                          <span className="win95-button text-[10px] font-mono px-1.5 py-0.5 bg-[#008080] text-white font-bold inline-block mr-2">
                            {m.category}
                          </span>
                          <h3 className="font-bold text-xs font-sans inline text-black leading-snug">{m.question}</h3>
                        </div>
                        <div className="text-left sm:text-right font-mono shrink-0">
                          <span className="text-xs font-bold text-[#000080] bg-[#e6f0ff] px-2 py-0.5 border border-[#000080] rounded-sm inline-block">
                            LIQUIDEZ: ${Number(m.liquidity).toLocaleString()}
                          </span>
                        </div>
                      </div>

                      {/* Probability Bar */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px] font-mono font-bold">
                          <span className="text-[#008000]">SI (YES): {yesProb}% (${yesPrice.toFixed(2)})</span>
                          <span className="text-[#cc0000]">NO: {100 - yesProb}% (${noPrice.toFixed(2)})</span>
                        </div>
                        <div className="w-full bg-[#e0e0e0] h-3 win95-inset flex overflow-hidden">
                          <div className="bg-[#008000] h-full transition-all duration-300" style={{ width: `${yesProb}%` }} />
                          <div className="bg-[#cc0000] h-full transition-all duration-300" style={{ width: `${100 - yesProb}%` }} />
                        </div>
                      </div>

                      {/* Market Info & Action Buttons */}
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pt-2 border-t border-[#e0e0e0] text-xs font-mono">
                        <div className="text-[10px] text-[#808080] space-x-1">
                          <span>Vol: <strong className="text-black">${(m.volume / 1000).toFixed(1)}k</strong></span>
                          <span>·</span>
                          <span>Fuente: <strong className="text-black">Gamma API</strong></span>
                        </div>

                        <span className="win95-button px-3 py-1 text-[10px] font-bold text-[#808080]">EJECUCIÓN NO DISPONIBLE</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="win95-inset bg-white p-6 text-center text-xs font-mono text-[#808080]">
                  {gammaAvailable === false ? 'Feed Gamma no disponible.' : 'No hay mercados reportados por Polymarket.'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Live Tactical Prediction Logs Console (1 Col) */}
        <div className="space-y-3">
          <div className="win95-window">
            <div className="win95-titlebar flex flex-wrap sm:flex-nowrap items-center justify-between gap-1 text-[11px] sm:text-xs">
              <div className="flex items-center gap-2 truncate">
                <Terminal className="h-3.5 w-3.5 text-white shrink-0" />
                <span className="truncate">CONSOLA POLYMARKET</span>
              </div>
              <span className="text-[#c0c0c0] font-bold text-[10px] shrink-0">SOLO LECTURA</span>
            </div>

            <div className="win95-inset bg-white p-3 font-mono text-xs text-black h-[480px] overflow-y-auto space-y-1">
              <div className="text-[#808080] text-[10px] border-b border-[#e5e5e5] pb-1 mb-2">
                === LOGS DE PREDICCIÓN POLYMARKET ===
              </div>
              {liveLogs.length > 0 ? (
                liveLogs.map((log, idx) => {
                  const msg = log.message || '';
                  let msgColor = 'text-[#007a3d]';
                  if (msg.includes('+EV=')) msgColor = 'text-[#b45309] font-bold';
                  if (msg.includes('OPORTUNIDAD ALTA') || msg.includes('COMPRA SUGERIDA')) msgColor = 'text-[#000080] font-bold';
                  if (msg.includes('Contrato Comprado')) msgColor = 'text-[#6b21a8] font-bold bg-[#f0fdf4]';

                  return (
                    <div key={idx} className="leading-tight flex items-start gap-1 hover:bg-[#f0f0f0] px-1 border-b border-[#f5f5f5]">
                      <span className="text-[#808080] shrink-0 text-[10px]">
                        [{new Date(log.timestamp || Date.now()).toLocaleTimeString()}]
                      </span>
                      <span className={msgColor}>{msg}</span>
                    </div>
                  );
                })
              ) : (
                <div className="text-[#808080] font-mono">
                  {available === false ? 'Módulo opcional de logs no disponible.' : 'No hay logs registrados en la infraestructura de Polymarket.'}
                </div>
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      </div>

      {/* Active Positions Table Panel */}
      <div className="win95-panel p-3 space-y-3">
        <div className="win95-titlebar flex flex-wrap sm:flex-nowrap items-center justify-between gap-1 text-[11px] sm:text-xs">
          <span className="truncate">Contratos Comprados Actualmente</span>
          <span className="shrink-0">{positions.length} Posiciones Activas</span>
        </div>

        {positions.length > 0 ? (
          <div className="space-y-2">
            {positions.map((pos) => (
              <div key={pos.id} className="win95-panel p-3 bg-white border border-[#404040] font-mono">
                <div className="flex flex-wrap items-center justify-between border-b border-[#c0c0c0] pb-2 mb-2 gap-2">
                  <div className="font-bold text-xs text-black">
                    <span className={`px-2 py-0.5 text-white font-bold text-[10px] mr-2 ${pos.outcome === 'YES' ? 'bg-[#008000]' : 'bg-[#cc0000]'}`}>
                      {pos.outcome}
                    </span>
                    {pos.question}
                  </div>
                  <div className={`font-bold text-xs ${pos.unrealized_pnl >= 0 ? 'text-[#008000]' : 'text-[#cc0000]'}`}>
                    {pos.unrealized_pnl >= 0 ? '+' : ''}${parseFloat(pos.unrealized_pnl).toFixed(2)} USD
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                  <div>
                    <div className="text-[10px] text-[#808080]">ACCIONES</div>
                    <div className="font-bold">{parseFloat(pos.shares).toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080]">PRECIO ENTRADA</div>
                    <div className="font-bold">${parseFloat(pos.contract_price).toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080]">COSTO TOTAL</div>
                    <div className="font-bold">${parseFloat(pos.total_cost).toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080]">PROBABILIDAD ACTUAL</div>
                    <div className="font-bold text-[#000080]">{(parseFloat(pos.current_prob) * 100).toFixed(0)}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#808080]">ESTADO</div>
                    <div className="font-bold text-[#008000]">OPERANDO Y MONITOREANDO</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="win95-inset bg-white p-6 text-center text-xs font-mono text-[#808080]">
            {available === false ? 'Módulo opcional de posiciones no disponible.' : 'No hay posiciones activas registradas en Polymarket.'}
          </div>
        )}
      </div>
    </div>
  );
};
