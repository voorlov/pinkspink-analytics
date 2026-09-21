# PageSpeed snapshot — 2026-09-21

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **60/100** | 24.1s ❌ | 2.9s ⚠ | 0.000 ✅ | 152ms ✅ | нет данных |
| intl homepage | desktop | **64/100** | 5.1s ❌ | 799ms ✅ | 0.000 ✅ | 201ms ⚠ | нет данных |
| jp homepage | mobile | **57/100** | 79.8s ❌ | 4.4s ❌ | 0.000 ✅ | 40ms ✅ | нет данных |
| jp homepage | desktop | **47/100** | 10.7s ❌ | 958ms ✅ | 0.077 ✅ | 416ms ⚠ | нет данных |
| intl catalog | mobile | **65/100** | 21.0s ❌ | 2.9s ⚠ | 0.002 ✅ | 58ms ✅ | нет данных |
| intl catalog | desktop | **74/100** | 1.2s ✅ | 802ms ✅ | 0.007 ✅ | 414ms ⚠ | нет данных |
| jp catalog | mobile | **60/100** | 41.9s ❌ | 4.3s ❌ | 0.002 ✅ | 74ms ✅ | нет данных |
| jp catalog | desktop | **49/100** | 3.6s ⚠ | 991ms ✅ | 0.010 ✅ | 735ms ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.