import { NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';
import { serviceUnavailable } from '@/lib/server-response';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getDbPool();
    const [[configRows], [settingsRows]]: any = await Promise.all([
      pool.query('SELECT exchange_id, mode FROM bot_configs ORDER BY id DESC LIMIT 1'),
      pool.query('SELECT exchange_id, mode, testnet, rate_limit_ms, updated_at FROM exchange_settings ORDER BY id LIMIT 1'),
    ]);
    const config = configRows?.[0] || null;
    const settings = settingsRows?.[0] || null;
    const exchange = settings?.exchange_id || config?.exchange_id || null;
    const [credentialRows]: any = exchange ? await pool.query(`SELECT exchange_name, testnet_flag, is_active, updated_at,
        api_key_encrypted IS NOT NULL AS has_api_key,
        api_secret_encrypted IS NOT NULL AS has_api_secret
        FROM exchange_credentials WHERE exchange_name = ? ORDER BY updated_at DESC LIMIT 1`, [exchange]) : [[]];
    const credentials = credentialRows?.[0] || null;

    return NextResponse.json({
      exchange,
      mode: settings?.mode || config?.mode || null,
      settings: settings ? {
        ...settings,
        testnet: Boolean(settings.testnet),
      } : null,
      credentials: credentials ? {
        exchange_name: credentials.exchange_name,
        has_api_key: Boolean(credentials.has_api_key),
        has_api_secret: Boolean(credentials.has_api_secret),
        testnet_flag: Boolean(credentials.testnet_flag),
        is_active: Boolean(credentials.is_active),
        updated_at: credentials.updated_at,
      } : null,
    }, { status: 200 });
  } catch (error) {
    return serviceUnavailable('Exchange settings', error);
  }
}

export async function PUT() {
  return NextResponse.json({
    success: false,
    error: 'El guardado seguro de credenciales no está implementado en este frontend. Use el servicio backend de credenciales.',
  }, { status: 501 });
}
