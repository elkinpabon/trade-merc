# Pruebas paper exploratorias A/B

Autorización: el operador solicitó implementar e iniciar nuevas pruebas paper usando
el historial de la base de datos. No se autoriza dinero real ni se acredita rentabilidad.
C y Mercado no cambian; Mercado conserva su protección por pérdidas.

## Hipótesis congeladas

- A: `intraday-reclaim-paper-v1`, recuperación intradía, máximo 360 minutos.
- B: `intraday-breakout-paper-v1`, ruptura corta, máximo 480 minutos.
- $100 virtuales nuevos por cuenta, riesgo por entrada 0,25%, dos posiciones,
  exposición máxima 20% por posición, ocho entradas diarias, cooldown 60 minutos
  después de salidas, pérdida diaria 1,5%, drawdown 5%.
- Comisión 0,10% y slippage 0,05% por lado; spread máximo 0,10% y desviación
  ejecutable máxima 0,30%. Stop neto de costes tras 1R, objetivo 2R.
- Los límites de pérdida bloquean entradas, no salidas. No garantizan un suelo
  exacto de pérdidas: gaps, costes y cadencia de 15 minutos pueden excederlos.
- Duración prevista 30 días. Registrar cobertura, órdenes, costes y resultados;
  no promover a real por tener más operaciones ni por superar 100 cierres.

## Diagnóstico histórico (no validación fuera de muestra)

| Cuenta | Decisiones | Setups anteriores → nuevos | Cierres desarrollo | Neto desarrollo | Cierres tramo final | Neto final | Neto final costes ×2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 56.981 | 59 → 542 | 74 | −4,685355 | 21 | −1,129521 | −2,153013 |
| B | 57.569 | 38 → 223 | 43 | −5,058293 | 9 | −0,526537 | −0,916786 |

Son resultados negativos sobre datos ya inspeccionados. Aumentar actividad no
demuestra ventaja económica. Se conservan como hipótesis exploratorias paper.
No hay libros históricos reales; se aproximan fills al siguiente open de 15m y
se usan reglas actuales del exchange. El warmup EMA puede diferir de la ventana
live. La división 70/30 y embargo de un día no hacen que estos datos sean inéditos.

Fuentes completadas: A `1e4622da-67e6-4536-ad31-f3ba2d7296d8`,
B `48453a75-cd97-4022-b20d-2e2e27f1b1f8`.
SHA256 datasets: A `e41378f1583fee0cd324734be9592014b1bf8bded1a06cb97033ac6e05abd8e0`;
B `97c1540ae6f0800202edfe58d03a852fbd2298e55d1a104115cbd2cd1ab57f54`.

## Inicio y operación

`backend/scripts/start_activity_pilot.py` exige perfil, `--trial-key`,
`--expected-previous-run` y `--acknowledge-unvalidated-paper`. Requiere entorno DB
explícito, predecessor completado, cuenta sin posiciones, y lock del worker.
La clave hace idempotente el inicio; nuevas configuraciones, bot y experimento
preservan el histórico. Las mutaciones de cuenta y snapshot son atómicas; un
registro candidato de modelo sin uso puede permanecer tras un fallo.

Desplegar código compatible antes de cambiar perfiles, retirar bloques antiguos
de Actions A entre ciclos y verificar SHA. B carga código en un hijo nuevo cada
slot. Verificar experimento RUNNING, política congelada y primer ciclo SUCCESS.
Los perfiles son reglas deterministas; no probabilidades calibradas ni ML entrenado.
