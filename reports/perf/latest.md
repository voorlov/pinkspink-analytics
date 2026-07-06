# PageSpeed snapshot — 2026-07-06

Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).

| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |
|---|---|---|---|---|---|---|---|
| intl homepage | mobile | **68/100** | 6.1s ❌ | 2.0s ⚠ | 0.000 ✅ | 192ms ✅ | нет данных |
| intl homepage | desktop | **93/100** | 1.1s ✅ | 533ms ✅ | 0.000 ✅ | 120ms ✅ | нет данных |
| jp homepage | mobile | **32/100** | 12.5s ❌ | 3.1s ❌ | 1.002 ❌ | 326ms ⚠ | нет данных |
| jp homepage | desktop | **88/100** | 1.1s ✅ | 513ms ✅ | 0.000 ✅ | 188ms ✅ | нет данных |
| intl catalog | mobile | **62/100** | 5.4s ❌ | 2.1s ⚠ | 0.000 ✅ | 392ms ⚠ | нет данных |
| intl catalog | desktop | **53/100** | 1.1s ✅ | 517ms ✅ | 0.385 ❌ | 553ms ⚠ | нет данных |
| jp catalog | mobile | **57/100** | 6.9s ❌ | 2.0s ⚠ | 0.000 ✅ | 481ms ⚠ | нет данных |
| jp catalog | desktop | **46/100** | 1.3s ✅ | 603ms ✅ | 0.550 ❌ | 604ms ❌ | нет данных |

**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.

LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.