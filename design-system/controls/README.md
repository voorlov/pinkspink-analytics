# Controls — v1.0

Раздел дизайн-системы про элементы управления: filter-кнопки, квадратные переключатели, top-level навигация, чекбоксы. Один высотный токен (28px), один радиус (2px), пять состояний, чёткое визуальное разделение filter-кнопок и навигации.

**Зависит от:** [Typography v1.0](../typography/) (шрифт, размеры, веса).

## Четыре компонента

| Компонент | Где | Состояние active | Высота |
|-----------|-----|------------------|--------|
| `.btn` | Filter-секции (период, и т.п.) | Чёрная заливка + белый текст | 28px |
| `.btn-sq` | Иконочно-компактные (D/W/M, Mob/Desk/Tab) | Чёрная заливка + белый текст | 28×28 |
| `.tab` | **Top-level навигация дашборда** (Сводка / Воронки / Аналитика) | **Подчёркивание + tx-primary + semibold** (без заливки) | по контенту |
| `.check` | Multi-select фильтры (источники, страны) | Чёрная заливка + белая галочка | 14×14 |

## Базовые токены

```css
:root {
    --h-control: 28px;   /* высота .btn, .btn-sq */
    --r-control: 2px;    /* радиус всех контролов */
}
```

## Состояния

Стандартный набор: **default · hover · active · focus · disabled**. Применяется ко всем компонентам кроме `.btn-sq` (без disabled — обычно не нужно для иконочных кнопок) и `.tab` (без disabled — навигация всегда доступна).

- **focus** = `outline: 2px solid var(--c-channel-social); outline-offset: 2px;` — видимый бренд-фиолетовый
- **disabled** = `opacity: 0.4; cursor: not-allowed`

## Filter-group

Когда несколько filter-кнопок объединены в смысловую группу (GRAIN, DEVICE, ПЕРИОД и т.п.) — оборачиваются в `.filter-group`:

```html
<div class="filter-group">
    <div class="filter-label">GRAIN</div>
    <div class="filter-buttons">
        <button class="btn-sq">D</button>
        <button class="btn-sq is-active">W</button>
        <button class="btn-sq">M</button>
    </div>
</div>
```

Подпись `--fs-caption` (11px) UPPERCASE серым с `--ls-label` letter-spacing — точь-в-точь как `.kpi-label` в Typography v1.0. Под подписью — 1px полоска `--bg-border`.

Несколько групп идут side-by-side в `.filter-bar` с `gap: var(--sp-5)` (24px).

## Соответствие Typography v1.0

- `.btn` / `.btn-sq` / `.tab`: `--fs-body` 13px
- `.check label` / `.filter-label`: `--fs-caption` 11px
- Все веса — из `--fw-regular/semibold/bold`
- Шрифт — наследуется от body через `* { font-family: inherit; }`

**Никаких хардкод-цифр** для font-size, weight, letter-spacing.

## Файлы

| Файл | Для кого / зачем |
|------|------------------|
| [`controls.html`](controls.html) | Открыть в браузере. Визуальная спецификация — все 4 компонента в 5 состояниях + filter-group + tab-bar. |
| [`tokens.md`](tokens.md) | Прочитать на спокойную голову. Полная текстовая спецификация с готовым CSS. |
| [`tokens.json`](tokens.json) | Импортировать в код. Машиночитаемая версия. |

## Применение в новом проекте

1. Применить Typography v1.0 (без неё контролы не будут работать как задумано)
2. Добавить `--h-control: 28px; --r-control: 2px;` в `:root`
3. Скопировать CSS из [`tokens.md`](tokens.md) → секция «Четыре компонента»
4. Использовать классы `.btn / .btn-sq / .tab / .check`
