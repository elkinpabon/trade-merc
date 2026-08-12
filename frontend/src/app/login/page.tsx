'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { Lock, User, KeyRound, TrendingUp, Zap, ArrowRight } from 'lucide-react';
import { WorkspaceLoader } from '@/components/common/WorkspaceLoader';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [authenticatedUser, setAuthenticatedUser] = useState<any | null>(null);
  const [loadingWorkspace, setLoadingWorkspace] = useState<{ path: string; name: string; desc: string } | null>(null);

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

  return (
    <>
      {loadingWorkspace && (
        <WorkspaceLoader
          targetPath={loadingWorkspace.path}
          targetName={loadingWorkspace.name}
          targetDesc={loadingWorkspace.desc}
        />
      )}

      <div className="min-h-screen bg-[#008080] flex items-center justify-center p-4 font-sans text-black">
        <div className="win95-window w-full max-w-lg p-2">
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
                      className="win95-button w-full py-2 text-xs font-bold font-mono bg-[#008000] text-white hover:bg-[#009900]"
                    >
                      {loading ? 'AUTENTICANDO...' : 'INICIAR SESIÓN'}
                    </button>
                  </div>
                </form>
              </>
            ) : (
              <div className="space-y-4">
                <div className="win95-inset bg-white p-3 text-center space-y-1">
                  <div className="font-bold text-sm font-mono text-[#008000]">AUTENTICACIÓN EXITOSA</div>
                  <div className="text-xs text-[#808080] font-mono">Selecciona el módulo al que deseas ingresar:</div>
                </div>

                {/* Side-by-side Square Buttons Container */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Crypto Bot Square Button */}
                  <button
                    onClick={() => setLoadingWorkspace({ path: '/', name: 'TRADEMERC CRYPTO BOT', desc: 'Trading Algorítmico Binance · 10 Indicadores + ML' })}
                    className="win95-button aspect-square p-4 font-mono bg-[#000080] text-white flex flex-col items-center justify-between text-center group cursor-pointer hover:bg-[#0000a0] transition-all border-2 border-white/20"
                  >
                    <div className="w-12 h-12 rounded-full bg-yellow-400/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                      <Zap className="h-7 w-7 text-yellow-400" />
                    </div>

                    <div className="space-y-1">
                      <div className="font-bold text-sm tracking-wide">TRADEMERC CRYPTO</div>
                      <div className="text-[10px] text-blue-200">Trading Algorítmico Cripto Spot</div>
                    </div>

                    <div className="w-full py-1 text-[11px] font-bold bg-white text-[#000080] win95-button group-hover:bg-yellow-400 group-hover:text-black">
                      INGRESAR
                    </div>
                  </button>

                  {/* Polymarket Bot Square Button */}
                  <button
                    onClick={() => setLoadingWorkspace({ path: '/polymarket', name: 'POLYMARKET BOT', desc: 'Mercados de Predicción · Algoritmo +EV & Criterio de Kelly' })}
                    className="win95-button aspect-square p-4 font-mono bg-[#008080] text-white flex flex-col items-center justify-between text-center group cursor-pointer hover:bg-[#00a0a0] transition-all border-2 border-white/20"
                  >
                    <div className="w-12 h-12 rounded-full bg-emerald-400/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                      <TrendingUp className="h-7 w-7 text-emerald-300" />
                    </div>

                    <div className="space-y-1">
                      <div className="font-bold text-sm tracking-wide">POLYMARKET BOT</div>
                      <div className="text-[10px] text-teal-200">Predicción Cuantitativa CLOB</div>
                    </div>

                    <div className="w-full py-1 text-[11px] font-bold bg-white text-[#008080] win95-button group-hover:bg-emerald-300 group-hover:text-black">
                      INGRESAR
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="win95-panel p-2 flex items-center justify-between text-[11px] font-mono text-black border-t border-[#808080]">
            <div>TRADEMERC v1.0</div>
            <div className="shrink-0 text-[10px] font-bold text-[#008000]">SECURE</div>
          </div>
        </div>
      </div>
    </>
  );
}
