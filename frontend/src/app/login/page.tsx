'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Lock, User, KeyRound } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !pin) {
      setErrorMsg('Por favor ingresa usuario y PIN.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      const res = await api.login(username, pin);
      if (res.success && res.token) {
        localStorage.setItem('trademerc_token', res.token);
        localStorage.setItem('trademerc_user', JSON.stringify(res.user));
        router.push('/');
      } else {
        setErrorMsg(res.message || 'Error de autenticación.');
      }
    } catch (err: any) {
      setErrorMsg('Usuario o PIN incorrectos. Revisa tus datos.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#008080] flex items-center justify-center p-4 font-sans text-black">
      <div className="win95-window w-full max-w-md p-2">
        {/* Title Bar */}
        <div className="win95-titlebar mb-3">
          <div className="flex items-center gap-2">
            <Lock className="h-3.5 w-3.5 text-white" />
            <span>TRADEMERC - Autenticación de Usuario</span>
          </div>
          <div className="flex items-center gap-1">
            <button className="win95-button px-1.5 py-0 text-[10px] text-black">_</button>
            <button className="win95-button px-1.5 py-0 text-[10px] text-black">▢</button>
            <button className="win95-button px-1.5 py-0 text-[10px] text-black font-bold">✕</button>
          </div>
        </div>

        {/* Login Box Panel */}
        <div className="win95-panel p-4 space-y-4">
          <div className="win95-inset bg-white p-3 text-center space-y-1">
            <div className="font-bold text-sm font-mono text-[#000080]">ACCESO PRIVADO AL SISTEMA</div>
            <div className="text-xs text-[#808080] font-mono">Ingresa tus credenciales autorizadas</div>
          </div>

          {errorMsg && (
            <div className="win95-inset bg-white p-2 text-xs font-mono text-[#cc0000] font-bold text-center">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-bold font-mono flex items-center gap-1">
                <User className="h-3.5 w-3.5 text-[#000080]" />
                <span>Nombre de Usuario:</span>
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Usuario"
                className="w-full win95-inset bg-white p-2 text-xs font-mono outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold font-mono flex items-center gap-1">
                <KeyRound className="h-3.5 w-3.5 text-[#000080]" />
                <span>PIN de Seguridad:</span>
              </label>
              <input
                type="password"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="Ingresa tu PIN"
                className="w-full win95-inset bg-white p-2 text-xs font-mono outline-none"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="win95-button w-full py-2 text-xs font-mono font-bold bg-[#000080] text-white flex items-center justify-center gap-2"
              >
                <Lock className="h-3.5 w-3.5" />
                <span>{loading ? 'INICIANDO SESIÓN...' : 'INICIAR SESIÓN'}</span>
              </button>
            </div>
          </form>

          <div className="win95-inset bg-white p-2 text-center text-[10px] font-mono text-[#808080]">
            TRADEMERC Security Module · Acceso Restringido a Administrador
          </div>
        </div>
      </div>
    </div>
  );
}
