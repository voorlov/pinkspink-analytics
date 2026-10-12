# PageSpeed snapshot — 2026-10-12

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **56/100** | 36.6s ❌ | 3.0s ❌ | 0.000 ✅ | 262ms ⚠ | нет данных |
| intl homepage | desktop | **49/100** | 5.2s ❌ | 813ms ✅ | 0.076 ✅ | 443ms ⚠ | нет данных |
| jp homepage | mobile | **55/100** | 80.2s ❌ | 4.4s ❌ | 0.000 ✅ | 165ms ✅ | нет данных |
| jp homepage | desktop | **34/100** | 10.6s ❌ | 971ms ✅ | 0.084 ✅ | 1.2s ❌ | нет данных |
| intl catalog | mobile | **57/100** | 19.0s ❌ | 3.0s ⚠ | 0.002 ✅ | 340ms ⚠ | нет данных |
| intl catalog | desktop | **76/100** | 1.2s ✅ | 811ms ✅ | 0.009 ✅ | 379ms ⚠ | нет данных |
| jp catalog | mobile | **58/100** | 41.1s ❌ | 4.3s ❌ | 0.002 ✅ | 198ms ✅ | нет данных |
| jp catalog | desktop | **50/100** | 3.7s ⚠ | 971ms ✅ | 0.010 ✅ | 664ms ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.