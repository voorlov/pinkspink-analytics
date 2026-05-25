# PageSpeed snapshot — 2026-05-25

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **69/100** | 5.4s ❌ | 2.2s ⚠ | 0.000 ✅ | 236ms ⚠ | нет данных |
| intl homepage | desktop | **94/100** | 1.1s ✅ | 503ms ✅ | 0.000 ✅ | 118ms ✅ | нет данных |
| jp homepage | mobile | **62/100** | 6.4s ❌ | 2.7s ⚠ | 0.000 ✅ | 248ms ⚠ | нет данных |
| jp homepage | desktop | **87/100** | 1.2s ✅ | 543ms ✅ | 0.000 ✅ | 191ms ✅ | нет данных |
| intl catalog | mobile | **42/100** | 17.0s ❌ | 2.7s ⚠ | 0.000 ✅ | 1.0s ❌ | нет данных |
| intl catalog | desktop | **55/100** | 1.3s ✅ | 502ms ✅ | 0.337 ❌ | 488ms ⚠ | нет данных |
| jp catalog | mobile | **57/100** | 7.4s ❌ | 2.7s ⚠ | 0.000 ✅ | 401ms ⚠ | нет данных |
| jp catalog | desktop | **60/100** | 1.4s ✅ | 542ms ✅ | 0.385 ❌ | 336ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.