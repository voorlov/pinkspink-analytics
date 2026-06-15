# PageSpeed snapshot — 2026-06-15

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **63/100** | 15.0s ❌ | 3.2s ❌ | 0.000 ✅ | 12ms ✅ | нет данных |
| intl homepage | desktop | **95/100** | 1.1s ✅ | 528ms ✅ | 0.000 ✅ | 88ms ✅ | нет данных |
| jp homepage | mobile | **63/100** | 13.6s ❌ | 3.2s ❌ | 0.000 ✅ | 100ms ✅ | нет данных |
| jp homepage | desktop | **84/100** | 1.4s ✅ | 543ms ✅ | 0.000 ✅ | 216ms ⚠ | нет данных |
| intl catalog | mobile | **71/100** | 5.2s ❌ | 2.0s ⚠ | 0.000 ✅ | 109ms ✅ | нет данных |
| intl catalog | desktop | **58/100** | 981ms ✅ | 564ms ✅ | 0.361 ❌ | 467ms ⚠ | нет данных |
| jp catalog | mobile | **56/100** | 6.7s ❌ | 2.3s ⚠ | 0.000 ✅ | 478ms ⚠ | нет данных |
| jp catalog | desktop | **44/100** | 1.1s ✅ | 543ms ✅ | 0.526 ❌ | 838ms ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.