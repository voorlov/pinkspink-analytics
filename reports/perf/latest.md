# PageSpeed snapshot — 2026-05-04

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **71/100** | 4.8s ❌ | 2.0s ⚠ | 0.000 ✅ | 237ms ⚠ | нет данных |
| intl homepage | desktop | **87/100** | 1.4s ✅ | 485ms ✅ | 0.000 ✅ | 164ms ✅ | нет данных |
| jp homepage | mobile | **68/100** | 6.7s ❌ | 2.0s ⚠ | 0.000 ✅ | 168ms ✅ | нет данных |
| jp homepage | desktop | **58/100** | 1.6s ✅ | 491ms ✅ | 0.000 ✅ | 833ms ❌ | нет данных |
| intl catalog | mobile | **45/100** | 6.2s ❌ | 2.0s ⚠ | 0.000 ✅ | 1.1s ❌ | нет данных |
| intl catalog | desktop | **50/100** | 1.2s ✅ | 487ms ✅ | 0.337 ❌ | 667ms ❌ | нет данных |
| jp catalog | mobile | **39/100** | 7.5s ❌ | 2.0s ⚠ | 0.000 ✅ | 1.7s ❌ | нет данных |
| jp catalog | desktop | **40/100** | 1.4s ✅ | 487ms ✅ | 0.408 ❌ | 1.5s ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.