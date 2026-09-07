# PageSpeed snapshot — 2026-09-07

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **61/100** | 35.8s ❌ | 2.9s ⚠ | 0.000 ✅ | 15ms ✅ | нет данных |
| intl homepage | desktop | **72/100** | 2.1s ✅ | 808ms ✅ | 0.076 ✅ | 252ms ⚠ | нет данных |
| jp homepage | mobile | **55/100** | 81.9s ❌ | 4.4s ❌ | 0.000 ✅ | 158ms ✅ | нет данных |
| jp homepage | desktop | **36/100** | 10.5s ❌ | 980ms ✅ | 0.077 ✅ | 969ms ❌ | нет данных |
| intl catalog | mobile | **65/100** | 20.8s ❌ | 2.9s ⚠ | 0.002 ✅ | 98ms ✅ | нет данных |
| intl catalog | desktop | **48/100** | 2.4s ✅ | 824ms ✅ | 0.004 ✅ | 1.7s ❌ | нет данных |
| jp catalog | mobile | **60/100** | 43.5s ❌ | 4.4s ❌ | 0.002 ✅ | 44ms ✅ | нет данных |
| jp catalog | desktop | **54/100** | 3.9s ⚠ | 976ms ✅ | 0.010 ✅ | 478ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.