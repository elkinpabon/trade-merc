'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export const ExchangeSettingsView: React.FC = () => {
  const [exchange, setExchange] = useState('binance');
  const [testnet, setTestnet] = useState(true);
  const [hasCreds, setHasCreds] = useState(false);

  useEffect(() => {
    api.getExchangeSettings().then((res) => {
      if (res.exchange) setExchange(res.exchange);
      if (res.credentials) {
        setHasCreds(res.credentials.has_api_key);
        setTestnet(res.credentials.testnet_flag);
      } else if (res.settings) {
        setTestnet(res.settings.testnet);
      }
    }).catch(console.error);
  }, []);

  return (
    <div className="max-w-2xl mx-auto space-y-3 font-sans text-black">
      <div className="win95-panel p-3 space-y-3">
        <div className="win95-titlebar">
          <span>Ajustes de Seguridad y Conexión (Profile / Settings)</span>
          <span>TRADEMERC Security</span>
        </div>

        <div className="win95-inset bg-white p-3 text-xs font-mono space-y-2">
          <p>La gestión de credenciales está deshabilitada en este panel.</p>
          <p>Exchange: <strong>{exchange}</strong></p>
          <p>Entorno: <strong>{testnet ? 'testnet' : 'producción'}</strong></p>
          <p>Credenciales configuradas: <strong>{hasCreds ? 'sí' : 'no'}</strong></p>
        </div>

        <div className="space-y-3 opacity-60" aria-disabled="true">
          <div className="space-y-1">
            <label className="text-xs font-bold font-mono">Exchange Cripto:</label>
            <select
              value={exchange}
              disabled
              className="w-full win95-inset bg-white p-2 text-xs font-mono outline-none"
            >
              <option value="binance">Binance (Oficial)</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};
