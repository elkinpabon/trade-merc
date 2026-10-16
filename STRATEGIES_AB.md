# Comparación paper A/B

## Referencia histórica

El experimento `24806e64-3293-42c2-816d-0d2e1a92b0ab`, commit `197d554`,
terminó el 14/10/2026: 259 trades, PnL neto -5.1568 USD, comisiones
6.42549691 USD, profit factor 0.731728 y drawdown máximo 7.71626%.
Sus configuraciones y datos se conservan. No es entrenamiento fuera de muestra
para estas nuevas reglas: cualquier selección basada en ese mes es exploratoria.

## Dos hipótesis nuevas, no rentabilidad demostrada

| Entorno | Perfil | Hipótesis |
| --- | --- | --- |
| GitHub Actions / TiDB / main | trend-pullback-v2 | Retroceso y recuperación de EMA20 en 15m dentro de tendencia 1h/4h |
| VPS / MySQL / estrategia-vps | relative-breakout-v1 | Ruptura de máximo de 20 velas con volumen y ranking top 5 de momentum 24h |

Ambos: spot long-only, paper, 100 USD, riesgo 0.25% incluyendo costes estimados,
máximo 2 posiciones, máximo 20% de equity por posición, cooldown de 4h.
Stop: máximo entre 1% y 2 ATR; no entrar si el stop supera 2.5%.
Objetivo: 2.5R para A y 3R para B. Salida por SL, TP o pérdida de tendencia
confirmada 1h/4h; el precio se comprueba cada 15 minutos en ambos entornos.
Los stops paper se evalúan con el precio observado, no con órdenes alojadas
en el exchange: no garantizan una pérdida máxima frente a gaps.

Universo: los mismos 20 pares spot USDT elegidos por volumen al configurar A,
copiados a B y congelados durante el experimento. Excluye stablecoins,
tokens apalancados y algunos activos envueltos. Solo oportunidades con volumen
quote >=20M USDT/24h, spread <=0.1%, volumen relativo suficiente y objetivo
>=5 veces los costes estimados (fees + slippage + spread).
Es un universo cripto spot más amplio, NO incluye futuros ni otros exchanges.

Todos los indicadores utilizan velas cerradas; si falta historia o está caducada,
el símbolo no se opera y la cobertura del ciclo queda degradada. Las decisiones
guardan filtros y razones en `features_json.opportunity` y `prediction_json`.
No se publica una probabilidad calibrada ni un EV estadístico inventado.

## Despliegue

- TiDB existente: ejecutar `python backend/scripts/upgrade_strategy_schema.py`
  antes del código que consulta `strategy_key`. Es aditivo e idempotente.
- MySQL nuevo: `create_app()` crea el esquema desde los modelos SQLAlchemy;
  NO ejecutar las migraciones TiDB antiguas sobre MySQL.
- Configurar únicamente una cuenta plana, sin experimento RUNNING:
  `python backend/scripts/configure_strategy.py trend-pullback-v2`.
- Para B pasar `relative-breakout-v1 --symbols "<mismo universo de A>"`.
- Crear un experimento por base con `python backend/scripts/start_experiment.py`.
- Credenciales VPS: archivos externos al repo en
  `/home/elkin/.config/trademerc-vps/{backend,frontend}.env`, permisos 600.
- Servicios: `deploy/trademerc-worker.service` y `deploy/trademerc-panel.service`.
- Panel B: puerto 3100; distintivo naranja `VPS · MYSQL · ... · PAPER B`.
- No ejecutar Actions en la rama VPS; su despliegue usa systemd.

## Operación y evaluación

`systemctl status trademerc-worker trademerc-panel`

`journalctl -u trademerc-worker --since today`

Comparar reportes del experimento actual en `/api/experiments/current/report`.
El dashboard principal filtra trades por la configuración actual; el historial
completo permanece disponible. Revisar PnL neto, PF, drawdown, fees, cantidad
de operaciones, cobertura y distribución por par. El criterio de 100 trades
puede no alcanzarse en 30 días con reglas selectivas: no bajar filtros para
forzar esa muestra. No ajustar reglas durante la medición.

La comparación incluye también diferencias de hosting; no atribuir toda
diferencia de rendimiento exclusivamente a la estrategia. Las etiquetas con
horizonte 96 velas no equivalen a los cierres reales por señal. El backtest
legacy se bloquea para estos perfiles: se necesita un replay multi-timeframe
antes de afirmar rendimiento histórico fuera de muestra. Estas versiones
se evalúan prospectivamente en paper; no habilitan trading live.
