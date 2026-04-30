# Typography Tokens — v1.1

Спецификация типографики для аналитических дашбордов. Шесть токенов размера, три веса, один шрифт, единый line-height, правила отступов заголовков. Источник правды — [`tokens.json`](tokens.json). Визуальный референс — [`typography.html`](typography.html).

**v1.1 что добавлено:** глобальный `line-height: 1.25` на body, унифицированный `.meta` на 11px caption (вместо 13 body), spacing-токены для заголовков (`--mt-h2/h3/h4`, `--tight-pair`, `--content-gap`).

---

## Шрифт

| Параметр | Значение |
|----------|----------|
| Family   | `'Ubuntu Mono', monospace` |
| Source   | [Google Fonts — Ubuntu Mono 400, 700](https://fonts.googleapis.com/css2?family=Ubuntu+Mono:wght@400;700&display=swap) |
| Fallback | `monospace` (любой системный моноширинный) |

**Почему моноширинный.** Числа в таблицах и KPI выравниваются по разрядам — можно глазом сравнивать столбцы цифр («1234» против «5678» — одинаковая ширина). На пропорциональных шрифтах цифры пляшут.

---

## Шкала размеров — 6 токенов

### `--fs-kpi` · 28px / bold

Главное KPI-число. Самый крупный размер в дашборде после удалённого `--fs-display`.

**Где:**
- `.kpi-value` в карточках 2×2 (Сессии, Доход, ATC и т.п.)

**Пример:** `12 845`, `$630`, `0.3%`

---

### `--fs-h2` · 18px / semibold (bold для бренда)

Средне-крупный универсальный размер. Покрывает четыре разные роли — все «средне-крупные» элементы дашборда сходятся сюда.

**Где:**
- Заголовки секций (`<h2>` внутри вкладок: «Воронки», «Сводка»)
- **Логотип / бренд** в шапке (`font-weight: bold`)
- Числа в `.metric .value` (3-кол. сетка слайдер-карточек: «31s», «3.5 стр»)
- KPI value в плотных сетках `.kpi-grid` (страница «Сводка»)

**Пример:** «Воронки» (semibold) · «Pinkspink» (bold) · «31s» (semibold)

---

### `--fs-h3` · 14px / semibold

Заголовки блоков. То, что подписывает каждую карточку `.cell` внутри сетки 12-кол.

**Где:**
- Заголовки блоков внутри карточек (`<h3>`)

**Пример:** «Динамика мобильной воронки», «Топ-5 source», «Эффективность по странам»

---

### `--fs-body` · 13px / regular

Основной текст и всё, что попадает в категорию «обычный текст». Включает несколько подрапортных ролей: `.meta`, h4-подзаголовки, лейблы фильтров, кнопки.

**Где:**
- Основной body-текст
- Подзаголовки `h4` (синоним 13px)
- `.meta`-параграфы (даты, периоды, описания)
- `.filters label` — лейблы у фильтров
- `.grain-btn` — кнопки переключения grain (day/week/month)
- `.delta` — дельты со стрелками
- `.country-row` — строки в списке топ-стран

**Пример:** «Период: 2026-W01 — 2026-W08», «Сессии: 12 845 · бенч 4w +12.4%»

---

### `--fs-caption` · 11px / regular (semibold для `<th>`)

Все мелкие UI-подписи. Самый «загруженный» по ролям токен — покрывает 7 разных мест в дашборде.

**Где:**
- `<th>` заголовки таблиц (`font-weight: semibold`, на тёмном фоне)
- `<td>` содержимое таблиц
- `.kpi-label` — UPPERCASE-лейблы в KPI-карточках (с `letter-spacing: var(--ls-label)`)
- `.kpi-bench` — бенчмарки («vs 4w avg: +12.4%»)
- `.header-meta` — подпись в sticky-header справа от логотипа
- `.agg-tag` — теги-маркеры
- **Datalabels на графиках** (Chart.js datalabels plugin) — числа над/в столбиках, на линиях

**Пример:** «КАНАЛ» (uppercase semibold), «1 234», «4.5%»

---

### `--fs-chart-meta` · 10px / regular

Отдельный токен для «обвязки» графиков — деления осей и легенда. Меньше datalabels (11px), чтобы значения выделялись над фоном осей.

**Где:**
- Подписи делений оси X и оси Y (Chart.js `scales.*.ticks.font.size`)
- Текст легенды на графиках (`plugins.legend.labels.font.size`)

**Логика разделения с `--fs-caption`:** datalabels (11px) — это сам контент графика, axis ticks и legend (10px) — рамка/обвязка. Иерархия: контент крупнее обвязки.

---

## Веса — 3 уровня

| Токен | Значение | Где применяется |
|-------|----------|------------------|
| `--fw-regular`  | 400 | Body, captions, описания |
| `--fw-semibold` | 600 | h2, h3, table th, .metric .value |
| `--fw-bold`     | 700 | KPI value, h1-уровень (если используется), логотип бренда, `.highlight` в таблицах |

---

## Letter-spacing

| Токен | Значение | Где |
|-------|----------|-----|
| `--ls-label` | `0.5px` | UPPERCASE-лейблы: `.kpi-label`, `.metric .label`, `.agg-tag` |

---

## Headings & Spacing (v1.1)

Универсальные правила отступов вокруг заголовков в нормальном flow.

### Принцип

Margin-top заголовка = **процент от его font-size**, затем округление **вниз до ближайшего чётного** целого. Получаются «дизайнерские» значения вместо дробных.

### Spacing-токены

| Токен | Значение | Формула |
|-------|----------|---------|
| `--mt-h2` | `44px` | 250% × 18 = 45 → **44** (round even down) |
| `--mt-h3` | `24px` | 175% × 14 = 24.5 → **24** |
| `--mt-h4` | `16px` | 125% × 13 = 16.25 → **16** |
| `--tight-pair` | `4px` | Зазор между заголовком и его описанием |
| `--content-gap` | `8px` | Зазор от `.meta` до контента (table/grid/chart) |

### Правила в CSS

```css
body { line-height: 1.25; }              /* применяется ко всему */

h2 {
    font-size:   var(--fs-h2);            /* 18 */
    font-weight: var(--fw-semibold);
    margin:      var(--mt-h2) 0 0;        /* 44px top */
    line-height: 1.25;
}

h3 {
    font-size:   var(--fs-h3);            /* 14 */
    font-weight: var(--fw-semibold);
    margin:      var(--mt-h3) 0 0;        /* 24px top */
    line-height: 1.25;
}

h4 {
    font-size:   var(--fs-body);          /* 13 */
    font-weight: var(--fw-semibold);
    margin:      var(--mt-h4) 0 0;        /* 16px top */
    color:       var(--tx-secondary);
    line-height: 1.25;
}

.meta {
    font-size:    var(--fs-caption);      /* 11px (унифицировано в v1.1) */
    color:        var(--tx-secondary);
    line-height:  1.25;
    margin:       0 0 var(--content-gap); /* 0 top, 8px bottom */
}

/* Tight pair — описание сразу после заголовка прижимается */
h2 + .meta, h3 + .meta, h4 + .meta {
    margin-top: var(--tight-pair);        /* 4px */
}
```

### Структура (как читается)

```
[предыдущий блок]
↕ 44px           ← --mt-h2 (margin-top h2)
<h2>
↕ 4px            ← --tight-pair (h2 + .meta)
<p class="meta">
↕ 24px           ← --mt-h3 (если идёт h3 после .meta) или
                    8px content-gap (если идёт table/grid)
<h3>
↕ 4px            ← --tight-pair
<p class="meta">
↕ 8px            ← --content-gap
[контент]
```

---

## Browser fix: form-элементы

**Проблема.** Браузеры (Chrome, Safari, Firefox) НЕ наследуют `font-family` от `body` для form-элементов: `<button>`, `<input>`, `<select>`, `<textarea>`. Они используют user-agent дефолт — обычно системный sans-serif (Helvetica/Arial). На моноширинном дашборде кнопки выглядят чужеродно — как будто другим шрифтом.

**Фикс.** Одна строка CSS:

```css
* { font-family: inherit; }
```

Универсальный селектор заставляет ВСЕ элементы наследовать `font-family` от родителя. Body выставляет Ubuntu Mono → каскадно применяется ко всему, включая form-элементы.

**Альтернатива** (более точечно, если боишься регрессий):

```css
button, input, select, textarea { font-family: inherit; }
```

Эффект тот же, но затрагивает только form-элементы.

---

## Совместимость с другими разделами

### Controls v1.0 — ✓ работает

Глобальный `body { line-height: 1.25 }` не нарушает контролы: каждый компонент Controls имеет **явный** `line-height`:

| Компонент | line-height | Почему |
|-----------|-------------|--------|
| `.btn` | `1` | Точное центрирование текста в фиксированной высоте 28px |
| `.btn-sq` | (наследует body 1.25) | Использует `display: inline-flex; align-items: center` — flex центрирует визуально, line-height не критичен |
| `.tab` | `1.4` | Текст в навигации с подчёркиванием — нужен воздух |
| `.check label` | `1.4` | Длинные подписи могут переноситься на 2 строки |

Тонкость: при изменении body line-height на 1.25 текст в `.btn-sq` (например, «D», «W», «M») становится чуть плотнее, но визуально не заметно из-за flex-центрирования.

### Charts v1.0 — ✓ работает

Графики рендерятся в `<canvas>` через Chart.js со своей font-системой. **Body line-height на canvas не влияет** — все размеры/шрифты графиков задаются через `Chart.defaults.font` (см. [`charts/tokens.md`](../charts/tokens.md)). `.chart-wrap` — это div-контейнер без текста, line-height наследуется но никак не используется.

Datalabels (Chart.js plugin) тоже рендерятся в canvas с своими font.size. Они ориентируются на `--fs-caption` 11px (через `Chart.defaults.plugins.datalabels.font.size = 11`), но line-height не задаётся — Chart.js сам управляет vertical metrics.

---

## Применение в новом проекте

### Шаг 1. Подключить шрифт в `<head>`

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Ubuntu+Mono:wght@400;700&display=swap" rel="stylesheet">
```

### Шаг 2. Скопировать `:root` блок в `<style>`

```css
:root {
    --ff-mono: 'Ubuntu Mono', monospace;
    --fw-regular:  400;
    --fw-semibold: 600;
    --fw-bold:     700;
    --ls-label: 0.5px;
    --fs-kpi:        28px;
    --fs-h2:         18px;
    --fs-h3:         14px;
    --fs-body:       13px;
    --fs-caption:    11px;
    --fs-chart-meta: 10px;

    /* v1.1: heading spacing */
    --mt-h2: 44px;        /* 250% × 18 = 45 → 44 */
    --mt-h3: 24px;        /* 175% × 14 = 24.5 → 24 */
    --mt-h4: 16px;        /* 125% × 13 = 16.25 → 16 */
    --tight-pair: 4px;
    --content-gap: 8px;
}
* { font-family: inherit; }
body { font-family: var(--ff-mono); line-height: 1.25; }

h2 { font-size: var(--fs-h2); font-weight: var(--fw-semibold); margin: var(--mt-h2) 0 0; line-height: 1.25; }
h3 { font-size: var(--fs-h3); font-weight: var(--fw-semibold); margin: var(--mt-h3) 0 0; line-height: 1.25; }
h4 { font-size: var(--fs-body); font-weight: var(--fw-semibold); margin: var(--mt-h4) 0 0; color: var(--tx-secondary); line-height: 1.25; }

.meta { font-size: var(--fs-caption); color: var(--tx-secondary); line-height: 1.25; margin: 0 0 var(--content-gap); }
h2 + .meta, h3 + .meta, h4 + .meta { margin-top: var(--tight-pair); }
```

### Шаг 3. Применять токены через `var(--...)`

```css
h2 { font-size: var(--fs-h2); font-weight: var(--fw-semibold); }
.kpi-value { font-size: var(--fs-kpi); font-weight: var(--fw-bold); }
.kpi-label { font-size: var(--fs-caption); text-transform: uppercase; letter-spacing: var(--ls-label); }
table th { font-size: var(--fs-caption); font-weight: var(--fw-semibold); }
table td { font-size: var(--fs-caption); }
```

### Для Chart.js

```js
Chart.defaults.font.family = "'Ubuntu Mono', monospace";
Chart.defaults.font.size = 10;  // = --fs-chart-meta (оси и легенда)
Chart.defaults.plugins.datalabels = Chart.defaults.plugins.datalabels || {};
Chart.defaults.plugins.datalabels.font = { size: 11 };  // = --fs-caption
```

---

## История версий

- **v1.0 · 2026-04-28** — старт. 6 токенов размера, 3 веса, шрифт Ubuntu Mono, фикс form-элементов.
- **v1.1 · 2026-04-29** — добавлены: `line-height: 1.25` на body, унифицированный `.meta` на 11px caption (вместо двух размеров), spacing-токены для заголовков (`--mt-h2: 44`, `--mt-h3: 24`, `--mt-h4: 16`, `--tight-pair: 4`, `--content-gap: 8`), правило округления margin-top заголовка = `floor_even(percent × font-size)`. Совместимо с Controls v1.0 и Charts v1.0 (явные line-height в контролах, canvas-независимость графиков).
