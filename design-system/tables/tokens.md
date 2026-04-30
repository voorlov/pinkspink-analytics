# Tables Tokens — v1.1

Спецификация таблиц для аналитических дашбордов. Auto-fit высота по контенту до 20 строк, дальше — внутренний scroll со sticky-header. Высота строки = высоте контролов (28px) — единый ритм UI. Источник правды — [`tokens.json`](tokens.json). Визуальный референс — [`tables.html`](tables.html).

**Зависимости:** [Typography v1.1](../typography/) (шрифты, lh 1.25), [Controls v1.0](../controls/) (`--h-control` 28px).

---

## Базовые токены

| Токен | Значение | Что это |
|-------|----------|---------|
| `--row-h-table` | `28px` (= `--h-control`) | Высота строки таблицы. Совпадает с высотой контролов — таблицы и фильтры на одной высотной шкале. |
| `--max-rows-table` | `20` | Максимальное количество видимых строк до появления внутреннего scroll. |
| `--max-h-table` | `calc(var(--row-h-table) × 21)` = **588px** | Вычисляемая max-height обёртки. (20 строк + 1 header) × 28. |

```css
:root {
    --row-h-table: 28px;
    --max-rows-table: 20;
    --max-h-table: calc(var(--row-h-table) * (var(--max-rows-table) + 1));
}
```

---

## Поведение

| Случай | Высота контейнера | Scroll | Sticky header |
|--------|-------------------|--------|---------------|
| **Короткая** (1-20 строк) | По контенту: rows × 28 + 28 | Нет | Не нужен (нет scroll) |
| **Длинная** (>20 строк) | Фикс **588px** (max-height) | `overflow-y: auto` | **Активен** |

---

## Принципы

1. **Таблица сама определяет высоту контейнера** по контенту до 20 строк.
2. **Свыше 20 строк — внутренний scroll** со sticky-header. Заголовки колонок остаются видимыми при прокрутке.
3. **Все таблицы компактные по дефолту** — никаких opt-in modifier'ов вроде `.tbl-compact`.
4. **Высота строки = высоте контролов** (28px) — через всю UI один ритм.
5. **Тонкий scrollbar** (6px) — не съедает место, не доминирует.
6. **Никаких grid-cell-обёрток** с фиксированной высотой — таблица в обычном flow, заворачивается только в `.data-table-wrap`.
7. **`.data-table-wrap` — naked-обёртка** (с v1.1). Только функциональные свойства (`max-height`, `overflow-y`). Карточка (фон, скругление, тень) приходит ОТ `.block`, в который таблица заворачивается. Это часть глобального принципа «один уровень визуального обрамления».

---

## Анатомия

### Структура HTML

```html
<div class="data-table-wrap">
    <table class="data-table">
        <thead>
            <tr>
                <th>Колонка 1</th>
                <th>Колонка 2</th>
                <!-- ... -->
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Данные</td>
                <td class="highlight">Акцент</td>
            </tr>
            <!-- ... -->
        </tbody>
    </table>
</div>
```

### CSS

```css
.data-table-wrap {
    max-height: var(--max-h-table);              /* 588px */
    overflow-y: auto;
    /* Naked: фон/скругление/тень приходят от .block. */
}

.data-table {
    width: 100%;
    border-collapse: collapse;
}

.data-table th {
    position: sticky;                            /* sticky header при scroll */
    top: 0;
    z-index: 1;
    background:  var(--bg-inverse);
    color:       var(--tx-ondark);
    height:      var(--row-h-table);             /* 28px */
    padding:     0 var(--sp-3);                  /* horizontal только */
    font-size:   var(--fs-caption);              /* 11px */
    font-weight: var(--fw-semibold);             /* 600 */
    text-align:  left;
    line-height: 1.25;
}

.data-table td {
    height:         var(--row-h-table);          /* 28px */
    padding:        0 var(--sp-3);
    font-size:      var(--fs-caption);           /* 11px */
    line-height:    1.25;
    border-bottom:  1px solid var(--bg-divider);
    vertical-align: middle;                      /* центрирование контента */
}

.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover { background: var(--bg-hover); }
.data-table .highlight {
    font-weight: var(--fw-bold);
    color:       var(--c-highlight);
}

/* Тонкий scrollbar */
.data-table-wrap::-webkit-scrollbar { width: 6px; }
.data-table-wrap::-webkit-scrollbar-track { background: transparent; }
.data-table-wrap::-webkit-scrollbar-thumb {
    background:    var(--tx-muted);
    border-radius: var(--r-control);
}
```

