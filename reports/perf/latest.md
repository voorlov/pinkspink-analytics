# PageSpeed snapshot — 2026-05-01

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **46/100** | 8.7s ❌ | 3.4s ❌ | 0.000 ✅ | 615ms ❌ | нет данных |
| intl homepage | desktop | **89/100** | 1.6s ✅ | 485ms ✅ | 0.000 ✅ | 113ms ✅ | нет данных |
| jp homepage | mobile | **59/100** | 6.7s ❌ | 2.0s ⚠ | 0.000 ✅ | 396ms ⚠ | нет данных |
| jp homepage | desktop | **86/100** | 1.3s ✅ | 486ms ✅ | 0.000 ✅ | 177ms ✅ | нет данных |
| intl catalog | mobile | **43/100** | 6.4s ❌ | 2.0s ⚠ | 0.000 ✅ | 1.4s ❌ | нет данных |
| intl catalog | desktop | **43/100** | 1.2s ✅ | 485ms ✅ | 0.337 ❌ | 2.1s ❌ | нет данных |
| jp catalog | mobile | **43/100** | 7.6s ❌ | 2.0s ⚠ | 0.000 ✅ | 1.2s ❌ | нет данных |
| jp catalog | desktop | **43/100** | 1.4s ✅ | 485ms ✅ | 0.337 ❌ | 1.7s ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.