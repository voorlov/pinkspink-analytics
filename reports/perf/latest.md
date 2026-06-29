# PageSpeed snapshot — 2026-06-29

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **44/100** | 5.9s ❌ | 2.0s ⚠ | 1.000 ❌ | 207ms ⚠ | нет данных |
| intl homepage | desktop | **95/100** | 1.3s ✅ | 530ms ✅ | 0.000 ✅ | 76ms ✅ | нет данных |
| jp homepage | mobile | **54/100** | 6.1s ❌ | 2.2s ⚠ | 0.000 ✅ | 573ms ⚠ | нет данных |
| jp homepage | desktop | **73/100** | 1.0s ✅ | 519ms ✅ | 0.000 ✅ | 455ms ⚠ | нет данных |
| intl catalog | mobile | **58/100** | 29.1s ❌ | 3.5s ❌ | 0.000 ✅ | 174ms ✅ | нет данных |
| intl catalog | desktop | **56/100** | 941ms ✅ | 520ms ✅ | 0.385 ❌ | 504ms ⚠ | нет данных |
| jp catalog | mobile | **60/100** | 6.5s ❌ | 2.3s ⚠ | 0.000 ✅ | 322ms ⚠ | нет данных |
| jp catalog | desktop | **62/100** | 901ms ✅ | 512ms ✅ | 0.550 ❌ | 291ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.