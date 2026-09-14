# PageSpeed snapshot — 2026-09-14

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **60/100** | 39.1s ❌ | 2.9s ⚠ | 0.000 ✅ | 126ms ✅ | нет данных |
| intl homepage | desktop | **41/100** | 5.3s ❌ | 806ms ✅ | 0.077 ✅ | 692ms ❌ | нет данных |
| jp homepage | mobile | **56/100** | 80.4s ❌ | 4.4s ❌ | 0.000 ✅ | 112ms ✅ | нет данных |
| jp homepage | desktop | **70/100** | 10.1s ❌ | 961ms ✅ | 0.073 ✅ | 90ms ✅ | нет данных |
| intl catalog | mobile | **65/100** | 20.9s ❌ | 2.9s ⚠ | 0.002 ✅ | 79ms ✅ | нет данных |
| intl catalog | desktop | **84/100** | 1.3s ✅ | 813ms ✅ | 0.009 ✅ | 245ms ⚠ | нет данных |
| jp catalog | mobile | **62/100** | 42.0s ❌ | 4.5s ❌ | 0.000 ✅ | 48ms ✅ | нет данных |
| jp catalog | desktop | **69/100** | 3.3s ⚠ | 1.0s ✅ | 0.012 ✅ | 245ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.