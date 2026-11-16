# Mejora medible A/B y Mercado — 2026-11-16

## Objetivo y límites

Mejorar ejecución y controlar pérdidas sin inventar rentabilidad, elevar riesgo,
depositar dinero real ni borrar experimentos. C no se modifica en esta fase.
No se interpreta ausencia de operaciones como beneficio. No hay martingala ni
optimización de umbrales hasta encontrar un resultado histórico positivo.

## Plan ejecutado

1. **Medir:** consultar ledger Mercado y exportar con SELECT los experimentos
   completos A/B, sus decisiones ya registradas, reglas y velas de 15m.
2. **Corregir ejecución:** A/B refrescan bid/ask antes de enviar una orden. BUY al
   ask, SELL al bid, después slippage/fees; cotización máxima 45s, sin precios
   futuros/NaN/invertidos. Entradas con spread >0.10% o desvío >0.30% de la señal
   se rechazan. Salidas no se bloquean por spread alto ni por desvío de entrada.
   También se refresca el bid al comprobar stops de posiciones abiertas.
   Un rechazo no inicia cooldown: solo operaciones realmente EXECUTED lo hacen.
3. **Proteger Mercado:** tras al menos 20 cierres, una ventana de hasta 30 trades
   con neto negativo y pérdidas mayores a ganancias suspende compras nuevas.
   El análisis, las valoraciones y las salidas continúan. No es una prueba
   estadística de ventaja negativa, sino un corte conservador de exposición.
4. **Stop tras costes:** al activar el trailing existente a 1R, Mercado calcula
   el bid de equilibrio incluyendo fee de entrada, fee de salida y slippage de
   salida. Nunca baja un stop existente. Gaps/latencia todavía pueden producir
   pérdidas: no es un stop con ejecución garantizada.
5. **Probar una hipótesis:** overlay único `protected-v1` sobre las entradas
   originales A/B: régimen BTC 1h/4h positivo, desvío máximo 0.30%, trailing neto
   a 1R y límite de permanencia 24h. No se prueban cientos de parámetros.
6. **No promover lo que falla:** solo investigación y observación prospectiva;
   no se reinician A/B ni se crean nuevos saldos/experimentos automáticamente.
7. **Guardar evidencia futura:** A/B guardan intenciones SHADOW, benchmark,
   bid/ask con hora y regla configurada conocida en cada decisión. Nunca son
   órdenes ni fills. Mercado añade un journal idempotente de velas cerradas de
   los mercados realmente analizados; conserva `recorded_at`, no finge conocer
   cotizaciones antiguas. Se mantienen las decisiones también durante la pausa.

## Evidencia de Mercado antes del cambio

Ledger observado: 33 operaciones cerradas y una abierta (ASTERUSDT), equity
aproximado $46.94 frente a $50 iniciales. No es un problema de cero señales:
había 34 entradas y 40 rechazos. El límite diario y el DD máximo existentes no
detienen necesariamente una pérdida acumulada repartida entre varios días.
No se cierra artificialmente la posición abierta ni se devuelve cash al capital
inicial. La política original y la versión de señal se conservan; la revisión de
protección se registra aparte como `net-cost-and-loss-guard-v1`.

## Replay diagnóstico A/B

Código reproducible: `backend/scripts/export_replay_inputs.py` y
`backend/research/paper_replay.py`. Exportación sin arranque de app, migraciones
ni escritura en las bases. Datos crudos y reportes detallados quedan fuera del
repositorio, en el directorio temporal local autorizado.

