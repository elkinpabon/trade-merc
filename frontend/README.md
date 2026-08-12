# TRADEMERC - Interfaz de Usuario Next.js & Serverless API

La interfaz de TRADEMERC está desarrollada con **Next.js 14 (App Router)**, **TypeScript** y **Tailwind CSS**, con un diseño táctico retro estilo Windows 95.

---

## 🚀 Características Principales

1. **Aislamiento Total de Módulos**:
   - Entorno **Crypto Trading Bot** (`/` y `/market`): Sin elementos de Polymarket.
   - Entorno **Polymarket Prediction Bot** (`/polymarket`): Sin elementos de Cripto.
2. **Pantalla de Carga Win95 (`WorkspaceLoader`)**:
   - Barra de progreso animada (0% a 100%) con logs de estado para transiciones fluidas entre módulos.
3. **Selección Dual Post-Login**:
   - Botones de acceso cuadrados ubicados uno al lado del otro con iconografía SVG limpia sin emojis.
4. **Despliegue Serverless en Vercel**:
   - Múltiples API Route Handlers integrados para responder a peticiones globales sin servidores dedicados.

---

## 💻 Comandos de Desarrollo

```bash
cd frontend
npm install
npm run dev     # Servidor de desarrollo en http://localhost:3000
npm run build   # Compilación de producción Next.js
```
