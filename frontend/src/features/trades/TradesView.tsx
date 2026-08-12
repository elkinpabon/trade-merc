'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { TradeData, PaperOrderData, SignalData } from '@/types';

export const TradesView: React.FC = () => {
  const [tab, setTab] = useState<'trades' | 'orders' | 'signals'>('trades');
  const [trades, setTrades] = useState<TradeData[]>([]);
  const [orders, setOrders] = useState<PaperOrderData[]>([]);
  const [signals, setSignals] = useState<SignalData[]>([]);

  const loadData = async () => {
    try {
      if (tab === 'trades') setTrades(await api.getTrades());
      if (tab === 'orders') setOrders(await api.getOrders());
      if (tab === 'signals') setSignals(await api.getSignals());
    } catch (err) {
      console.error('Error al cargar historial:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, [tab]);

  return (
    <div className="space-y-3 font-sans text-black">
      {/* Win95 Header & Tabs */}
      <div className="win95-panel p-3 space-y-2">
        <div className="win95-titlebar">
          <span>Historial de Operaciones Automáticas</span>
          <span>BingX Log</span>
        </div>

        <div className="grid grid-cols-3 gap-1">
          {[
            { id: 'trades', label: 'Operaciones Cerradas' },
            { id: 'orders', label: 'Órdenes de Compra/Venta' },
            { id: 'signals', label: 'Señales Detectadas' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id as any)}
              className={`win95-button py-1 text-xs font-mono font-bold ${
                tab === item.id ? 'win95-button-active' : ''
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table in Win95 Inset Box */}
      <div className="win95-panel p-3">
        <div className="win95-inset bg-white p-2 overflow-x-auto">
          {tab === 'trades' && (
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#c0c0c0] text-black uppercase border-b border-[#808080]">
                <tr>
                  <th className="p-2">Moneda</th>
                  <th className="p-2">Acción</th>
                  <th className="p-2">Precio Compra</th>
                  <th className="p-2">Precio Venta</th>
                  <th className="p-2">Cantidad</th>
                  <th className="p-2">Ganancia / Pérdida</th>
                  <th className="p-2">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e5e5e5]">
                {trades.length > 0 ? (
                  trades.map((t) => (
                    <tr key={t.id} className="hover:bg-[#000080] hover:text-white">
                      <td className="p-2 font-bold">{t.symbol}</td>
                      <td className="p-2 text-[#008000] font-bold">COMPRA/VENTA</td>
                      <td className="p-2">${t.entry_price.toFixed(2)}</td>
                      <td className="p-2">${t.exit_price.toFixed(2)}</td>
                      <td className="p-2">{t.quantity}</td>
                      <td className={`p-2 font-bold ${t.realized_pnl >= 0 ? 'text-[#008000]' : 'text-[#cc0000]'}`}>
                        {t.realized_pnl >= 0 ? '+' : ''}${t.realized_pnl.toFixed(2)} ({t.realized_pnl_pct.toFixed(2)}%)
                      </td>
                      <td className="p-2 opacity-75">{new Date(t.closed_at).toLocaleTimeString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-[#808080]">
                      No hay operaciones cerradas registradas aún.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}

          {tab === 'orders' && (
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#c0c0c0] text-black uppercase border-b border-[#808080]">
                <tr>
                  <th className="p-2">Moneda</th>
                  <th className="p-2">Tipo</th>
                  <th className="p-2">Cantidad</th>
                  <th className="p-2">Precio</th>
                  <th className="p-2">Estado</th>
                  <th className="p-2">Comisión</th>
                  <th className="p-2">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e5e5e5]">
                {orders.length > 0 ? (
                  orders.map((o) => (
                    <tr key={o.id} className="hover:bg-[#000080] hover:text-white">
                      <td className="p-2 font-bold">{o.symbol}</td>
                      <td className={`p-2 font-bold ${o.side === 'BUY' ? 'text-[#008000]' : 'text-[#cc0000]'}`}>
                        {o.side}
                      </td>
                      <td className="p-2">{o.quantity}</td>
                      <td className="p-2">${o.requested_price.toFixed(2)}</td>
                      <td className="p-2 font-bold">{o.status}</td>
                      <td className="p-2">${o.simulated_fee.toFixed(4)}</td>
                      <td className="p-2 opacity-75">{new Date(o.created_at).toLocaleTimeString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-[#808080]">
                      No hay órdenes registradas aún.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}

          {tab === 'signals' && (
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#c0c0c0] text-black uppercase border-b border-[#808080]">
                <tr>
                  <th className="p-2">Moneda</th>
                  <th className="p-2">Señal</th>
                  <th className="p-2">Precio Objetivo</th>
                  <th className="p-2">Estado</th>
                  <th className="p-2">Detalle</th>
                  <th className="p-2">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e5e5e5]">
                {signals.length > 0 ? (
                  signals.map((s) => (
                    <tr key={s.id} className="hover:bg-[#000080] hover:text-white">
                      <td className="p-2 font-bold">{s.symbol}</td>
                      <td className="p-2 font-bold text-[#008000]">{s.type}</td>
                      <td className="p-2">${s.price.toFixed(2)}</td>
                      <td className="p-2 font-bold">{s.status}</td>
                      <td className="p-2">{s.reason}</td>
                      <td className="p-2 opacity-75">{new Date(s.timestamp).toLocaleTimeString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-[#808080]">
                      No hay señales recientes.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
