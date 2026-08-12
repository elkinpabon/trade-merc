import requests

base = 'https://trade-merc.vercel.app'
endpoints = [
    '/api/auth/verify',
    '/api/bot/status',
    '/api/bot/live-logs',
    '/api/dashboard/summary',
    '/api/market/scanner',
    '/api/market/ticker?symbol=BTC/USDT',
    '/api/trades?limit=50',
    '/api/logs?limit=100',
    '/api/analytics/overview',
    '/api/config',
    '/api/exchange/settings',
    '/api/signals',
    '/api/orders',
    '/api/fills',
    '/api/positions',
    '/api/health',
]

print("=== VERIFICANDO ENDPOINTS EN LA NUBE (VERCEL + TIDB CLOUD) ===")
all_ok = True
for ep in endpoints:
    url = base + ep
    r = requests.get(url, timeout=10)
    status = "200 OK" if r.status_code == 200 else f"ERROR {r.status_code}"
    if r.status_code != 200:
        all_ok = False
    print(f"  [{status}] {ep}")

print(f"\nRESULTADO DE ENDPOINTS: {'TODOS 100% OPERATIVOS (200 OK)' if all_ok else 'HUBO ALGUN FALLO'}")

# Check live logs endpoint
r_logs = requests.get(base + '/api/bot/live-logs', timeout=10)
if r_logs.ok:
    data = r_logs.json()
    logs = data.get('logs', [])
    print("\n=== MONITOREO DE LOGS EN TIEMPO REAL DESDE LA NUBE ===")
    print(f"Total logs disponibles en nube: {len(logs)}")
    if logs:
        latest = logs[0]
        print(f"Último registro guardado: [{latest.get('module')}] {latest.get('message')[:100]}...")
