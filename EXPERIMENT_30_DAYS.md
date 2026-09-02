# Experimento Paper De 30 Dias

## Alcance

- Modo exclusivo: `paper`.
- Duracion: 30 dias continuos desde `strategy_runs.started_at`.
- Scheduler: GitHub Actions cada 15 minutos.
- Configuracion y modelo congelados durante el experimento.
- Los modelos candidatos pueden entrenarse, pero no controlan ejecuciones.

## Configuracion Congelada

- Capital virtual: USD 100.
- Timeframe: 15 minutos.
- Riesgo por trade: 0,25%.
- Stop loss: 2%.
- Take profit: 4%.
- Fee por lado: 0,10%.
- Slippage por lado: 0,05%.
- Coste completo usado por estrategia, labels y paper: 0,30%.
- Maximo de posiciones abiertas: 2.

El snapshot completo, el modelo y el commit quedan almacenados en `strategy_runs`.

## Operacion

- `worker_cycles` registra inicio, fin, cobertura y errores de cada ciclo.
- Un ciclo parcial falla el workflow y no se contabiliza como exitoso.
- El health degrada un heartbeat con mas de 15 minutos.
- `.github/workflows/health-monitor.yml` verifica produccion dos veces por hora.
- Los logs tienen retencion automatica de 90 dias.
- Polymarket no forma parte del experimento.

## Consulta

- Panel: `/analytics`.
- API Flask: `/api/experiments/current/report`.
- API Next: `/api/experiments/current/report`.

El reporte muestra progreso, cobertura, funnel, PnL, fees, expectancy, profit factor,
drawdown y criterios de evaluabilidad.

## Criterios

- 30 dias completos.
- Cobertura diaria minima del 99%.
- Cobertura de ciclos exitosos minima del 99%.
- Al menos 100 trades cerrados.
- Sin posiciones abiertas al finalizar.
- Configuracion sin cambios.

No se debe cambiar la estrategia durante el periodo. Si no se alcanzan 100 trades,
el resultado sirve para validar operacion y diagnosticar el funnel, pero no para
afirmar rentabilidad estadistica ni habilitar dinero real.
