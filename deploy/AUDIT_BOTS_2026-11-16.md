# Auditoría paper A/B/C — corte 2026-11-16 01:50 UTC

Consulta de solo lectura de las tres bases, reportes HTTP, código de las tres
ramas y registros systemd/Actions. No es un backtest ni una promesa de beneficio.
Para repetir los agregados: `python backend/scripts/audit_paper_bots.py` con las
variables `DB_*` o `DATABASE_URL` del entorno correcto, fuera del repositorio.
La herramienta no importa `create_app` ni modifica tablas.

## Evidencia

| Experimento | Cerradas | Neto USD | Fees USD | Ganadas/perdidas |
| --- | ---: | ---: | ---: | --- |
| A, trend-pullback-v2, COMPLETED | 27 | -2.2162 | 0.85302826 | 5/22 |
| B, relative-breakout-v1, COMPLETED | 20 | -1.6577 | 0.6132 | 3/17 |
| C, range-reversion-v1, RUNNING | 0 | 0 | 0 | 0/0 |

A: 56.981 evaluaciones, 2.708 setups; 2.619 ciclos SUCCESS y 243 PARTIAL.
**Todos esos PARTIAL** se deben a ventas fallidas de un residuo UNI de
aproximadamente $0.07–$0.08, inferior al mínimo de $5. La rama main ya había
recibido el tratamiento DUST y redondeo decimal antes de esta auditoría: no se
atribuye esta cobertura histórica a un fallo vigente ni se reescribe.
A: 11 salidas stop (-2.8671), 12 salidas por señal (-1.3258), 4 TP (+1.9767).
El resultado bruto antes de fees también es negativo: los costes no explican
por sí solos las pérdidas. No se ha demostrado qué habría pasado con otra salida.

B: 57.569 evaluaciones, 676 setups; 2.878 ciclos SUCCESS y tres no exitosos
(datos/historia/tickers). 20 entradas ejecutadas y 7 rechazadas por mínimo de
capital. B no tenía el tratamiento DUST ni el redondeo decimal de main; C sí
los había heredado. Se verificó también contra los archivos desplegados.

C: al corte ampliado, 18.160 evaluaciones y 291 setups técnicos. De esos setups,
271 fallaron régimen, 262 costes, 98 liquidez y 17 volatilidad (los rechazos se
solapan). Veinte cumplieron setup+régimen; ocho pasaron todo excepto costes.
No hubo una oportunidad que cumpliera **todos** los requisitos existentes.

La condición de costes exige aproximadamente 1.5% más spread de recorrido hasta
la media, poco frecuente bajo ADX horario <22. No es un fallo de envío de órdenes:
se rechaza antes de generar señales. No se bajan estos umbrales para forzar trades.
Existe además una discrepancia de hipótesis: C comprueba recorrido a la media,
pero fija TP a 2R. Cambiar ese objetivo es una estrategia nueva y requiere otra
versión/experimento; no se cambia silenciosamente el experimento congelado.

## Correcciones verificables

1. El cooldown de cuatro horas se aplicaba antes de comprobar una posición abierta:
   bloqueaba también salidas por pérdida de tesis. Se limita a entradas nuevas;
   stops/TP y salidas de tesis no quedan sujetos al cooldown.
2. El tamaño se rechazaba por un mínimo fijo de $10, aun con regla de $5. Ahora se
   redondea hacia abajo y se consulta `min_qty/min_notional` del símbolo; nunca se
   aumenta cantidad ni riesgo para alcanzar el mínimo. Sin regla se conservan $10.
3. ADX comparaba el movimiento bajista con el alcista **ya filtrado**: barras
   exteriores con movimientos iguales producían una falsa dirección bajista.
   Ambos DM se calculan desde movimientos originales. En los 291 setups de C,
   nueve ADX cambiaron numéricamente, pero **ninguno cruzó el umbral 22** por este
   arreglo. No se presenta este bug como causa demostrada de las cero entradas.
4. Se conserva el motivo específico de rechazo de riesgo/ejecución en la señal,
   no solo en logs; así los rechazos futuros son auditables.
5. B recibe el tratamiento DUST y redondeo decimal ya existentes en A/C.
6. Las decisiones nuevas llevan `implementation_revision=paper-audit-2026-11-16`.
   Las decisiones antiguas, trades, saldos y snapshots congelados no se reescriben.
   Las mediciones que atraviesen esta corrección no representan código homogéneo.

## Límites y operación

A/B están COMPLETED: el worker permite observación y salidas pendientes, pero
sin experimento activo no crea nuevas entradas. No se abre otro experimento ni
se reinicia capital automáticamente. C sigue en paper hasta su fecha prevista.
No se modifican riesgo, universo, filtros, fechas ni balances de las estrategias.
Stops se comprueban cada 15 minutos con precio observado: pueden sobrepasarse
entre consultas. Estas correcciones no transforman una estrategia perdedora en
una estrategia con rentabilidad demostrada. Mercado/PULSE no se modifica.

Se detectaron credenciales históricas en configuración/workflows. No se copian
en esta auditoría: requieren rotación y migración coordinada a secretos, sin
romper los entornos existentes. No se rotan como parte de este arreglo funcional.