---

## Соответствие другим разделам

### Typography v1.1 — ✓

- `th/td` на `--fs-caption` (11px)
- `line-height: 1.25` (наследуется от body)
- `th` semibold, `td` regular (через дефолт body)
- Font-family `'Ubuntu Mono'` наследуется

Никаких новых шрифтовых правил, всё через токены типографики.

### Controls v1.0 — ✓

`--row-h-table` = `--h-control` = **28px**. Таблицы и контролы (`.btn`, `.btn-sq`, `.check`) на одной высотной шкале:

- Filter-бар над таблицей: кнопки фильтров и строки таблицы пиксель-в-пиксель
- Чекбоксы рядом с table-row: одинаковая высота, выглядит ровно
- Tab-переключатель → таблица: одинаковая «плотность» элементов

### Charts v1.0 — ✓

Tables и charts живут в разных контейнерах. Если в одной `.cell` есть и таблица, и chart — это отдельный паттерн (KPI sparkline), не относится к Tables spec.

---

## Что упраздняется

### `.tbl-compact` modifier

В v0 (текущий дашборд) это opt-in класс для компактных строк. В v1.0 **компактность — дефолт**, modifier не нужен.

**При миграции дашборда:**
- Убрать `class="data-table tbl-compact"` → `class="data-table"`
- Удалить CSS-правило `.data-table.tbl-compact { ... }`

### `.h8x12` grid-cell для таблиц

Grid-ячейка `.h8x12` форсит высоту 720px у блоков с таблицами. Заменяется на обычный flow:

**Было:**
```html
<div class="grid">
    <div class="h8x12">
        <div class="title-area">...</div>
        <div class="cell" style="overflow:auto;">
            <table class="data-table tbl-compact">...</table>
        </div>
    </div>
</div>
```

**Стало:**
```html
<h3>Заголовок таблицы</h3>
<p class="meta">Описание</p>
<div class="data-table-wrap">
    <table class="data-table">...</table>
</div>
```

Никакого grid'а, никакой фикс-высоты, никакого `.tbl-compact`.

---

## Применение в новом проекте

### Шаг 0. Таблица всегда живёт внутри `.block`

С v1.1 `.data-table-wrap` — **naked**. Без обёртки `.block` фона, скругления и тени не будет — это by design. Структура: `<.block><.data-table-wrap><table></.../></.block>`.

### Шаг 1. Применить Typography v1.1 + Controls v1.0

См. соседние папки `typography/` и `controls/`.

### Шаг 2. Добавить токены таблиц в `:root`

```css
:root {
    --row-h-table: 28px;
    --max-rows-table: 20;
    --max-h-table: calc(var(--row-h-table) * (var(--max-rows-table) + 1));
}
```

### Шаг 3. Скопировать CSS-блок

Из секции «Анатомия → CSS» выше.

### Шаг 4. Использовать структуру

```html
<div class="data-table-wrap">
    <table class="data-table">
        <thead>...</thead>
        <tbody>...</tbody>
    </table>
</div>
```

Все таблицы — короткие или длинные — используют одну и ту же разметку. Высота определяется автоматически.

---

## История версий

- **v1.0 · 2026-04-29** — старт. Auto-fit высота по контенту до 20 строк, max-height 588px со sticky-header при превышении. Row-height 28px (= `--h-control`). Тонкий scrollbar 6px. Компактность по дефолту, упразднены `.tbl-compact` и `.h8x12` для блоков с таблицами. Полное соответствие Typography v1.1 и Controls v1.0.
- **v1.1 · 2026-04-29** — `.data-table-wrap` стал **naked**: убраны `background`, `border-radius`, `box-shadow`. Карточка приходит от `.block`, в который таблица заворачивается. Скроллбар-правила и sticky-header у `th` остаются. Bump следует за глобальным принципом «один уровень визуального обрамления» (см. корневой `design-system/README.md`) и Blocks v1.1 («карточка не вкладывается в карточку»). Поводом стала проблема двойных рамок на дашборде Pinkspink (таблицы получали и `.block`-карточку снаружи, и `.data-table-wrap`-карточку внутри).
