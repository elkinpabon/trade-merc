'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useSocket } from '@/hooks/useSocket';
import { BotLogData, SystemHealthData } from '@/types';

export const LogsView: React.FC = () => {
  const [logs, setLogs] = useState<BotLogData[]>([]);
  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { socket } = useSocket();

  const loadData = async () => {
    setLoading(true);
    try {
      const logData = await api.getLogs(100);
      setLogs(logData);
      const hData = await api.getHealth();
      setHealth(hData);
      setError(null);
    } catch (err) {
      console.error('Error al cargar diagnóstico:', err);
      setError('No se pudieron consultar los logs o el estado del sistema.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    socket.on('system_log', (newLog: BotLogData) => {
      setLogs((prev) => [newLog, ...prev.slice(0, 99)]);
    });

    socket.on('health_update', (hData: SystemHealthData) => {
      setHealth(hData);
    });

    return () => {
      socket.off('system_log');
      socket.off('health_update');
    };
  }, [socket]);

  return (
    <div className="space-y-3 font-sans text-black">
      <div className="win95-panel p-3 space-y-2">
        <div className="win95-titlebar">
          <span>Diagnóstico y Estado del Sistema (Logs)</span>
          <span>TRADEMERC Event Log</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs font-bold font-mono">Consola de Eventos en Tiempo Real</span>
          <button onClick={loadData} className="win95-button px-3 py-1 text-xs font-mono font-bold">
            {loading ? 'RESCANIANDO...' : 'ACTUALIZAR LOGS'}
          </button>
        </div>

        {error && <div className="win95-inset bg-white p-2 text-xs font-mono font-bold text-[#cc0000]">{error}</div>}

        <div className="win95-inset bg-white p-3 font-mono text-xs h-[380px] overflow-y-auto space-y-1">
          {!error && logs.length > 0 ? (
            logs.map((l, idx) => (
              <div key={idx} className="flex items-start gap-2 border-b border-[#e5e5e5] pb-1 text-[11px]">
                <span className="text-[#808080] shrink-0">{new Date(l.timestamp).toLocaleTimeString()}</span>
                <span
                  className={`font-bold shrink-0 w-16 uppercase ${
                    l.level === 'INFO'
                      ? 'text-[#000080]'
                      : l.level === 'WARNING'
                      ? 'text-[#d97706]'
                      : l.level === 'ERROR'
                      ? 'text-[#cc0000]'
                      : 'text-black'
                  }`}
                >
                  [{l.level}]
                </span>
                <span className="font-bold shrink-0 text-[#808080]">[{l.module}]</span>
                <span>{l.message}</span>
              </div>
            ))
          ) : (
            <div className="text-[#808080] text-center py-12">{error || 'No hay registros de eventos disponibles.'}</div>
          )}
        </div>
      </div>
    </div>
  );
};
