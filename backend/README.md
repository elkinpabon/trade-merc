# TRADEMERC - Servidor Backend & Motor de Trading ML

El servidor backend de TRADEMERC está desarrollado en Python (Flask, SQLAlchemy y PyMySQL) y proporciona el motor de cálculo cuantitativo para el análisis de mercados cripto y predicciones.

---

## 🛠️ Estructura del Backend

```
backend/
├── app/
│   ├── models/           # Modelos de base de datos SQLAlchemy
│   ├── routes/           # Blueprints y endpoints API REST
│   ├── services/         # Servicios de dominio y motores de cálculo
│   │   ├── indicator_service.py   # 10 Indicadores técnicos (EMA, RSI, MACD, BB, ATR, ADX, StochRSI, OBV, VWAP)
│   │   ├── strategy_service.py    # Motor de predicción ML (Regresión Lineal OLS + Patrones de Velas + Divergencias)
│   │   ├── risk_service.py        # Gestión de riesgo (Stop Loss 2%, Take Profit 4%)
│   │   └── portfolio_service.py   # Valoración de portafolio y PnL
│   └── utils/            # Funciones auxiliares y encriptación Fernet AES
├── worker/
│   └── bot_runner.py     # Bucle ejecutor autónomo del bot
└── run.py                # Punto de entrada principal del servidor Flask
```

---

## ⚙️ Ejecución del Servidor Local

```bash
cd backend
pip install -r requirements.txt
python run.py
```
*El servidor Flask iniciará en `http://localhost:5000` y activará el hilo ejecutor del bot en segundo plano.*
