'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart2, Zap, Repeat, User, Settings, Lock, Terminal } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const navItems = [
    { label: 'Markets', path: '/market', icon: <BarChart2 className="h-3.5 w-3.5" /> },
    { label: 'Signal', path: '/', icon: <Zap className="h-3.5 w-3.5" /> },
    { label: 'Trades', path: '/trades', icon: <Repeat className="h-3.5 w-3.5" /> },
    { label: 'Profile', path: '/analytics', icon: <User className="h-3.5 w-3.5" /> },
    { label: 'Bot Config', path: '/bot-control', icon: <Settings className="h-3.5 w-3.5" /> },
    { label: 'Seguridad', path: '/exchange-settings', icon: <Lock className="h-3.5 w-3.5" /> },
    { label: 'Logs', path: '/logs', icon: <Terminal className="h-3.5 w-3.5" /> },
  ];

  return (
    <nav className="win95-window p-1 mb-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-1">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`win95-button py-2 px-2 text-center text-xs font-mono font-bold flex flex-col items-center justify-center gap-1 transition-none ${
                isActive ? 'win95-button-active' : ''
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
};
