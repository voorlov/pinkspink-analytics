# PageSpeed snapshot — 2026-07-20

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **44/100** | 7.6s ❌ | 2.0s ⚠ | 1.000 ❌ | 65ms ✅ | нет данных |
| intl homepage | desktop | **97/100** | 1.0s ✅ | 529ms ✅ | 0.000 ✅ | 26ms ✅ | нет данных |
| jp homepage | mobile | **66/100** | 4.4s ❌ | 1.8s ⚠ | 0.000 ✅ | 460ms ⚠ | нет данных |
| jp homepage | desktop | **89/100** | 1.0s ✅ | 514ms ✅ | 0.000 ✅ | 203ms ⚠ | нет данных |
| intl catalog | mobile | **42/100** | 21.2s ❌ | 2.9s ⚠ | 0.000 ✅ | 915ms ❌ | нет данных |
| intl catalog | desktop | **50/100** | 981ms ✅ | 519ms ✅ | 0.385 ❌ | 616ms ❌ | нет данных |
| jp catalog | mobile | **42/100** | 6.9s ❌ | 2.1s ⚠ | 0.000 ✅ | 1.4s ❌ | нет данных |
| jp catalog | desktop | **63/100** | 1.1s ✅ | 514ms ✅ | 0.550 ❌ | 231ms ⚠ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.