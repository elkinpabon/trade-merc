---
name: trademerc-liquid-ui
description: Use ONLY when designing or reviewing the independent TRADEMERC market interface in pulse/web. Applies its Apple-inspired system typography, liquid glass materials, accessibility and concise Spanish product vocabulary.
---

# TRADEMERC Liquid UI

Project-specific design skill, authored for this product. Not an Apple asset or
an upstream Superpowers plugin. No external scripts or dependencies.

## Direction

- Financial workspace, not a marketing landing page. Brand: TRADEMERC.
- Product descriptor: Mercado. Keep technical pulse identifiers internal.
- Use system typography: -apple-system, BlinkMacSystemFont, 'SF Pro Text',
  'SF Pro Display', 'Segoe UI', sans-serif. San Francisco is used when locally
  available on Apple platforms. Never download or redistribute proprietary fonts.
- Light botanical canvas (#f1f5f0), ink (#1b2c22), secondary (#607168), tonal
  sage/forest greens (#729d80, #397454), translucent white panels. Financial
  data must remain legible.
- Use the original `frontend/public/favicon.ico`, copied to
  `pulse/web/public/trademerc.ico`, as the TRADEMERC mark in login and shell;
  preserve its aspect ratio and clear space. Do not substitute a generic activity icon.
- Floating translucent sidebar, large rounded material surfaces and compact
  pill controls. Use backdrop-filter with a solid fallback.
- Glass conveys hierarchy. Avoid neon, ornamental radar graphics, uppercase
  eyebrow labels, promotional slogans and decorative gradients inside text.

## Content

Use functional Spanish headings: Resumen, Mercado, Cartera, Actividad, Estrategia.
No 'Encuentra el movimiento', 'Sin IA' selling points or generic motivational copy.
Keep the Paper/simulation label, risk rules and data freshness truthful.
Keep empty, stale and error states distinct. Never invent financial data.

## Verification

- Review real desktop and mobile screenshots before completion.
- Test navigation, search, opportunity details and empty/error states.
- Visible keyboard focus, Escape closes modal, reduced motion support.
- No document-level horizontal overflow at 390px; tables may scroll internally.
- Do not modify execution strategy, balances or existing bots for UI tasks.
