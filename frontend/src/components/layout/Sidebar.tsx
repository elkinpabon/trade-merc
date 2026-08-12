'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart2, Zap, Repeat, User, Settings, Lock, Terminal, RefreshCw } from 'lucide-react';
import { WorkspaceLoader } from '@/components/common/WorkspaceLoader';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const [switchingTo, setSwitchingTo] = useState<{ path: string; name: string; desc: string } | null>(null);

  const isPolymarketPage = pathname === '/polymarket';

  const cryptoNavItems = [
    { label: 'Markets', path: '/market', icon: <BarChart2 className="h-3.5 w-3.5" /> },
    { label: 'Signals', path: '/', icon: <Zap className="h-3.5 w-3.5" /> },
    { label: 'Trades', path: '/trades', icon: <Repeat className="h-3.5 w-3.5" /> },
    { label: 'Profile', path: '/analytics', icon: <User className="h-3.5 w-3.5" /> },
    { label: 'Bot Config', path: '/bot-control', icon: <Settings className="h-3.5 w-3.5" /> },
    { label: 'Seguridad', path: '/exchange-settings', icon: <Lock className="h-3.5 w-3.5" /> },
    { label: 'Logs', path: '/logs', icon: <Terminal className="h-3.5 w-3.5" /> },
  ];

  if (isPolymarketPage) {
    return (
      <>
        {switchingTo && (
          <WorkspaceLoader
            targetPath={switchingTo.path}
            targetName={switchingTo.name}
            targetDesc={switchingTo.desc}
          />
        )}
        <nav className="win95-window p-1 mb-3">
          <div className="flex items-center justify-between px-2 py-1">
            <div className="text-xs font-mono font-bold text-[#000080]">
              ENTORNO TÁCTICO POLYMARKET (MERCADOS DE PREDICCIÓN)
            </div>
            <button
              onClick={() => setSwitchingTo({ path: '/', name: 'TRADEMERC CRYPTO BOT', desc: 'Trading Algorítmico Binance · 10 Indicadores + ML' })}
              className="win95-button py-1.5 px-3 text-xs font-mono font-bold bg-[#000080] text-white flex items-center gap-1.5 hover:bg-[#0000a0]"
            >
              <RefreshCw className="h-3.5 w-3.5 text-yellow-300" />
              <span>CAMBIAR A MÓDULO CRYPTO</span>
            </button>
          </div>
        </nav>
      </>
    );
  }

  return (
    <>
      {switchingTo && (
        <WorkspaceLoader
          targetPath={switchingTo.path}
          targetName={switchingTo.name}
          targetDesc={switchingTo.desc}
        />
      )}
      <nav className="win95-window p-1 mb-3">
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-1">
          {cryptoNavItems.map((item) => {
            const isActive = pathname === item.path;
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`win95-button py-2 px-1 text-center text-xs font-mono font-bold flex flex-col items-center justify-center gap-1 transition-none ${
                  isActive ? 'win95-button-active' : ''
                }`}
              >
                <span>{item.icon}</span>
                <span className="truncate max-w-full">{item.label}</span>
              </Link>
            );
          })}

          <button
            onClick={() => setSwitchingTo({ path: '/polymarket', name: 'TRADEMERC POLYMARKET BOT', desc: 'Mercados de Predicción · Ventaja +EV' })}
            className="win95-button py-2 px-1 text-center text-xs font-mono font-bold flex flex-col items-center justify-center gap-1 bg-[#008080] text-white hover:bg-[#009090]"
          >
            <RefreshCw className="h-3.5 w-3.5 text-emerald-300" />
            <span className="truncate max-w-full">CAMBIAR MÓDULO</span>
          </button>
        </div>
      </nav>
    </>
  );
};
