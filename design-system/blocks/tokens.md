# Blocks Tokens — v1.1

Спецификация блоков-карточек для аналитических дашбордов. Один класс `.block` заменяет цепочку `.h4x6 + .title-area + .cell` из v0. Высота определяется контентом, визуальный ритм — через единые chart-heights. Источник правды — [`tokens.json`](tokens.json). Визуальный референс — [`blocks.html`](blocks.html).

**Зависимости:** [Typography v1.1](../typography/) (h3/h4/.meta + spacing tokens), [Charts v1.0](../charts/) (`--ch-xs/sm/md/lg` heights).

---

## Принципы

1. **Один класс = один блок.** `.block` заменяет цепочку из трёх классов (`.h4x6 + .title-area + .cell`).
2. **Высота auto по контенту** — никаких `grid-row: span N` или `grid-auto-rows: 80px` хардкодов.
3. **Визуальный ритм через chart-heights**, а не через grid. Два блока с `.h-md` имеют одинаковую часть с графиком (280px) → одинаковая общая высота.
4. **Заголовки внутри блока — глобальные правила Typography v1.1.** Никаких font-overrides внутри блока.
5. **Span-классы задают только ширину**, не высоту. `.span-6` = grid-column span 6.
6. **Карточка не вкладывается в карточку.** Внутри `.block` запрещены вложенные элементы с `background` + `border-radius` + `box-shadow`. Wrappers внутри блока (`.chart-wrap`, `.data-table-wrap` и будущие компоненты) должны быть naked — только функциональные свойства (overflow, max-height, sticky, scrollbar). Карточка (фон, скругление, тень) приходит ТОЛЬКО от `.block`. Это часть глобального принципа «один уровень визуального обрамления» (см. корневой README).

---

## Базовые токены

| Токен | Значение | Что |
|-------|----------|-----|
| `block-padding` | `var(--sp-3)` (12px) | Внутренний padding блока |
| `block-radius` | `var(--r-xl)` (8px) | Скругление углов |
| `block-shadow` | `var(--sh-card)` | Тень карточки |

---

## Анатомия

### Структура HTML

```html
<div class="grid">
    <div class="block span-6 h-md">
        <h3>Заголовок блока</h3>
        <p class="meta">Описание</p>
        <div class="chart-wrap">
            <canvas>...</canvas>
        </div>
    </div>
    <div class="block span-6 h-md">
        ...
    </div>
</div>
```

### CSS

```css
.grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: var(--sp-4);
    /* НЕТ grid-auto-rows — ряды auto по контенту */
}

.block {
    background:      var(--bg-card);
    border-radius:   var(--r-xl);
    box-shadow:      var(--sh-card);
    padding:         var(--sp-3);
    display:         flex;
    flex-direction:  column;
}

/* Первый child не получает свой margin-top (он внутри padding'а блока) */
.block > :first-child { margin-top: 0; }

/* Span-классы — только ширина */
.span-12 { grid-column: span 12; }
.span-8  { grid-column: span 8; }
.span-6  { grid-column: span 6; }
.span-4  { grid-column: span 4; }
.span-3  { grid-column: span 3; }
.span-2  { grid-column: span 2; }

/* Height-варианты — применяют --ch-* токены к chart-wrap */
.block.h-xs .chart-wrap { height: var(--ch-xs); }   /* 60px sparkline */
.block.h-sm .chart-wrap { height: var(--ch-sm); }   /* 180px slider */
.block.h-md .chart-wrap { height: var(--ch-md); }   /* 280px default */
.block.h-lg .chart-wrap { height: var(--ch-lg); }   /* 360px detailed */
```

---

## Span-классы (placement в .grid)

| Класс | grid-column |
|-------|-------------|
| `.span-12` | span 12 (full width) |
| `.span-8` | span 8 |
| `.span-6` | span 6 (half) |
| `.span-4` | span 4 |
| `.span-3` | span 3 |
| `.span-2` | span 2 |

Имя класса не закодировано как «5×6» (5 строк × 6 колонок). Только ширина — высота определяется отдельно через `.h-*` или контентом.

---

## Height-варианты (для chart-блоков)

| Класс | --ch-* токен | Высота chart-wrap |
|-------|--------------|-------------------|
| `.h-xs` | `--ch-xs` | 60px (sparkline) |
| `.h-sm` | `--ch-sm` | 180px (slider, compact) |
| `.h-md` | `--ch-md` | 280px (default chart) |
| `.h-lg` | `--ch-lg` | 360px (detailed: bubble, dual-axis) |

**Visual ритм между блоками** сохраняется автоматически: два `.block.span-6.h-md` рядом имеют одинаковую часть с графиком (280px) и одинаковые header'ы (h3 + meta) → одинаковая общая высота. Без grid-row span хардкода.

---

## Что внутри блока

Стандартный паттерн — три ребёнка в `flex-direction: column`:

1. **Заголовок** — `<h3>` (или `<h4>` если sub-section)
2. **Описание** — `<p class="meta">` (опционально)
3. **Контент** — один из:
   - `<div class="chart-wrap"><canvas></div>` (для графиков)
   - `<div class="data-table-wrap"><table></div>` (для таблиц, см. Tables v1.0)
   - KPI-стуктура (label + value + spark, отдельный паттерн в Components — будущий спек)
   - Любой другой UI-элемент

