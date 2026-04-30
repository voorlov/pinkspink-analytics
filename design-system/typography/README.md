# Typography — v1.1

Раздел дизайн-системы про шрифты, размеры, веса и **отступы заголовков**. Шесть токенов размера + правила headings & spacing покрывают весь UI аналитического дашборда — от KPI-цифр до подписей осей графиков.

**v1.1 — что добавилось:**
- Глобальный `line-height: 1.25` на body
- Унифицированный `.meta` на 11px caption (вместо двух размеров)
- Spacing-токены для заголовков: `--mt-h2` (44), `--mt-h3` (24), `--mt-h4` (16), `--tight-pair` (4), `--content-gap` (8)
- Правило округления margin-top заголовка = `floor_even(percent × font-size)`
- Совместимо с Controls v1.0 и Charts v1.0 (см. секцию «Совместимость» в [tokens.md](tokens.md))

## Шкала

| Токен | Размер | Вес | Роль |
|-------|--------|-----|------|
| `--fs-kpi`         | 28px | bold (700)     | Главное KPI-число |
| `--fs-h2`          | 18px | semibold (600) / bold для бренда | Заголовки секций / логотип / metric values / dense KPI |
| `--fs-h3`          | 14px | semibold (600) | Заголовки блоков внутри карточек |
| `--fs-body`        | 13px | regular (400)  | Body, h4-подзаголовки, .meta, кнопки, лейблы фильтров |
| `--fs-caption`     | 11px | regular (semibold для `<th>`) | Таблицы, .kpi-label, .kpi-bench, .agg-tag, datalabels |
| `--fs-chart-meta`  | 10px | regular (400)  | Подписи осей и легенда графиков |

## Веса

- `--fw-regular`  · 400 — body
- `--fw-semibold` · 600 — h2, h3, table th, .metric .value
- `--fw-bold`     · 700 — KPI value, логотип, .highlight

## Headings & Spacing (v1.1)

| Токен | Значение | Формула |
|-------|----------|---------|
| `--mt-h2` | 44px | 250% × 18 = 45 → 44 (round even down) |
| `--mt-h3` | 24px | 175% × 14 = 24.5 → 24 |
| `--mt-h4` | 16px | 125% × 13 = 16.25 → 16 |
| `--tight-pair` | 4px | h2/h3/h4 ↔ .meta |
| `--content-gap` | 8px | .meta ↔ table/grid/chart |

`line-height: 1.25` глобально на body. Подробнее в [tokens.md → Headings & Spacing](tokens.md#headings--spacing-v11).

## Letter-spacing

- `--ls-label` · 0.5px — UPPERCASE-лейблы

## Шрифт

`'Ubuntu Mono', monospace` — Google Fonts, веса 400 и 700.

## Файлы

| Файл | Для кого / зачем |
|------|------------------|
| [`typography.html`](typography.html) | Открыть в браузере. Визуальная спецификация — реальные примеры каждого токена + аннотированный мокап + Chart.js demo. |
| [`tokens.md`](tokens.md) | Прочитать на спокойную голову. Текстовые правила: где какой токен, почему так разделено, инструкция по применению. |
| [`tokens.json`](tokens.json) | Импортировать в код. Машиночитаемая версия — для Python/Node/build-скриптов или для копи-паста `:root` блока. |

## Важно: фикс шрифта на формах

Form-элементы (`<button>`, `<input>`, `<select>`, `<textarea>`) **не наследуют** `font-family` от `body` в большинстве браузеров. Они показывают системный sans-serif (например, Helvetica на macOS) — на моноширинном дашборде это выглядит чужеродно.

**Фикс — одна строка:**

```css
* { font-family: inherit; }
```

Подробнее в [tokens.md → Browser fix](tokens.md#browser-fix-form-элементы).

## Применение в новом проекте

В трёх шагах: подключить шрифт в `<head>`, скопировать `:root` блок в `<style>`, применять через `var(--fs-...)`. Готовый snippet — в [`tokens.md → Применение в новом проекте`](tokens.md#применение-в-новом-проекте) или в полях `cssRoot.snippet` файла [`tokens.json`](tokens.json).
