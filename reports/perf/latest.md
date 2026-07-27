# PageSpeed snapshot — 2026-07-27

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **40/100** | 7.4s ❌ | 1.9s ⚠ | 1.000 ❌ | 256ms ⚠ | нет данных |
| intl homepage | desktop | **71/100** | 1.0s ✅ | 460ms ✅ | 1.010 ❌ | 77ms ✅ | нет данных |
| jp homepage | mobile | **61/100** | 7.0s ❌ | 1.9s ⚠ | 0.000 ✅ | 371ms ⚠ | нет данных |
| jp homepage | desktop | **73/100** | 1.0s ✅ | 459ms ✅ | 1.010 ❌ | 51ms ✅ | нет данных |
| intl catalog | mobile | **48/100** | 4.6s ❌ | 1.8s ⚠ | 0.928 ❌ | 151ms ✅ | нет данных |
| intl catalog | desktop | **60/100** | 1.1s ✅ | 515ms ✅ | 0.385 ❌ | 391ms ⚠ | нет данных |
| jp catalog | mobile | **61/100** | 6.2s ❌ | 2.6s ⚠ | 0.000 ✅ | 192ms ✅ | нет данных |
| jp catalog | desktop | **54/100** | 1.1s ✅ | 516ms ✅ | 0.550 ❌ | 428ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.