# Blocks — v1.1

Раздел дизайн-системы про блоки-карточки. Один класс `.block` заменяет цепочку из трёх классов (`.h4x6 + .title-area + .cell`). Высота определяется контентом, визуальный ритм — через единые chart-heights.

**Зависит от:** [Typography v1.1](../typography/), [Charts v1.0](../charts/).

## Принципы

1. **Один класс = один блок** — никаких цепочек обёрток
2. **Высота auto по контенту** — нет фиксированных grid-row spans
3. **Visual ритм через chart-heights** — не через grid hardcode
4. **Заголовки внутри блока — глобальные правила Typography v1.1** — никаких font-overrides
5. **Span-классы — только ширина**, высота отдельно
6. **Карточка не вкладывается в карточку** (v1.1) — wrappers внутри блока (`.chart-wrap`, `.data-table-wrap`) naked, фон/скругление/тень только от `.block`

## Базовые токены

| Что | Значение |
|-----|----------|
| Padding | `var(--sp-3)` 12px |
| Radius  | `var(--r-xl)` 8px |
| Shadow  | `var(--sh-card)` |

## Структура

```html
<div class="grid">
    <div class="block span-6 h-md">
        <h3>Заголовок</h3>
        <p class="meta">Описание</p>
        <div class="chart-wrap"><canvas></canvas></div>
    </div>
</div>
```

## Span-классы (ширина в 12-кол. сетке)

`.span-12 / .span-8 / .span-6 / .span-4 / .span-3 / .span-2`

## Height-классы (для chart-блоков)

| Класс | Размер | Применение |
|-------|--------|------------|
| `.h-xs` | `--ch-xs` 60px | sparkline |
| `.h-sm` | `--ch-sm` 180px | slider, compact |
| `.h-md` | `--ch-md` 280px | default chart |
| `.h-lg` | `--ch-lg` 360px | detailed (bubble, dual-axis) |

Применяют `--ch-*` токены из Charts v1.0 к `chart-wrap` внутри блока.

## Что упраздняется при миграции дашборда

| Было (v0) | Стало | Кол-во |
|-----------|-------|--------|
| `.h4x12 / .h4x8 / .h4x6 / .h4x4` | `.block.span-N` | 32 |
| `.h2x2 / .h1x4 / .h1x2` | `.block.span-N` | 0 в текущем view |
| `.title-area` | (удаляется) | 37 |
| `.cell` | `.block` | 56 |
| `.h8x12` | (уже упразднён в Tables v1.0) | 1 |
| `grid-auto-rows: 80px` в `.grid` | удалить | — |
| `<h2 style="margin-top:32px">` inline | удалить | 2 |

## Совместимость

- **Typography v1.1** ✓ — внутри блока работают глобальные h3/h4/.meta + правило `.block > :first-child { margin-top: 0 }`
- **Charts v1.0** ✓ — высоты через `--ch-*` токены
- **Tables v1.1** ✓ — `.data-table-wrap` (naked) укладывается внутрь `.block`; карточка приходит от `.block`
- **Controls v1.0** ✓ — контролы вне блока, не пересекаются

## Файлы

| Файл | Зачем |
|------|-------|
| [`blocks.html`](blocks.html) | Открыть в браузере. Визуальная спецификация всех вариантов. |
| [`tokens.md`](tokens.md) | Прочитать. Полная спецификация с готовым CSS. |
| [`tokens.json`](tokens.json) | Импортировать. Машиночитаемая версия. |

## Применение в новом проекте

1. Применить Typography v1.1 + Charts v1.0 (соседние папки)
2. Скопировать CSS из [`tokens.md`](tokens.md) → секция «Анатомия»
3. Использовать `<div class="grid"><div class="block span-N h-M">...</div></div>`
