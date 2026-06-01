# PageSpeed snapshot — 2026-06-01

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **62/100** | 5.0s ❌ | 2.3s ⚠ | 0.000 ✅ | 479ms ⚠ | нет данных |
| intl homepage | desktop | **59/100** | 1.2s ✅ | 504ms ✅ | 1.010 ❌ | 286ms ⚠ | нет данных |
| jp homepage | mobile | **56/100** | 6.3s ❌ | 2.4s ⚠ | 0.000 ✅ | 472ms ⚠ | нет данных |
| jp homepage | desktop | **65/100** | 1.3s ✅ | 502ms ✅ | 1.007 ❌ | 173ms ✅ | нет данных |
| intl catalog | mobile | **41/100** | 6.6s ❌ | 2.0s ⚠ | 0.928 ❌ | 221ms ⚠ | нет данных |
| intl catalog | desktop | **41/100** | 1.6s ✅ | 523ms ✅ | 0.337 ❌ | 1.7s ❌ | нет данных |
| jp catalog | mobile | **66/100** | 6.7s ❌ | 2.3s ⚠ | 0.000 ✅ | 114ms ✅ | нет данных |
| jp catalog | desktop | **43/100** | 1.4s ✅ | 523ms ✅ | 0.385 ❌ | 1.1s ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.