# PageSpeed snapshot — 2026-05-11

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **63/100** | 5.0s ❌ | 2.2s ⚠ | 0.000 ✅ | 414ms ⚠ | нет данных |
| intl homepage | desktop | **82/100** | 1.3s ✅ | 485ms ✅ | 0.000 ✅ | 278ms ⚠ | нет данных |
| jp homepage | mobile | **67/100** | 6.4s ❌ | 2.1s ⚠ | 0.000 ✅ | 217ms ⚠ | нет данных |
| jp homepage | desktop | **89/100** | 1.3s ✅ | 485ms ✅ | 0.000 ✅ | 165ms ✅ | нет данных |
| intl catalog | mobile | **70/100** | 5.6s ❌ | 2.1s ⚠ | 0.000 ✅ | 61ms ✅ | нет данных |
| intl catalog | desktop | **45/100** | 1.5s ✅ | 490ms ✅ | 0.337 ❌ | 846ms ❌ | нет данных |
| jp catalog | mobile | **40/100** | 7.7s ❌ | 2.0s ⚠ | 0.000 ✅ | 1.6s ❌ | нет данных |
| jp catalog | desktop | **38/100** | 1.9s ✅ | 489ms ✅ | 0.337 ❌ | 1.9s ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.