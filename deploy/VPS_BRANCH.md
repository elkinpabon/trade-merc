# Rama estrategia-vps

Esta rama exige DATABASE_URL explícita para el backend y DB_HOST, DB_NAME,
DB_USER, DB_PASSWORD para el panel. No permite fallback de conexión a TiDB.
El distintivo naranja VPS/PAPER B está fijado en el build de Next.js.
El perfil operativo es relative-breakout-v1, almacenado en MySQL local.
Los workflows de trading solo se ejecutan en main; aquí se utiliza systemd.

Para incorporar correcciones comunes, revisar y fusionar desde main conservando
estas diferencias de conexión y de build. No intercambiar archivos .env entre
los entornos.
