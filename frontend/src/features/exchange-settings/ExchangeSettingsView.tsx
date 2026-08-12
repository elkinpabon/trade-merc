'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export const ExchangeSettingsView: React.FC = () => {
  const [exchange, setExchange] = useState('binance');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [testnet, setTestnet] = useState(true);
  const [hasCreds, setHasCreds] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    api.getExchangeSettings().then((res) => {
      if (res.credentials) {
        setHasCreds(res.credentials.has_api_key);
        setTestnet(res.credentials.testnet_flag);
      }
    }).catch(console.error);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatusMsg(null);
    try {
      await api.updateExchangeSettings({
        exchange,
        apiKey,
        apiSecret,
        testnet,
      });
      setHasCreds(true);
      setStatusMsg('Credenciales cifradas con AES guardadas correctamente.');
    } catch (err: any) {
      setStatusMsg(`Error al guardar: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testExchangeConnection({
        exchange,
        apiKey,
        apiSecret,
        testnet,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({ error: err.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-3 font-sans text-black">
      <div className="win95-panel p-3 space-y-3">
        <div className="win95-titlebar">
          <span>Ajustes de Seguridad y Conexión (Profile / Settings)</span>
          <span>TRADEMERC Security</span>
        </div>

        {statusMsg && (
          <div className="win95-inset bg-white p-2 text-xs font-mono text-[#008000] font-bold">
            {statusMsg}
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-3">
          <div className="space-y-1">
            <label className="text-xs font-bold font-mono">Exchange Cripto:</label>
            <select
              value={exchange}
              onChange={(e) => setExchange(e.target.value)}
              className="w-full win95-inset bg-white p-2 text-xs font-mono outline-none"
            >
              <option value="binance">Binance (Oficial)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold font-mono">API Key (Llave Pública):</label>
            <input
              type="password"
              placeholder={hasCreds ? '••••••••••••••••••••••••' : 'Pega tu API Key de Binance'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full win95-inset bg-white p-2 text-xs font-mono outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold font-mono">API Secret (Llave Secreta):</label>
            <input
              type="password"
              placeholder={hasCreds ? '••••••••••••••••••••••••' : 'Pega tu API Secret de Binance'}
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              className="w-full win95-inset bg-white p-2 text-xs font-mono outline-none"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="win95-button flex-1 py-2 text-xs font-mono font-bold bg-[#000080] text-white"
            >
              {saving ? 'GUARDANDO...' : 'GUARDAR CREDENCIALES'}
            </button>
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="win95-button px-4 py-2 text-xs font-mono font-bold"
            >
              {testing ? 'PROBANDO...' : 'PROBAR CONEXIÓN'}
            </button>
          </div>
        </form>

        {testResult && (
          <div className="win95-inset bg-white p-3 font-mono text-xs overflow-x-auto">
            <pre className="text-[11px]">{JSON.stringify(testResult, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
};
