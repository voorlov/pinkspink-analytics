# PageSpeed snapshot — 2026-08-17

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **55/100** | 35.6s ❌ | 3.0s ❌ | 0.000 ✅ | 300ms ⚠ | нет данных |
| intl homepage | desktop | **66/100** | 5.2s ❌ | 743ms ✅ | 0.073 ✅ | 105ms ✅ | нет данных |
| jp homepage | mobile | **51/100** | 90.9s ❌ | 7.2s ❌ | 0.000 ✅ | 221ms ⚠ | нет данных |
| jp homepage | desktop | **37/100** | 11.5s ❌ | 1.1s ✅ | 0.077 ✅ | 845ms ❌ | нет данных |
| intl catalog | mobile | **60/100** | 23.4s ❌ | 3.0s ❌ | 0.002 ✅ | 184ms ✅ | нет данных |
| intl catalog | desktop | **77/100** | 1.0s ✅ | 769ms ✅ | 0.004 ✅ | 367ms ⚠ | нет данных |
| jp catalog | mobile | **54/100** | 48.3s ❌ | 7.3s ❌ | 0.000 ✅ | 207ms ⚠ | нет данных |
| jp catalog | desktop | **52/100** | 5.1s ❌ | 1.5s ✅ | 0.013 ✅ | 370ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.