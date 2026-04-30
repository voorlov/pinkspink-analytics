# Controls Tokens — v1.0

Спецификация контролов: filter-кнопок, квадратных переключателей, top-level навигации, чекбоксов. Источник правды — [`tokens.json`](tokens.json). Визуальный референс — [`controls.html`](controls.html).

**Зависимости:** Typography v1.0 (шрифт, размеры, веса).

---

## Базовые токены

| Токен | Значение | Что это |
|-------|----------|---------|
| `--h-control` | `28px` | Высота всех контролов (`.btn`, `.btn-sq`, `.check input`). Square кнопки = квадрат 28×28. |
| `--r-control` | `2px`  | Радиус всех контролов. Меньше чем у карточек/таблиц — даёт «инженерный» вид. |

**Состояния (стандартный набор для всех):** `default · hover · active · focus · disabled`.

---

## Четыре компонента

### `.btn` — Toggle button (filter)

Для filter-секций: grain (D/W/M), device (M/D/T), период и т.п. **Не использовать** для top-level навигации — для неё `.tab`.

```css
.btn {
    font-family: var(--ff-mono);                /* наследуется */
    height: var(--h-control);                    /* 28px */
    padding: 0 var(--sp-3);                      /* 0 vertical, 12 horizontal */
    display: inline-flex; align-items: center; justify-content: center;
    border-radius: var(--r-control);             /* 2px */
    font-size: var(--fs-body);                   /* 13px */
    font-weight: var(--fw-regular);              /* 400 */
    color: var(--tx-secondary);
    background: var(--bg-muted);
    border: 1px solid transparent;
    cursor: pointer;
    transition: background 120ms, color 120ms, border-color 120ms;
    line-height: 1;
}
.btn:hover    { background: var(--bg-border); color: var(--tx-primary); }
.btn.is-active{ background: var(--bg-inverse); color: var(--tx-ondark); }
.btn:focus    { outline: 2px solid var(--c-channel-social); outline-offset: 2px; }
.btn[disabled]{ opacity: 0.4; cursor: not-allowed; }
```

### `.btn-sq` — Square toggle

Для иконочно-компактных переключателей (D/W/M в шапке, иконки фильтров). Те же правила, фиксированный квадрат **28×28**, `font-weight: semibold`.

```css
.btn-sq {
    font-family: var(--ff-mono);
    width: var(--h-control); height: var(--h-control);     /* 28×28 */
    display: inline-flex; align-items: center; justify-content: center;
    font-size: var(--fs-body);                              /* 13px */
    font-weight: var(--fw-semibold);                        /* 600 */
    color: var(--tx-secondary);
    background: var(--bg-muted);
    border: 1px solid transparent;
    border-radius: var(--r-control);
    cursor: pointer;
    transition: background 120ms, color 120ms, border-color 120ms;
}
.btn-sq:hover    { background: var(--bg-border); color: var(--tx-primary); }
.btn-sq.is-active{ background: var(--bg-inverse); color: var(--tx-ondark); }
.btn-sq:focus    { outline: 2px solid var(--c-channel-social); outline-offset: 2px; }
```

### `.tab` — Navigation tab

Top-level навигация дашборда (Сводка / Воронки / Аналитика). **Только текст с подчёркиванием** — без заливки, без рамки. Визуально отделено от чёрных filter-кнопок.

```css
.tab {
    font-family: var(--ff-mono);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;       /* резерв под active-underline */
    padding: var(--sp-2) var(--sp-3) var(--sp-1);
    font-size: var(--fs-body);                   /* 13px */
    font-weight: var(--fw-regular);
    color: var(--tx-muted);                      /* приглушённый когда не активен */
    cursor: pointer;
    transition: color 120ms, border-color 120ms;
    line-height: 1.4;
}
.tab:hover    { color: var(--tx-secondary); }
.tab.is-active{
    color: var(--tx-primary);
    border-bottom-color: var(--tx-primary);
    font-weight: var(--fw-semibold);
}
.tab:focus    { outline: 2px solid var(--c-channel-social); outline-offset: 2px; border-radius: var(--r-control); }
```

Контейнер:

```css
.tab-bar {
    display: flex;
    gap: var(--sp-3);
    border-bottom: 1px solid var(--bg-border);
    padding: 0 var(--sp-3);
}
```

### `.check` — Checkbox

Кастомный чекбокс через `appearance: none`. Заполнение **чёрным** (`--bg-inverse`) при checked, белая галочка через CSS-rotation.

```css
.check {
    display: inline-flex; align-items: center;
    gap: var(--sp-1);
    font-size: var(--fs-caption);                /* 11px */
    color: var(--tx-primary);
    cursor: pointer;
    line-height: 1.4;
    user-select: none;
}
.check input {
    appearance: none; -webkit-appearance: none;
    width: 14px; height: 14px;
    border: 1.5px solid var(--bg-border);
    border-radius: var(--r-control);             /* 2px */
    background: var(--bg-card);
    cursor: pointer;
    flex-shrink: 0;
    position: relative;
    transition: background 120ms, border-color 120ms;
}
.check input:hover     { border-color: var(--tx-secondary); }
.check input:checked   { background: var(--bg-inverse); border-color: var(--bg-inverse); }
.check input:checked::after {
    content: '';
    position: absolute; left: 3px; top: 0;
    width: 5px; height: 9px;
    border: solid var(--tx-ondark);
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
}
.check input:focus     { outline: 2px solid var(--c-channel-social); outline-offset: 2px; }
.check[disabled]       { opacity: 0.4; cursor: not-allowed; }
.check[disabled] input { cursor: not-allowed; }
```

