'use client';

import React, { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';
import { useSocket } from '@/hooks/useSocket';
import { Play, Square } from 'lucide-react';

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [timeStr, setTimeStr] = useState<string>('12:00');
  const { isConnected } = useSocket();

  const isPolymarketPage = pathname === '/polymarket';

  useEffect(() => {
    if (!isPolymarketPage) {
      api.getBotStatus()
        .then((res) => setIsRunning(res.is_running))
        .catch(console.error);
    }

    const timer = setInterval(() => {
      const d = new Date();
      setTimeStr(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 1000);

    return () => clearInterval(timer);
  }, [isPolymarketPage]);

  const toggleBot = async () => {
    setLoading(true);
    try {
      if (isRunning) {
        await api.stopBot();
        setIsRunning(false);
      } else {
        await api.startBot();
        setIsRunning(true);
      }
    } catch (err) {
      console.error('Error al cambiar estado del bot crypto:', err);
    } finally {
      setLoading(false);
    }
  };

  // If inside Polymarket Workspace, render clean isolated header
  if (isPolymarketPage) {
    return (
      <header className="win95-window mb-2">
        <div className="win95-titlebar flex flex-wrap sm:flex-nowrap items-center justify-between gap-1">
          <div className="flex items-center gap-1.5 shrink-0">
            <img src="/icon.png" alt="TRADEMERC Logo" className="h-4 w-4 rounded-sm border border-white/40 object-cover" />
            <span className="font-bold text-xs font-mono">{timeStr}</span>
            <span className="text-emerald-300 font-mono text-[10px] sm:text-[11px] truncate">| POLYMARKET.EXE</span>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap sm:flex-nowrap">
            <span className="text-[9px] sm:text-[11px] font-mono text-emerald-300 font-bold truncate max-w-full">
              Polygon CLOB & Gamma API · online
            </span>
            <div className="flex items-center gap-1 shrink-0">
              <button className="win95-button px-1.5 py-0 text-[10px] text-black">_</button>
              <button className="win95-button px-1.5 py-0 text-[10px] text-black">▢</button>
              <button className="win95-button px-1.5 py-0 text-[10px] text-black font-bold">✕</button>
            </div>
          </div>
        </div>
      </header>
    );
  }

  // Crypto Workspace Header
  return (
    <header className="win95-window mb-2">
      {/* Titlebar */}
      <div className="win95-titlebar flex flex-wrap sm:flex-nowrap items-center justify-between gap-1">
        <div className="flex items-center gap-1.5 shrink-0">
          <img src="/icon.png" alt="TRADEMERC Logo" className="h-4 w-4 rounded-sm border border-white/40 object-cover" />
          <span className="font-bold text-xs font-mono">{timeStr}</span>
          <span className="text-slate-300 font-mono text-[10px] sm:text-[11px] truncate">| TRADEMERC.EXE</span>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap sm:flex-nowrap">
          <span className="text-[9px] sm:text-[11px] font-mono text-emerald-300 font-bold truncate max-w-full">
            Binance · {isConnected ? 'online' : 'connecting'}
          </span>
          <div className="flex items-center gap-1 shrink-0">
            <button className="win95-button px-1.5 py-0 text-[10px] text-black">_</button>
            <button className="win95-button px-1.5 py-0 text-[10px] text-black">▢</button>
            <button className="win95-button px-1.5 py-0 text-[10px] text-black font-bold">✕</button>
          </div>
        </div>
      </div>

      {/* Menu / Bot Action Toolbar */}
      <div className="p-2 bg-[#c0c0c0] flex flex-wrap items-center justify-between gap-2 border-b border-[#808080]">
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={toggleBot}
            disabled={loading}
            className={`win95-button px-3 sm:px-4 py-1 text-xs font-bold font-mono flex items-center gap-1.5 ${
              isRunning ? 'bg-[#cc0000] text-white' : 'bg-[#008000] text-white'
            }`}
          >
            {isRunning ? <Square className="h-3 w-3 fill-current" /> : <Play className="h-3 w-3 fill-current" />}
            <span className="truncate">{loading ? 'CARGANDO...' : isRunning ? 'PAUSAR BOT CRYPTO ML' : 'ACTIVAR BOT CRYPTO ML'}</span>
          </button>

          <span className="text-[10px] sm:text-xs font-mono text-black font-bold px-2 py-1 win95-inset bg-white truncate max-w-full">
            MODO: CRYPTO SPOT SIMULACIÓN
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-black">
          <span className="win95-inset px-2 py-0.5 bg-white font-bold text-[#008000] text-[10px] sm:text-xs">
            ESTADO: {isRunning ? 'EJECUTANDO 24/7' : 'EN ESPERA'}
          </span>
        </div>
      </div>
    </header>
  );
};
