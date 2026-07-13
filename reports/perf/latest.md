# PageSpeed snapshot — 2026-07-13

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **66/100** | 6.9s ❌ | 2.1s ⚠ | 0.000 ✅ | 188ms ✅ | нет данных |
| intl homepage | desktop | **92/100** | 1.3s ✅ | 585ms ✅ | 0.000 ✅ | 27ms ✅ | нет данных |
| jp homepage | mobile | **59/100** | 5.6s ❌ | 2.0s ⚠ | 0.000 ✅ | 508ms ⚠ | нет данных |
| jp homepage | desktop | **70/100** | 982ms ✅ | 510ms ✅ | 1.001 ❌ | 100ms ✅ | нет данных |
| intl catalog | mobile | **63/100** | 5.8s ❌ | 2.2s ⚠ | 0.000 ✅ | 268ms ⚠ | нет данных |
| intl catalog | desktop | **49/100** | 1.1s ✅ | 528ms ✅ | 0.385 ❌ | 724ms ❌ | нет данных |
| jp catalog | mobile | **55/100** | 6.8s ❌ | 2.2s ⚠ | 0.000 ✅ | 481ms ⚠ | нет данных |
| jp catalog | desktop | **58/100** | 1.1s ✅ | 514ms ✅ | 0.550 ❌ | 340ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.