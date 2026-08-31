# PageSpeed snapshot — 2026-08-31

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **61/100** | 38.0s ❌ | 2.7s ⚠ | 0.000 ✅ | 61ms ✅ | нет данных |
| intl homepage | desktop | **44/100** | 5.4s ❌ | 768ms ✅ | 0.076 ✅ | 550ms ⚠ | нет данных |
| jp homepage | mobile | **51/100** | 89.7s ❌ | 4.7s ❌ | 0.000 ✅ | 258ms ⚠ | нет данных |
| jp homepage | desktop | **34/100** | 11.9s ❌ | 1.1s ✅ | 0.077 ✅ | 1.5s ❌ | нет данных |
| intl catalog | mobile | **61/100** | 23.2s ❌ | 2.9s ⚠ | 0.002 ✅ | 171ms ✅ | нет данных |
| intl catalog | desktop | **74/100** | 1.3s ✅ | 763ms ✅ | 0.013 ✅ | 399ms ⚠ | нет данных |
| jp catalog | mobile | **46/100** | 44.3s ❌ | 3.9s ❌ | 0.000 ✅ | 536ms ⚠ | нет данных |
| jp catalog | desktop | **35/100** | 5.4s ❌ | 1.6s ✅ | 0.004 ✅ | 1.6s ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.