- A: 56.981 decisiones, 59 entradas técnicamente elegibles, 57.620 velas.
- B: 57.569 decisiones, 38 entradas técnicamente elegibles, 57.620 velas.
- SHA256 A: `762797a2906c3c0e5ddd4c9450b36631f0ccade9d84cbcc5d11aea533bd57992`.
- SHA256 B: `cc42753e9f8887ae51f6bda3fbb567d8c1b8101c7826c822312ee04495cafbef`.
- Corte cronológico 70/30, purga de 24h antes del tramo final.
- Entrada en la primera apertura de 15m **posterior a la disponibilidad** de la
  decisión, no al cierre histórico de señal. STOP_FIRST si ambos niveles se
  cruzan en una vela; gaps al precio desfavorable de apertura. Trailing nuevo
  efectivo solo en la vela siguiente, sin fills retrospectivos favorables.
- Máximo dos posiciones, exposición 20% por posición, riesgo 0.25% incluyendo
  costes, mínimos y redondeo hacia abajo. Stress duplica fees y slippage.

| Bot / tramo | Baseline: cierres / neto USD | protected-v1: cierres / neto USD |
| --- | --- | --- |
| A / desarrollo | 30 / -2.460710 | 7 / -0.435417 |
| A / diagnóstico final | 4 / -0.958498 | 0 / 0 |
| B / desarrollo | 20 / -1.455484 | 4 / -0.455395 |
| B / diagnóstico final | 4 / -0.187917 | 0 / 0 |

**Resultado: ninguna candidata supera el gate.** Cero trades en el tramo final
evitaron exposición, no demostraron ganancia. No se activa el overlay como
estrategia ganadora. El replay no replica exactamente los fills anteriores.

Limitaciones deliberadamente bloqueantes: estos datos ya se inspeccionaron,
no hay libros históricos y las reglas son las configuradas actualmente, no
snapshots históricos verificados del exchange. Por eso el tramo final se llama
**diagnóstico**, no prueba fuera de muestra genuinamente desconocida.

Gate implementado: al menos 100 cierres del tramo final, neto positivo, PF>=1.2,
DD<=5%, neto positivo con costes duplicados, mejora frente a baseline, sin huecos
con posiciones abiertas, datos realmente no inspeccionados, books/reglas punto
en el tiempo y validación prospectiva. Las últimas condiciones **no se cumplen**;
no existe promoción automática ni una ruta de ejecución de la candidata.

## Verificación y operación

- Backend A/B: 57 pruebas unitarias/integración correctas con SQLite aislado.
- Mercado: 15 pruebas correctas, incluidos pausa sin bloquear salidas, trailing
  tras costes y journal sin duplicados/velas abiertas. Build web correcto.
- A/B continúan observación; sus experimentos previos permanecen COMPLETED.
- Mercado muestra el motivo de pausa explícitamente en el panel, sin confundirlo
  con una caída del servicio. Reactivar exige evidencia y una decisión explícita
  sobre una estrategia nueva, no limpiar contadores ni ocultar pérdidas.

### Comprobación en producción

- B, código `0571652`: ciclo del 16/11 a las 03:46 UTC, SUCCESS; evaluaciones
  nuevas contienen `protected-v1-shadow-2026-11-16`, modo SHADOW y permiso de
  órdenes false. Se ejecutaron también las 57 pruebas en la VPS contra SQLite.
- Mercado, código `dcabed6`: backup de código/build anterior, esquema de journal
  aditivo, 15 pruebas en VPS y reinicio únicamente de `pulse-market`.
- API real autenticada: ONLINE; protección activa, últimos 30 cierres
  -2.728103905445 USDT y PF 0.1734142991. Cash conservado en 38.964767128138 USDT;
  saldo inicial 50 y ASTER abierto, sin reinicializar cuenta. Equity varía con bid.
- Journal verificado: 2.970 velas de 30 símbolos poco después del despliegue.
- Revisión del panel autenticado en escritorio y móvil de 390px: aviso de pausa,
  navegación, búsqueda, drawer/Escape y sin overflow. API sin sesión devuelve 401.
- A: relevo del bloque anterior realizado con cuenta plana y sin ciclo en marcha;
  bloque Actions `43800263933` usa SHA `dcabed6` (código de ejecución `79a8345`).
  No se toca el workflow/worker de C ni se activa el overlay investigado.
