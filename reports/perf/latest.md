# PageSpeed snapshot — 2026-10-05

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **62/100** | 36.3s ❌ | 2.8s ⚠ | 0.000 ✅ | 9ms ✅ | нет данных |
| intl homepage | desktop | **80/100** | 1.8s ✅ | 804ms ✅ | 0.077 ✅ | 175ms ✅ | нет данных |
| jp homepage | mobile | **56/100** | 104.7s ❌ | 5.3s ❌ | 0.000 ✅ | 78ms ✅ | нет данных |
| jp homepage | desktop | **56/100** | 15.0s ❌ | 1.1s ✅ | 0.072 ✅ | 275ms ⚠ | нет данных |
| intl catalog | mobile | **66/100** | 8.4s ❌ | 2.8s ⚠ | 0.002 ✅ | 17ms ✅ | нет данных |
| intl catalog | desktop | **85/100** | 1.2s ✅ | 803ms ✅ | 0.009 ✅ | 245ms ⚠ | нет данных |
| jp catalog | mobile | **59/100** | 59.1s ❌ | 5.2s ❌ | 0.002 ✅ | 0ms ✅ | нет данных |
| jp catalog | desktop | **36/100** | 5.4s ❌ | 1.1s ✅ | 0.004 ✅ | 3.4s ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.