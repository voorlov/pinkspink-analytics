# PageSpeed snapshot — 2026-08-24

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **60/100** | 37.7s ❌ | 2.8s ⚠ | 0.000 ✅ | 84ms ✅ | нет данных |
| intl homepage | desktop | **53/100** | 5.3s ❌ | 766ms ✅ | 0.075 ✅ | 345ms ⚠ | нет данных |
| jp homepage | mobile | **56/100** | 85.7s ❌ | 4.8s ❌ | 0.000 ✅ | 98ms ✅ | нет данных |
| jp homepage | desktop | **38/100** | 11.4s ❌ | 1.1s ✅ | 0.075 ✅ | 731ms ❌ | нет данных |
| intl catalog | mobile | **60/100** | 7.1s ❌ | 3.7s ❌ | 0.000 ✅ | 88ms ✅ | нет данных |
| intl catalog | desktop | **76/100** | 971ms ✅ | 763ms ✅ | 0.009 ✅ | 383ms ⚠ | нет данных |
| jp catalog | mobile | **55/100** | 48.2s ❌ | 4.8s ❌ | 0.000 ✅ | 182ms ✅ | нет данных |
| jp catalog | desktop | **40/100** | 5.2s ❌ | 1.5s ✅ | 0.014 ✅ | 805ms ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.