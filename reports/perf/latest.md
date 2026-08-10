# PageSpeed snapshot — 2026-08-10

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **53/100** | 40.3s ❌ | 2.6s ⚠ | 0.000 ✅ | 355ms ⚠ | нет данных |
| intl homepage | desktop | **42/100** | 5.3s ❌ | 745ms ✅ | 1.000 ❌ | 153ms ✅ | нет данных |
| jp homepage | mobile | **52/100** | 64.8s ❌ | 5.1s ❌ | 0.000 ✅ | 229ms ⚠ | нет данных |
| jp homepage | desktop | **33/100** | 12.1s ❌ | 1.6s ✅ | 0.077 ✅ | 738ms ❌ | нет данных |
| intl catalog | mobile | **39/100** | 23.1s ❌ | 2.6s ⚠ | 1.002 ❌ | 131ms ✅ | нет данных |
| intl catalog | desktop | **45/100** | 1.4s ✅ | 746ms ✅ | 1.014 ❌ | 499ms ⚠ | нет данных |
| jp catalog | mobile | **26/100** | 49.5s ❌ | 7.2s ❌ | 1.000 ❌ | 278ms ⚠ | нет данных |
| jp catalog | desktop | **40/100** | 5.6s ❌ | 1.1s ✅ | 0.007 ✅ | 940ms ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.