---

## Контейнеры

### `.filter-bar` — обёртка filter-секций

Внутри — несколько `.filter-group` side-by-side.

```css
.filter-bar {
    display: flex;
    align-items: flex-start;
    gap: var(--sp-5);                            /* 24px между группами */
    padding: var(--sp-3);
    background: var(--bg-card);
    border-radius: var(--r-xl);
    box-shadow: var(--sh-card);
    flex-wrap: wrap;
}
```

### `.filter-group` — одна группа фильтра

Подпись UPPERCASE серым + 1px полоска + кнопки.

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

```css
.filter-group { display: flex; flex-direction: column; gap: var(--sp-1); }

.filter-label {
    font-size: var(--fs-caption);                /* 11px */
    font-weight: var(--fw-regular);              /* 400 */
    color: var(--tx-secondary);
    text-transform: uppercase;
    letter-spacing: var(--ls-label);             /* 0.5px */
    padding-bottom: var(--sp-1);
    border-bottom: 1px solid var(--bg-border);
    min-width: 110px;
}

.filter-buttons { display: flex; gap: var(--sp-1); }
```

---

## Соответствие Typography v1.0

Все размеры и веса берутся из шкалы типографики:

| Компонент | Размер | Вес |
|-----------|--------|-----|
| `.btn` | `--fs-body` 13px | `--fw-regular` 400 |
| `.btn-sq` | `--fs-body` 13px | `--fw-semibold` 600 |
| `.tab` (default) | `--fs-body` 13px | `--fw-regular` 400 |
| `.tab` (active) | `--fs-body` 13px | `--fw-semibold` 600 |
| `.check label` | `--fs-caption` 11px | `--fw-regular` 400 |
| `.filter-label` | `--fs-caption` 11px UPPERCASE | `--fw-regular` 400 + `--ls-label` 0.5px |

**Шрифт:** наследуется от `body` через универсальное правило `* { font-family: inherit; }` (см. Typography v1.0). Без этого правила form-элементы (button, input) показывают системный sans-serif вместо Ubuntu Mono.

---

## Принципы

1. **Одна высота** — все контролы на `var(--h-control)` 28px. В filter-баре они стоят пиксель-в-пиксель.
2. **Один радиус** — все контролы на `var(--r-control)` 2px. Карточки/таблицы используют свои радиусы.
3. **Активное состояние через заливку** — для `.btn` и `.btn-sq`. Чёрный фон + белый текст.
4. **Навигация — особый случай** — только `.tab` с подчёркиванием, без заливки. Визуально отличается от filter-кнопок.
5. **Focus всегда виден** — outline 2px бренд-фиолетовый с offset 2px. Не убирать без замены.
6. **Никаких хардкод-размеров шрифта/веса** — всё из Typography v1.0.

---

## Применение в новом проекте

### Шаг 1. Применить Typography v1.0

См. соседнюю папку [`typography/`](../typography/). Без неё контролы не будут работать как задумано (шрифт, размеры).

### Шаг 2. Добавить токены контролов в `:root`

```css
:root {
    /* Controls v1.0 — дополнение к Typography v1.0 */
    --h-control: 28px;
    --r-control: 2px;
}
```

### Шаг 3. Скопировать CSS компонентов

Из секций «Четыре компонента» и «Контейнеры» выше.

### Шаг 4. Использовать

```html
<!-- Filter-bar с двумя группами -->
<div class="filter-bar">
    <div class="filter-group">
        <div class="filter-label">GRAIN</div>
        <div class="filter-buttons">
            <button class="btn-sq">D</button>
            <button class="btn-sq is-active">W</button>
            <button class="btn-sq">M</button>
        </div>
    </div>
    <div class="filter-group">
        <div class="filter-label">ПЕРИОД</div>
        <div class="filter-buttons">
            <button class="btn is-active">last 8w</button>
            <button class="btn">all</button>
        </div>
    </div>
</div>

<!-- Top-level навигация -->
<div class="tab-bar">
    <button class="tab">Сводка</button>
    <button class="tab is-active">Воронки</button>
    <button class="tab">Аналитика</button>
</div>

<!-- Чекбоксы -->
<label class="check"><input type="checkbox" checked> ig</label>
<label class="check"><input type="checkbox"> google</label>
```

---

## Совместимость с Typography v1.1

Typography v1.1 добавил глобальный `body { line-height: 1.25 }`. **Controls v1.0 совместим без изменений** — каждый компонент имеет явный line-height который перебивает наследование:

| Компонент | line-height | Почему |
|-----------|-------------|--------|
| `.btn` | `1` | Точное центрирование текста в фиксированной высоте 28px |
| `.btn-sq` | (наследует body 1.25) | `display: inline-flex; align-items: center` — flex центрирует, lh не критичен |
| `.tab` | `1.4` | Текст с подчёркиванием, нужен воздух |
| `.check label` | `1.4` | Длинные подписи могут переноситься на 2 строки |

При изменении body line-height с 1.5 (default) на 1.25 (Typography v1.1) текст в `.btn-sq` становится чуть плотнее, но визуально не заметно из-за flex-центрирования.

## История версий

- **v1.0 · 2026-04-28** — старт. 4 компонента (.btn, .btn-sq, .tab, .check), filter-group с UPPERCASE-подписью, единая высота 28px, единый радиус 2px, 5 состояний, полное соответствие Typography v1.0.
- **v1.0 совместим с Typography v1.1** (2026-04-29) — никаких правок CSS не требуется. Все line-heights явно заданы в компонентах, body inheritance не ломает.
