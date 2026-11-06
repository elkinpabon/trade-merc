# Bot C: reversión en rango (paper)

Hipótesis experimental, no garantiza ganancias. Adx horario <22, régimen 4h
estable, caída previa bajo banda inferior y recuperación en 15m, RSI recuperando,
liquidez y costes mínimos. Stop ATR y objetivo 2R; salida por ruptura del
régimen. Velas cerradas, $100 paper, máximo dos posiciones, riesgo 0.25%.
Backtest legacy está bloqueado: aún falta replay multitemporal fuera de muestra.

Instalación separada: `/home/elkin/trademerc-vps-c`; base exclusiva MySQL;
`WORKER_LOCK_NAME=trademerc:bot-worker-c` para evitar colisiones con B.
Servicios `trademerc-worker-c` y `trademerc-panel-c`; panel puerto 3200.
No ejecutar la rama C en GitHub Actions, que está restringido a main.
