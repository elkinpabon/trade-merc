'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Lock, User, KeyRound, TrendingUp, Zap } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [authenticatedUser, setAuthenticatedUser] = useState<any | null>(null);
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
        setAuthenticatedUser(res.user);
      } else {
        setErrorMsg(res.message || 'Error de autenticación.');
      }
    } catch (err: any) {
      setErrorMsg('Usuario o PIN incorrectos. Revisa tus datos.');
    } finally {
      setLoading(false);
    }
  };

  const selectMode = (path: string) => {
    router.push(path);
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
          {!authenticatedUser ? (
            <>
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
                    className="win95-button w-full py-2 text-xs font-bold font-mono bg-[#008000] text-white"
                  >
                    {loading ? 'AUTENTICANDO...' : 'INICIAR SESIÓN'}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <div className="space-y-4">
              <div className="win95-inset bg-white p-3 text-center space-y-1">
                <div className="font-bold text-sm font-mono text-[#008000]">¡AUTENTICACIÓN EXITOSA!</div>
                <div className="text-xs text-[#808080] font-mono">Selecciona el módulo de trading al que deseas ingresar:</div>
              </div>

              <div className="space-y-3">
                <button
                  onClick={() => selectMode('/')}
                  className="win95-button w-full py-3 px-4 text-left font-mono bg-[#000080] text-white flex items-center justify-between group hover:bg-[#0000a0]"
                >
                  <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-yellow-300" />
                    <div>
                      <div className="font-bold text-xs">TRADEMERC CRYPTO BOT</div>
                      <div className="text-[10px] text-slate-300">Trading Algorítmico Binance · 10 Indicadores + ML</div>
                    </div>
                  </div>
                  <span className="font-bold text-xs text-yellow-300">ENTRAR ➔</span>
                </button>

                <button
                  onClick={() => selectMode('/polymarket')}
                  className="win95-button w-full py-3 px-4 text-left font-mono bg-[#008080] text-white flex items-center justify-between group hover:bg-[#009090]"
                >
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-emerald-300" />
                    <div>
                      <div className="font-bold text-xs">TRADEMERC POLYMARKET BOT</div>
                      <div className="text-[10px] text-slate-200">Mercados de Predicción Descentralizada · Ventaja +EV</div>
                    </div>
                  </div>
                  <span className="font-bold text-xs text-emerald-300">ENTRAR ➔</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
