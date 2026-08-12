'use client';

import React, { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Navbar } from '@/components/layout/Navbar';
import { Sidebar } from '@/components/layout/Sidebar';
import { api } from '@/lib/api';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    if (pathname === '/login') {
      setAuthed(true);
      return;
    }

    const token = localStorage.getItem('trademerc_token');
    if (!token) {
      setAuthed(false);
      router.push('/login');
      return;
    }

    api.verifyAuth()
      .then(() => setAuthed(true))
      .catch(() => {
        setAuthed(false);
        localStorage.removeItem('trademerc_token');
        router.push('/login');
      });
  }, [pathname, router]);

  if (pathname === '/login') {
    return <>{children}</>;
  }

  if (authed === null) {
    return (
      <div className="min-h-screen bg-[#008080] flex items-center justify-center p-4 font-mono text-xs">
        <div className="win95-window p-4 bg-[#c0c0c0] font-bold">
          Verificando sesión segura TRADEMERC...
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-2">
      <Navbar />
      <Sidebar />
      <main className="win95-window p-3 sm:p-4 min-h-[600px] bg-[#c0c0c0]">
        {children}
      </main>

      <footer className="win95-panel p-2 flex items-center justify-between text-xs font-mono text-black">
        <div>TRADEMERC v1.0</div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              localStorage.removeItem('trademerc_token');
              router.push('/login');
            }}
            className="win95-button px-2 py-0.5 text-[10px] text-[#cc0000] font-bold"
          >
            CERRAR SESIÓN
          </button>
          <span className="win95-inset px-2 py-0.5 bg-white">OK</span>
          <span>Memory: 64MB RAM</span>
        </div>
      </footer>
    </div>
  );
};
