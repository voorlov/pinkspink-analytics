# PageSpeed snapshot — 2026-06-08

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **75/100** | 4.4s ❌ | 2.4s ⚠ | 0.000 ✅ | 129ms ✅ | нет данных |
| intl homepage | desktop | **90/100** | 1.2s ✅ | 544ms ✅ | 0.000 ✅ | 138ms ✅ | нет данных |
| jp homepage | mobile | **42/100** | 5.3s ❌ | 2.3s ⚠ | 0.000 ✅ | 2.9s ❌ | нет данных |
| jp homepage | desktop | **94/100** | 956ms ✅ | 526ms ✅ | 0.000 ✅ | 113ms ✅ | нет данных |
| intl catalog | mobile | **58/100** | 5.9s ❌ | 2.3s ⚠ | 0.000 ✅ | 437ms ⚠ | нет данных |
| intl catalog | desktop | **54/100** | 1.5s ✅ | 563ms ✅ | 0.337 ❌ | 505ms ⚠ | нет данных |
| jp catalog | mobile | **45/100** | 7.2s ❌ | 2.6s ⚠ | 0.000 ✅ | 962ms ❌ | нет данных |
| jp catalog | desktop | **52/100** | 1.3s ✅ | 563ms ✅ | 0.385 ❌ | 519ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.