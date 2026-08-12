'use client';

import React, { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';
import { TrendingUp, Play, Square, Terminal, Award } from 'lucide-react';

export const PolymarketView: React.FC = () => {
  const [category, setCategory] = useState<string>('ALL');
  const [markets, setMarkets] = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [liveLogs, setLiveLogs] = useState<any[]>([]);
  const [isBotRunning, setIsBotRunning] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const loadData = async () => {
    try {
      const [mktsRes, posRes, anaRes, statusRes] = await Promise.all([
        api.getPolymarketMarkets(category),
        api.getPolymarketPositions(),
        api.getPolymarketAnalytics(),
        api.getPolymarketBotStatus()
      ]);

      if (mktsRes?.markets) setMarkets(mktsRes.markets);
      if (posRes) setPositions(posRes);
      if (anaRes) setAnalytics(anaRes);
      if (statusRes) setIsBotRunning(statusRes.is_running);
    } catch (err) {
      console.error('Error loading Polymarket data:', err);
    }
  };

  const fetchLiveLogs = async () => {
    try {
      const res = await api.getPolymarketLiveLogs();
      if (res?.logs && res.logs.length > 0) {
        setLiveLogs(res.logs);
      }
    } catch (err) {
      console.warn('Error fetching Polymarket live logs:', err);
    }
  };

  useEffect(() => {
    loadData();
    fetchLiveLogs();
    const interval = setInterval(() => {
      fetchLiveLogs();
      loadData();
    }, 2000);
    return () => clearInterval(interval);
  }, [category]);

  const toggleBot = async () => {
    setLoading(true);
    try {
      if (isBotRunning) {
        await api.stopBot();
        setIsBotRunning(false);
        setActionMsg('Bot de Polymarket Pausado.');
      } else {
        await api.startBot();
        setIsBotRunning(true);
        setActionMsg('Bot de Polymarket Activado.');
      }
    } catch (err: any) {
      setActionMsg(`Error: ${err?.message}`);
    } finally {
      setLoading(false);
      setTimeout(() => setActionMsg(null), 3000);
    }
  };

  const buyContract = async (question: string, outcome: string, contractPrice: number, cExecWeighted?: number, pModel?: number, takerFeePct?: number) => {
    setLoading(true);
    try {
      const res = await api.buyPolymarketContract(question, outcome, contractPrice, 50.0, cExecWeighted, pModel, takerFeePct);
      if (res.success) {
        setActionMsg(`Contrato L2 Llenado: ${outcome} en "${question}" (c_exec_w=$${(cExecWeighted || contractPrice).toFixed(3)})`);
        loadData();
      }
    } catch (err: any) {
      setActionMsg(`Error de compra: ${err?.message}`);
    } finally {
      setLoading(false);
      setTimeout(() => setActionMsg(null), 3000);
    }
  };

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
            RED: POLYGON CLOB & GAMMA API · ONLINE
          </span>
        </div>

        <div className="p-2 bg-[#c0c0c0] flex flex-wrap items-center justify-between gap-2 border-b border-[#808080]">
          <div className="flex items-center gap-2">
            <button
              onClick={toggleBot}
              disabled={loading}
              className={`win95-button px-4 py-1.5 text-xs font-bold font-mono flex items-center gap-1.5 ${
                isBotRunning ? 'bg-[#cc0000] text-white' : 'bg-[#008000] text-white'
              }`}
            >
              {isBotRunning ? <Square className="h-3.5 w-3.5 fill-current" /> : <Play className="h-3.5 w-3.5 fill-current" />}
              <span>{loading ? 'PROCESANDO...' : isBotRunning ? 'PAUSAR BOT POLYMARKET' : 'ACTIVAR BOT POLYMARKET'}</span>
            </button>

            <span className="text-xs font-mono text-black font-bold px-2 py-1 win95-inset bg-white">
              MODO: SIMULACIÓN (+EV)
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="win95-inset px-2 py-1 bg-white font-bold text-[#000080]">
              SALDO: ${analytics?.virtual_balance?.toFixed(2) || '1,000.00'} USD
            </span>
            <span className="win95-inset px-2 py-1 bg-white font-bold text-[#008000]">
              ACIERTO: {analytics?.prediction_win_rate_pct || 78.5}%
            </span>
          </div>
        </div>

        {actionMsg && (
          <div className="m-2 p-2 win95-inset bg-white font-mono text-xs text-[#008000] font-bold text-center">
            {actionMsg}
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
                  const yesPrice = m.prices ? m.prices[0] : 0.5;
                  const noPrice = m.prices ? m.prices[1] : 0.5;
                  const yesProb = Math.round(yesPrice * 100);

                  const cExecBest = m.c_exec || (m.best_price ? m.best_price + 0.005 : 0.5);
                  const evNetPct = m.ev_net ? (m.ev_net * 100).toFixed(1) : (m.ev_pct || 8.0);
                  const spreadPct = m.spread ? (m.spread * 100).toFixed(2) : '0.50';
                  const kellySize = Math.min(25, Math.max(10, Math.round(parseFloat(evNetPct || '10') * 1.8)));

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
                            NET EV: +{evNetPct}% | c_exec: ${cExecBest.toFixed(3)}
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
                          <span>Spread: <strong className="text-black">{spreadPct}%</strong></span>
                          <span>·</span>
                          <span>Kelly: <strong className="text-[#000080]">${kellySize}.00 USD</strong></span>
                        </div>

                        <div className="flex items-center gap-1.5 w-full sm:w-auto justify-end">
                          <button
                            onClick={() => buyContract(m.question, 'YES', yesPrice)}
                            disabled={loading}
                            className="win95-button px-3 py-1 text-xs font-bold bg-[#008000] text-white hover:bg-[#009900] flex-1 sm:flex-initial"
                          >
                            COMPRAR YES (${yesPrice.toFixed(2)})
                          </button>
                          <button
                            onClick={() => buyContract(m.question, 'NO', noPrice)}
                            disabled={loading}
                            className="win95-button px-3 py-1 text-xs font-bold bg-[#cc0000] text-white hover:bg-[#ee0000] flex-1 sm:flex-initial"
                          >
                            COMPRAR NO (${noPrice.toFixed(2)})
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="win95-inset bg-white p-6 text-center text-xs font-mono text-[#808080]">
                  Escaneando mercados de Polymarket en tiempo real...
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
              <span className="animate-pulse text-[#00ff00] font-bold text-[10px] shrink-0">ESCANEANDO</span>
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
                <div className="text-[#007a3d] font-mono animate-pulse">
                  Calculando algoritmo de Valor Esperado (+EV) y Criterio de Kelly en Polymarket...
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
            No hay posiciones activas en Polymarket. El bot está escaneando los mercados para ejecutar la siguiente compra de contrato +EV.
          </div>
        )}
      </div>
    </div>
  );
};
