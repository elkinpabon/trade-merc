'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Play, Square } from 'lucide-react';

export const BotControlPanel: React.FC = () => {
  const [riskPreset, setRiskPreset] = useState<'conservador' | 'equilibrado' | 'crecimiento'>('equilibrado');
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    api.getBotStatus().then((res) => setIsRunning(res.is_running)).catch(console.error);
  }, []);

  const handleToggleBot = async () => {
    setLoading(true);
    setStatusMsg(null);
    try {
      if (isRunning) {
        await api.stopBot();
        setIsRunning(false);
        setStatusMsg('Bot pausado correctamente.');
      } else {
        await api.startBot();
        setIsRunning(true);
        setStatusMsg('Bot activado en Piloto Automático.');
      }
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = async (preset: 'conservador' | 'equilibrado' | 'crecimiento') => {
    setRiskPreset(preset);
    let sl = 1.5, tp = 3.0;
    if (preset === 'conservador') { sl = 1.0; tp = 2.0; }
    if (preset === 'crecimiento') { sl = 3.0; tp = 6.0; }

    try {
      await api.updateConfig({ stop_loss_pct: sl, take_profit_pct: tp });
      setStatusMsg(`Modo de riesgo [${preset.toUpperCase()}] aplicado.`);
    } catch (err: any) {
      setStatusMsg(`Error al aplicar preset: ${err.message}`);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-3 font-sans text-black">
      <div className="win95-panel p-3 space-y-3">
        <div className="win95-titlebar">
          <span>Configuración del Bot (Bot Config)</span>
          <span>TRADEMERC Control</span>
        </div>

        {statusMsg && (
          <div className="win95-inset bg-white p-2 text-xs font-mono text-[#008000] font-bold">
            {statusMsg}
          </div>
        )}

        <div className="win95-inset bg-white p-4 text-center space-y-3">
          <h2 className="text-sm font-bold font-mono uppercase">Estado del Piloto Automático</h2>
          <button
            onClick={handleToggleBot}
            disabled={loading}
            className={`win95-button w-full py-3 text-sm font-mono font-bold flex items-center justify-center gap-2 ${
              isRunning ? 'bg-[#cc0000] text-white' : 'bg-[#008000] text-white'
            }`}
          >
            {isRunning ? <Square className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 fill-current" />}
            <span>{loading ? 'PROCESANDO...' : isRunning ? 'PAUSAR BOT AUTOMÁTICO' : 'ACTIVAR BOT AUTOMÁTICO'}</span>
          </button>
        </div>

        <div className="space-y-2">
          <div className="text-xs font-bold font-mono">Selecciona el Perfil de Riesgo:</div>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'conservador', label: 'Conservador', desc: 'SL 1.0% / TP 2.0%' },
              { id: 'equilibrado', label: 'Equilibrado', desc: 'SL 1.5% / TP 3.0%' },
              { id: 'crecimiento', label: 'Crecimiento', desc: 'SL 3.0% / TP 6.0%' },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => applyPreset(item.id as any)}
                className={`win95-button p-3 text-center text-xs font-mono ${
                  riskPreset === item.id ? 'win95-button-active' : ''
                }`}
              >
                <div className="font-bold">{item.label}</div>
                <div className="text-[10px] opacity-75 mt-1">{item.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
