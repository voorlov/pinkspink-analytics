# PageSpeed snapshot — 2026-05-18

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **67/100** | 5.2s ❌ | 2.2s ⚠ | 0.000 ✅ | 288ms ⚠ | нет данных |
| intl homepage | desktop | **92/100** | 1.5s ✅ | 485ms ✅ | 0.000 ✅ | 79ms ✅ | нет данных |
| jp homepage | mobile | **60/100** | 14.8s ❌ | 3.3s ❌ | 0.000 ✅ | 189ms ✅ | нет данных |
| jp homepage | desktop | **91/100** | 1.3s ✅ | 612ms ✅ | 0.000 ✅ | 130ms ✅ | нет данных |
| intl catalog | mobile | **57/100** | 6.0s ❌ | 2.2s ⚠ | 0.000 ✅ | 492ms ⚠ | нет данных |
| intl catalog | desktop | **47/100** | 1.2s ✅ | 503ms ✅ | 0.337 ❌ | 942ms ❌ | нет данных |
| jp catalog | mobile | **42/100** | 7.5s ❌ | 2.1s ⚠ | 0.000 ✅ | 1.3s ❌ | нет данных |
| jp catalog | desktop | **46/100** | 1.4s ✅ | 615ms ✅ | 0.337 ❌ | 810ms ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.