# TRADEMERC — Mercado

Segundo producto de TRADEMERC, ubicado en `pulse/` dentro del mismo repositorio.
La carpeta, base y servicio conservan el identificador técnico `pulse` para
preservar el despliegue y su historial. La marca visible es TRADEMERC.

Interfaz: material translúcido claro, controles de vidrio y tipografía del
sistema. Safari/macOS/iOS usan San Francisco si está disponible; Windows usa
Segoe UI. No se redistribuyen fuentes propietarias de Apple ni se descargan
fuentes desde Google. Guía UI: `.opencode/skills/trademerc-liquid-ui/SKILL.md`.

Aplicación autónoma de investigación **paper-only**. Ninguna ruta permite órdenes
reales, depósitos ni retiros. No importa modelos, claves ni bases de TRADEMERC.
Mismo repositorio, carpeta, entorno y base de datos independientes.

## Stack

- Python 3.12, FastAPI, SQLAlchemy, MySQL 8.
- React 18, Vite, Recharts y Lucide; interfaz propia responsive.
- Un proceso Uvicorn, dos hilos: cotizaciones cada ~15s y escáner cada ~60s.
- Binance REST público con conexiones compartidas y backoff 418/429.
  **Esta versión NO implementa WebSocket**. No es alta frecuencia.

## Hipótesis congelada

`impulse-consolidation-v1`: 6 velas de impulso, 3 de consolidación, ruptura en
la última vela cerrada de 5m. Tendencia EMA20/50, volumen >=1.5x y fracción
compradora >=55%. Stop de estructura / 1.5 ATR, mínimo 0.8%, máximo 3%.
Objetivo 2R, trailing a partir de 1R, salida temporal 90m. No hay prueba de
rentabilidad ni backtest fuera de muestra de esta combinación de reglas.

Descubre pares USDT spot activos; excluye stablecoins conocidas y tokens
apalancados. Esto no certifica la naturaleza de todos los tokens listados.
Prefiltro de volumen >=10M USDT/24h y spread <=0.12%. Los 40 candidatos con mayor
movimiento absoluto 24h pasan a velas; en ejecución se priorizan setups válidos,
score de filtros y volumen relativo. El score NO es probabilidad.

Capital: $50 paper, una posición, tope 30% del equity, objetivo de riesgo 0.5%
incluyendo costes estimados. Fees 0.1% por lado, slippage 0.05% sobre ask/bid.
Entradas bloqueadas con pérdida diaria >=3% o drawdown >=10%; salidas continúan.
Nunca aumentar tamaño para alcanzar mínimos. Dust se conserva abierto y valorado.
El PnL de un cierre contiene ambas comisiones; la cantidad se guarda en DECIMAL.
Los $50 son saldo simulado, no una cuenta conectada a Binance.

## Límites de la simulación

Cotizaciones observadas, no fills reales; no reproduce colas, fills parciales,
comisiones en BNB/base, todos los filtros por cuenta ni impacto extremo. Los stops
se comprueban al observar precios, no en el exchange; gaps pueden exceder riesgo.
BTC es una referencia fraccional con costes modelados, no una ejecución real.
No seleccionar retrospectivamente solo monedas supervivientes para backtesting.
Snapshots del gráfico: últimos 10.000, agrupados cada 5m. Historial SQL completo
conservado. El panel muestra últimas 100 decisiones y operaciones.

## Desarrollo

```
python -m venv .venv
# activar .venv y pip install -r requirements.txt
python -m unittest discover -s tests -v
# PULSE_DATABASE_URL=mysql+pymysql://.../pulse_market
cd web
npm ci
npm run build
cd ..
python -m uvicorn pulse.api:app --host 127.0.0.1 --port 3400 --workers 1
```

No usar múltiples workers Uvicorn: cada instancia inicia el supervisor. systemd
gestiona un único proceso. Las transacciones bloquean la cuenta para movimientos.

## API de solo lectura

- `/api/overview`: cuenta, curvas, estado y configuración real.
- `/api/market`: universo de cotizaciones.
- `/api/opportunities`: último barrido, filtros y errores.
- `/api/activity`: diario de decisiones y trades.
- `/api/health`: salud de monitor y scanner con control de antigüedad.

Sin panel de administración público; para pausar: `sudo systemctl stop pulse-market`.
Al detener se detiene también la simulación de salidas. La cuenta persiste al
reiniciar. Un experimento nuevo requiere otra base, no borrar la anterior.

## Despliegue

Base MySQL exclusiva `pulse_market`, usuario local de esa base; variables fuera
del repositorio en `/home/elkin/.config/pulse-market/service.env` (modo 600).
Servicio `deploy/pulse-market.service`, puerto 3400. A/B/C no se detienen.
Una URL HTTP por IP puede servir para este panel paper de solo lectura; para
autenticación o futuras acciones administrativas utilizar dominio y HTTPS.