Зазоры между этими тремя — задаются Typography v1.1:
- h3 → .meta = `var(--tight-pair)` 4px (правило `h2 + .meta`)
- .meta → контент = `var(--content-gap)` 8px (margin-bottom у .meta)

---

## Совместимость с другими разделами

### Typography v1.1 — ✓

Внутри `.block` работают глобальные правила h3, h4, .meta. Tight pair и content gap применяются автоматически.

Правило `.block > :first-child { margin-top: 0 }` гасит margin-top первого заголовка — он внутри padding'а блока, дополнительный margin не нужен.

### Charts v1.0 — ✓

`.h-xs/sm/md/lg` модификаторы применяют `--ch-*` токены из Charts v1.0 к chart-wrap внутри блока. Все Chart.defaults / pre-sets / typography-rules продолжают работать без изменений.

### Tables v1.0 — ✓

Внутри `.block` можно положить `.data-table-wrap` вместо `.chart-wrap`. Структура совместима. Tables упразднил `.h8x12` ещё раньше (`.data-table-wrap` сам управляет высотой).

### Controls v1.0 — ✓

Контролы (filter-bar, кнопки, чекбоксы, табы) живут вне `.block`, в нормальном flow на уровне страницы. Никаких пересечений.

---

## Что упраздняется при миграции

### Классы (заменяются)

| Было (v0) | Стало (Blocks v1.0) | Где использовалось |
|-----------|---------------------|---------------------|
| `.h4x12` | `.block.span-12` (+ `.h-md` или `.h-lg`) | 5 блоков |
| `.h4x8`  | `.block.span-8` | 1 блок |
| `.h4x6`  | `.block.span-6` (+ `.h-md`) | **26 блоков** (самый частый) |
| `.h4x4`  | `.block.span-4` | 0 в текущем view |
| `.h2x2`  | `.block.span-2` | 0 (KPI — будущий Components) |
| `.h1x4`  | `.block.span-4` | 0 |
| `.h1x2`  | `.block.span-2` | 0 |
| `.h8x12` | (уже упразднён в Tables v1.0) | 1 → `.data-table-wrap` |
| `.title-area` | (полностью удаляется) | **37 раз** |
| `.cell` | `.block` | 56 элементов |

### CSS-правила (удаляются)

- `grid-auto-rows: 80px` в `.grid`
- `grid-template-rows: 80px 1fr` во всех `.h4x*`
- `.title-area { ... }` целиком
- `.title-area h3 { font-size: var(--fs-body); font-weight: bold; }` (font override)
- `.title-area .meta { line-height: 1.3; }` (lh override)
- `.cell h2, .cell h3, .cell h4 { margin-top: 0 }` → заменяется на `.block > :first-child { margin-top: 0 }`

### Inline overrides (удаляются)

- `<h2 style="margin-top:32px;">Scroll Rate по сайту</h2>` (line ~3215)
- `<h2 style="margin-top:32px;">Cohort Retention</h2>` (line ~3231)

После миграции `--mt-h2: 44px` из Typography v1.1 даст нужный отступ автоматически.

---

## Применение в новом проекте

### Шаг 1. Применить Typography v1.1 + Charts v1.0

См. соседние папки. Без них блоки не получат правильные шрифты и chart-heights.

### Шаг 2. Скопировать CSS

Из секции «Анатомия → CSS» выше.

### Шаг 3. Использовать структуру

```html
<div class="grid">
    <div class="block span-6 h-md">
        <h3>...</h3>
        <p class="meta">...</p>
        <div class="chart-wrap"><canvas>...</canvas></div>
    </div>
</div>
```

### Шаг 4. Для разных контентов — разные wrappers

- График: `.chart-wrap` + `.h-md` модификатор
- Таблица: `.data-table-wrap` (Tables v1.0)
- KPI: специфическая структура (Components v1.0 — будущий спек)

---

## История версий

- **v1.0 · 2026-04-29** — старт. Единый `.block` примитив взамен `.h4x6 + .title-area + .cell` цепочки. `.grid` без `grid-auto-rows: 80px` хардкода. Span-классы для ширины (`.span-12 / 8 / 6 / 4 / 3 / 2`), height-классы для chart-высот (`.h-xs/sm/md/lg`). Visual ритм через единые chart-heights, не через grid-row span. Полное соответствие Typography v1.1, Charts v1.0, Tables v1.0, Controls v1.0.
- **v1.1 · 2026-04-29** — добавлен принцип №6 «карточка не вкладывается в карточку» (naked-wrappers). Закрепляет глобальный принцип «один уровень визуального обрамления» из корневого `design-system/README.md`. Совместим с `tables/` v1.1 (`.data-table-wrap` стал naked). Без правок в коде разделов, только новое правило. Поводом стала проблема двойных рамок на дашборде Pinkspink (бабл-чарты и таблицы получали и `.block`-карточку снаружи, и `.data-table-wrap`-карточку внутри).
