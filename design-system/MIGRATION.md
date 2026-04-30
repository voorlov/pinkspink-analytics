# Migration Plan — Pinkspink Dashboard → Design System

План внедрения **пяти разделов** спецификации в действующий дашборд `generate_report.py`:

1. **Typography v1.1** — 6 размеров, line-height 1.25, headings & spacing tokens, унифицированный .meta
2. **Charts v1.0** — 6 типов графиков, форматтеры, пресеты легенды, hover-mode 'index'
3. **Controls v1.0** — `.btn / .btn-sq / .tab / .check`, filter-group, единая высота 28px
4. **Tables v1.0** — auto-fit высота, sticky-header, max 20 строк до scroll
5. **Blocks v1.0** — единый `.block` примитив взамен `.h4x*` + `.title-area` + `.cell`, `.grid` без `grid-auto-rows: 80px`

Цель — единый проход, без поломок генерации отчётов и визуальных регрессий.

**Создано:** 2026-04-28 (v1.0) · обновлено 2026-04-29 (Tables, Blocks, Headings v1.1)
**Объём работы:** ~10 часов в один заход (или поэтапно по фазам)
**Файл, который меняется:** только [`generate_report.py`](../generate_report.py)
**Файлы, которые перегенерируются после:** `report_day.html`, `report_week.html`, `report_month.html`, `styleguide.html`

**Статус:** часть Typography v1.1 уже применена (line-height 1.25, mt-h2/h3/h4, .meta унификация) — но без миграции Blocks v1.0 эффект частичный (`.title-area` font-overrides и 80px grid-row нивелируют новые правила). Phase 5 — Blocks — ключевая для финального результата.

---

## Аудит текущего состояния (обновлён 2026-04-29)

### Typography (Phase 1)
| Что | Состояние | Объём |
|-----|-----------|-------|
| `TOKENS["type"]["scale"]` | 15 токенов размера | сжать до 6 |
| `<h1>` в дашборде | уже отсутствует | пропускаем |
| `* { font-family: inherit; }` | установлен ✓ | (другая сессия) |
| `body { line-height: 1.25 }` | установлен ✓ | (другая сессия) |
| `--mt-h2/h3/h4`, `--tight-pair`, `--content-gap` | объявлены ✓ | (другая сессия) |
| `h2 + .meta { margin-top: var(--tight-pair) }` | установлен ✓ | (другая сессия) |
| Inline `<h2 style="margin-top:32px">` | 2 места | удалить — `--mt-h2: 44px` справится |

### Charts (Phase 2)
| Что | Состояние | Объём |
|-----|-----------|-------|
| `Chart.register(ChartDataLabels)` | НЕ вызывается | добавить |
| `Chart.defaults.interaction` | НЕ установлен | добавить `mode:'index'` |
| `Chart.defaults.font.size` | 11 (старая шкала) | сменить на 10 (`--fs-chart-meta`) |
| Графики с `new Chart(...)` | 25 штук | каждый — обновить options |
| `datalabels: {{...}}` конфигов | 23 | перевести на пресеты |
| Inline hex в чарт-конфигах | 8 (`borderColor: '#XXX'`) | заменить на `cssvar()` |
| `maxBarThickness` | НЕ установлен | добавить ко всем bar-датасетам |
| Sparkline min/max + сетка | НЕ реализовано | добавить |

### Controls (Phase 3)
| Что | Состояние | Объём |
|-----|-----------|-------|
| `.grain-btn` / `.tab-btn` / `.grain-sq` | старые стили в CSS | заменить на `.btn` / `.btn-sq` |
| `.tab` (text + underline) | НЕ существует | создать |
| `.check` (кастомный) | НЕ существует | создать (заменить дефолтные input) |
| `.filter-group` (UPPERCASE label + полоска) | НЕ существует | создать |
| `--h-control` / `--r-control` | НЕ объявлены | добавить в `:root` |

### Tables (Phase 4 — NEW)
| Что | Состояние | Объём |
|-----|-----------|-------|
| `.tbl-compact` modifier | opt-in в 7 из 14 таблиц | упразднить (компактность по дефолту) |
| `.h8x12` контейнер с фикс высотой 720px | используется для таблиц | упразднить, обернуть таблицу в `.data-table-wrap` |
| `.data-table` row-height | ~25px (через padding) | переход на фиксированный 28px = `--h-control` |
| Sticky thead | НЕ реализовано | добавить (`position: sticky; top: 0`) |
| Max-height для длинных таблиц | НЕ реализовано | `var(--max-h-table)` 588px + `overflow-y: auto` |
| `--row-h-table` / `--max-rows-table` | НЕ объявлены | добавить в `:root` |

### Blocks (Phase 5 — NEW, КРИТИЧНАЯ)
| Что | Состояние | Объём |
|-----|-----------|-------|
| `.h4x12 / .h4x8 / .h4x6 / .h4x4` | используются как grid-cells | заменить на `.block.span-N` (32 блока) |
| `.h2x2 / .h1x4 / .h1x2` | определены, не используются в main view | удалить (KPI — будущий Components) |
| `.title-area` (80px row, justify-content: flex-end) | используется в каждом chart-блоке | удалить целиком (37 экземпляров) |
| `.title-area h3` font override (13/bold) | переопределяет global 14/semibold | удалить override |
| `.title-area .meta` line-height 1.3 | переопределяет global 1.25 | удалить override |
| `.cell` | 56 элементов | переименовать в `.block` |
| `.grid { grid-auto-rows: 80px }` | хардкод в .grid | удалить — ряды auto |
| `.cell h2, h3, h4 { margin-top: 0 }` | reset правило | заменить на `.block > :first-child { margin-top: 0 }` |

---

## Phase 0 — Подготовка

**Цель:** иметь baseline для сравнения, защититься от потерь.

### Шаги
1. Сделать baseline-снапшоты (если ещё не сделаны):
   ```bash
   cp generate_report.py generate_report.before-migration.py
   cp report_week.html report_week.before-migration.html
   md5 generate_report.py styleguide.html report_*.html > /tmp/migration-baseline-md5.txt
   ```
2. Перегенерировать все три grain'а на текущей версии — должны открываться без ошибок:
   ```bash
   source venv/bin/activate
   python generate_report.py --grain all
   ```
3. Открыть в браузере все три отчёта, мысленно зафиксировать «как сейчас выглядит»

**Точка возврата:** в любой момент `cp generate_report.before-migration.py generate_report.py && python generate_report.py --grain all`.

---

## Phase 1 — Typography v1.1

**Цель:** сжать шкалу шрифтов до 6 токенов, исправить наследование шрифта на form-элементах, добавить Headings & Spacing tokens (line-height 1.25, унифицированный .meta, `--mt-h2/h3/h4`, tight-pair, content-gap). **Часть уже применена другой сессией** — см. аудит.
**Время:** ~1 час
**Спецификация:** [`typography/`](typography/) → [`tokens.md`](typography/tokens.md)

### Что меняется в `generate_report.py`

#### 1.1 `TOKENS["type"]` — сжимаем шкалу

**Сейчас** (15 токенов):
```python
"scale": {
    "h1": "32px", "h2": "20px", "kpi-xl": "28px", "kpi-lg": "20px",
    "metric": "18px", "brand": "16px", "h3": "14px", "h4": "13px",
    "body": "13px", "meta": "12px", "table": "12px", "th": "11px",
    "label": "11px", "tag": "10px", "datalabel": "10px"
}
```

**Стало** (6 токенов):
```python
"scale": {
    "kpi":        "28px",   # KPI value 2×2
    "h2":         "18px",   # section heads + brand + .metric .value + .kpi-grid
    "h3":         "14px",   # block titles
    "body":       "13px",   # body, h4, .meta, buttons, filter labels
    "caption":    "11px",   # th, td, kpi-label, kpi-bench, agg-tag, datalabels
    "chart-meta": "10px",   # axis ticks, legend
}
```

Удаляются: `h1` (h1 уже не используется), `kpi-lg` → h2, `metric` → h2, `brand` → h2, `h4` → body, `meta` → body, `table` → caption, `th` → caption, `label` → caption, `tag` → caption, `datalabel` → caption (но в Chart.defaults остаётся 11).

#### 1.2 CSS-блок (`generate_html` f-string `<style>`)

Найти все `var(--fs-XXX)` для удалённых токенов и заменить:
- `var(--fs-h1)` → удалить или заменить на `var(--fs-kpi)` (h1 не должно встречаться)
- `var(--fs-kpi-xl)` → `var(--fs-kpi)`
- `var(--fs-kpi-lg)` → `var(--fs-h2)`
- `var(--fs-metric)` → `var(--fs-h2)`
- `var(--fs-brand)` → `var(--fs-h2)`
- `var(--fs-h4)` → `var(--fs-body)`
- `var(--fs-meta)` → `var(--fs-body)`
- `var(--fs-table)` → `var(--fs-caption)`
- `var(--fs-th)` → `var(--fs-caption)`
- `var(--fs-label)` → `var(--fs-caption)`
- `var(--fs-tag)` → `var(--fs-caption)`
- `var(--fs-datalabel)` → удалить (Chart.defaults задаёт 11)

#### 1.3 Фикс form-шрифта

В начало CSS-блока добавить:
```css
* { font-family: inherit; }
```

Без этого `<button>`, `<input>`, `<select>` остаются с системным sans-serif.

### Верификация

```bash
python generate_report.py --grain week
# Открыть report_week.html
```

Что проверить глазами:
- Все цифры KPI (28px) на месте
- Заголовки секций (h2) — стало 18 вместо 20 (чуть мельче)
- Логотип Pinkspink в шапке — стало 18 (было 16, чуть крупнее, bold)
- `.metric .value` (например, «31s») — стало 18 (было 18, без изменений)
- Таблицы td — стало 11 (было 12, плотнее)
- Кнопки day/week/month — теперь Ubuntu Mono (а не Helvetica)
- Datalabels на графиках всё ещё на месте (Chart.defaults задаёт 11)

**Если что-то съехало — фиксируем точечно. Точка возврата — Phase 0 backup.**

---

## Phase 2 — Charts v1.0

**Цель:** ввести единые форматтеры, пресеты, hover-mode, перевести 25 графиков на v1.0.
**Время:** ~3-4 часа (объёмная фаза)
**Спецификация:** [`charts/`](charts/) → [`tokens.md`](charts/tokens.md)

### Что меняется в `generate_report.py`

#### 2.1 Глобальная настройка Chart.js (один раз, в JS-блоке)

Добавить в начало `<script>` блока (где сейчас `Chart.defaults.font.family = ...`):

```javascript
Chart.register(ChartDataLabels);          // ОБЯЗАТЕЛЬНО для v4
Chart.defaults.font.family = "'Ubuntu Mono', monospace";
Chart.defaults.color       = '#636E72';
Chart.defaults.font.size                  = 10;            // изменено с 11
Chart.defaults.plugins.legend.labels.font = { size: 10 };  // НОВОЕ
Chart.defaults.plugins.datalabels         = Chart.defaults.plugins.datalabels || {};
Chart.defaults.plugins.datalabels.font    = { size: 11 };  // оставить
Chart.defaults.scale.grid.color = 'rgba(0,0,0,0.06)';
Chart.defaults.interaction = { mode: 'index', intersect: false };  // НОВОЕ
```

#### 2.2 Helper-функции (один раз, в начале JS-блока)

```javascript
const cssvar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// Forматтеры — заменяют 11+ разных вариантов в коде
const fmt = {
    num: v => (v == null || v === 0) ? '' : v.toLocaleString('ru-RU'),
    pct: (v, dec=1) => (v == null || v === 0) ? '' : v.toFixed(dec) + '%',
    sec: v => (v == null || v === 0) ? '' : v + 's',
    cur: (v, c='$') => (v == null || v === 0) ? '' : c + v.toLocaleString('ru-RU')
};

// Полупрозрачный фон под лейблами
const dlPad = {
    backgroundColor: 'rgba(255,255,255,0.85)',
    borderRadius: 3,
    padding: { top: 1, bottom: 1, left: 4, right: 4 }
};

// Кастомный generator маркеров легенды (для line/mixed)
function legendLabels(chart) {
    return chart.data.datasets.map((ds, i) => {
        const isLine = (ds.type === 'line') || (chart.config.type === 'line' && !ds.type);
        const color = ds.borderColor || ds.backgroundColor;
        return {
            text: ds.label, fillStyle: color, strokeStyle: color,
            lineWidth: isLine ? 2 : 0,
            pointStyle: isLine ? 'line' : (chart.config.type === 'bubble' ? 'circle' : 'rect'),
            hidden: !chart.isDatasetVisible(i),
            datasetIndex: i
        };
    });
}

// Пресеты легенды
const legendPresets = {
    bar:    { display: true, position: 'top', align: 'start', labels: { usePointStyle: true, pointStyle: 'rect',   boxWidth: 10, boxHeight: 10, padding: 12 } },
    line:   { display: true, position: 'top', align: 'start', labels: { usePointStyle: true, boxWidth: 32, boxHeight: 2, padding: 12, generateLabels: legendLabels } },
    bubble: { display: true, position: 'top', align: 'start', labels: { usePointStyle: true, pointStyle: 'circle', boxWidth: 10, boxHeight: 10, padding: 12 } },
    mixed:  { display: true, position: 'top', align: 'start', labels: { usePointStyle: true, boxWidth: 14, boxHeight: 8, padding: 12, generateLabels: legendLabels } },
    none:   { display: false }
};

// Пресеты datalabel-позиций
const dlPresets = {
    barTop:    { anchor: 'end',    align: 'top',    color: cssvar('--tx-primary') },
    barCenter: { anchor: 'center', align: 'center', color: cssvar('--tx-ondark')  },
    line:      { align: 'top',                       color: cssvar('--tx-primary'), ...dlPad },
    off:       { display: false }
};
```

#### 2.3 Высоты — добавить в `:root`

```css
--ch-xs: 60px;
--ch-sm: 180px;
--ch-md: 280px;
--ch-lg: 360px;
```

И применить к контейнерам графиков (`.cell .chart-wrap`, `.kpi-spark` и т.п.) — где какой нужен.

#### 2.4 Каждый из 25 графиков — обновить options

Стратегия: проходить по типам последовательно (это позволяет легко возвращаться к одному типу если что-то сломалось).

**Group A — Grouped Bar (~9 графиков):** funnel-stages по периодам.
- `legend: legendPresets.bar`
- `datalabels: { ...dlPresets.barTop, formatter: fmt.num }`
- На каждый dataset с `type:'bar'` добавить `maxBarThickness: 40`
- Цвета через `cssvar('--c-funnel-X')` или `cssvar('--c-channel-X')`

**Group B — Stacked Bar (~3 графика):** композиция каналов.
- `legend: legendPresets.bar`
- `datalabels: { ...dlPresets.barCenter, display: ctx => ctx.dataset.data[ctx.dataIndex] > 30, formatter: fmt.num }`
- `tooltip: { callbacks: { label: ctx => ... +доля% } }` (паттерн `withShare`)

**Group C — Combo (~4 графика):** bar+line dual-axis.
- Per-dataset `datalabels` (не в plugins.datalabels):
  - bar: `barCenter` preset + display:>30
  - line: `{ anchor:'end', align:'top', offset:6, color: cssvar('--c-growth'), formatter: fmt.num, ...dlPad }`
- `legend: legendPresets.mixed`
- Bar-датасеты: `order: 2`. Line-датасеты: `order: 0` (на переднем плане)
- Line-датасеты: `pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0`

**Group D — Line (~10 графиков):** % конверсии, тренды.
- Dataset defaults: `borderWidth: 2, tension: 0.3, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0`
- `legend: legendPresets.line`
- `datalabels: { ...dlPresets.line, formatter: v => fmt.pct(v, 1) }`
- `tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmt.pct(ctx.parsed.y, 1) } }`

**Group E — Bubble (~2 графика):** эффективность source.
- `interaction: { mode: 'point', intersect: true }` (override global)
- `layout: { padding: { top: 16, right: 32, bottom: 4, left: 4 } }`
- `legend: legendPresets.bubble`
- `datalabels: { anchor:'end', align:'right', offset:6, clamp:true, formatter: (v,ctx)=>ctx.dataset.label, color: cssvar('--tx-primary'), ...dlPad }`
- `tooltip: twoDimensions pattern`

**Group F — Sparkline (~5 графиков):** мини-тренды в KPI.
- Уже почти работают, нужно добавить min/max:
  - `pointRadius: ctx => v === Math.max(...) || v === Math.min(...) ? 2.5 : 0`
  - `pointBackgroundColor: ctx => max → growth · min → decline · else transparent`
  - `datalabels` с `display: только в min/max`, `font: { size: 10 }`, `color: max → growth · min → decline`, `align: top/bottom`
- `scales.x: { display: true, grid: { color: 'rgba(0,0,0,0.06)', drawTicks: false }, ticks: { display: false } }`
- Контейнер: bump высоту с 60px → 100px для версий с min/max

#### 2.5 Inline hex → `cssvar()`

Поиск: `grep -E "(borderColor|backgroundColor): '#[0-9A-Fa-f]+'" generate_report.py`. Заменить каждый на соответствующий `cssvar('--c-...')`.

### Верификация

```bash
python generate_report.py --grain week
# открыть report_week.html
```

- Datalabels видны на всех bar/line чартах (Chart.register работает)
- Hover на любую x-позицию → tooltip со значениями ВСЕХ датасетов
- Sparklines имеют min/max подписи (зелёный/красный) и лёгкую вертикальную сетку
- Bar-чарты не «жирные» при малом числе периодов
- Маркеры легенды компактные (не 36×12)
- В Combo: линия на переднем плане, у её точек видны кружки 4px
- В Bubble: имена source у пузырей, не вылезают за пределы

---

## Phase 3 — Controls v1.0

**Цель:** заменить 4 типа контролов на v1.0, добавить filter-group, выделить навигацию в `.tab`.
**Время:** ~1-2 часа
**Спецификация:** [`controls/`](controls/) → [`tokens.md`](controls/tokens.md)

### Что меняется в `generate_report.py`

#### 3.1 Добавить токены в `:root`

```css
--h-control: 28px;
--r-control: 2px;
```

#### 3.2 Заменить CSS старых классов на новые

**Удалить:**
```css
.grain-btn { ... }
.grain-btn:hover { ... }
.grain-active { ... }
.tab-btn { ... }
.tab-btn:hover { ... }
.tab-active { ... }
.grain-sq { ... }
.grain-sq:hover { ... }
.bubble-filters label { ... }  /* частично */
```

**Добавить** (по `tokens.md` controls):
```css
.btn { ... }                              /* единый toggle: filter + ex-tab-btn-в-фильтрах */
.btn:hover, .btn.is-active, .btn:focus, .btn[disabled] { ... }
.btn-sq { ... }                           /* квадратные иконки D/W/M */
.btn-sq:hover, .btn-sq.is-active, .btn-sq:focus { ... }
.tab { ... }                              /* НОВОЕ — top-level навигация */
.tab:hover, .tab.is-active, .tab:focus { ... }
.tab-bar { ... }
.check { ... }                            /* НОВОЕ — кастомный чекбокс */
.check input { ... } / :hover / :checked / :focus / etc.
.filter-bar { ... }                       /* обёртка filter-секций */
.filter-group { ... }                     /* подпись + полоска + кнопки */
.filter-group .filter-label { ... }
.filter-group .filter-buttons { ... }
```

#### 3.3 Обновить HTML-разметку

Везде в `generate_report.py` где есть HTML-генерация контролов:

- `<button class="grain-btn">` → `<button class="btn">`
- `<button class="grain-btn grain-active">` → `<button class="btn is-active">`
- `<button class="tab-btn">` → решение по контексту:
  - если это TOP-LEVEL вкладка (Сводка / Воронки / Аналитика) → `<button class="tab">`
  - если это filter-кнопка которая случайно использовала tab-btn → `<button class="btn">`
- `<button class="grain-sq">` → `<button class="btn-sq">`
- `<input type="checkbox">` → завернуть в `<label class="check">` + соблюсти структуру

#### 3.4 Filter-bar layout — собрать filter-group

Найти существующую filter-секцию (`.filters` контейнер) и переписать на `.filter-bar` + `.filter-group`:

**Было:**
```html
<div class="filters">
    <label>Grain:</label>
    <button class="grain-btn">day</button>
    <button class="grain-btn grain-active">week</button>
    <button class="grain-btn">month</button>
</div>
```

**Стало:**
```html
<div class="filter-bar">
    <div class="filter-group">
        <div class="filter-label">GRAIN</div>
        <div class="filter-buttons">
            <button class="btn-sq">D</button>
            <button class="btn-sq is-active">W</button>
            <button class="btn-sq">M</button>
        </div>
    </div>
    <!-- + другие группы (DEVICE, ПЕРИОД, ...) -->
</div>
```

#### 3.5 Top-level навигация — отдельный `.tab-bar`

В sticky-header или там где сейчас табы:

```html
<div class="tab-bar">
    <button class="tab" onclick="switchTab('summary', this)">Сводка</button>
    <button class="tab is-active" onclick="switchTab('funnels', this)">Воронки</button>
    <button class="tab" onclick="switchTab('analytics', this)">Аналитика</button>
</div>
```

#### 3.6 JS — обновить классы переключения

В функциях `switchTab(...)` и подобных, где есть `classList.add('grain-active')` и `classList.remove('grain-active')`:
- `grain-active` → `is-active`
- `tab-active` → `is-active`

### Верификация

```bash
python generate_report.py --grain all
```

- Все три отчёта открываются без ошибок
- Filter-кнопки и квадратные стоят пиксель-в-пиксель (одинаковая высота 28px)
- Навигация (Сводка / Воронки / Аналитика) — текст с подчёркиванием активной, без чёрной заливки
- Чекбоксы — кастомные, при checked заливаются чёрным с белой галочкой
- Tab по клавиатуре — виден focus-outline (фиолетовый)
- Шрифт всех контролов — Ubuntu Mono (не системный)
- Filter-секции имеют UPPERCASE-подписи (GRAIN, DEVICE, ...) с тонкой полоской

---

## Phase 4 — Tables v1.0 (NEW)

**Цель:** перевести таблицы на auto-fit высоту до 20 строк со sticky-header при превышении. Упразднить `.tbl-compact` modifier и `.h8x12` grid-cell.
**Время:** ~1 час
**Спецификация:** [`tables/`](tables/) → [`tokens.md`](tables/tokens.md)

### Что меняется в `generate_report.py`

#### 4.1 Добавить токены в `:root`

```css
--row-h-table: 28px;        /* = --h-control */
--max-rows-table: 20;
--max-h-table: calc(var(--row-h-table) * (var(--max-rows-table) + 1));  /* 588px */
```

#### 4.2 Заменить CSS таблиц

**Удалить:**
```css
.data-table { ... overflow: hidden; }                /* старые стили */
.data-table th { padding: 8px 12px; ... }            /* var. padding */
.data-table td { padding: 6px 12px; ... }
.data-table.tbl-compact { ... }                       /* opt-in modifier */
.data-table.tbl-compact td, .data-table.tbl-compact th { height: auto; line-height: 1.3; }
.h8x12 { grid-row: span 9; ... }                      /* фикс-высота cell */
.h8x12 > .cell { grid-row: 2; overflow: auto; }
```

**Добавить** (полный CSS см. в [`tables/tokens.md`](tables/tokens.md)):
```css
.data-table-wrap { max-height: var(--max-h-table); overflow-y: auto; ... }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { position: sticky; top: 0; z-index: 1; height: var(--row-h-table); padding: 0 var(--sp-3); ... }
.data-table td { height: var(--row-h-table); padding: 0 var(--sp-3); vertical-align: middle; ... }
.data-table-wrap::-webkit-scrollbar { width: 6px; ... }
```

#### 4.3 Обновить HTML — обернуть таблицы в `.data-table-wrap`

Найти все 14 таблиц `<table class="data-table ...">` и обернуть:

**Было:**
```html
<div class="h8x12">
    <div class="title-area">...</div>
    <div class="cell" style="overflow:auto;">
        <table class="data-table tbl-compact">...</table>
    </div>
</div>
```

**Стало:**
```html
<h3>...</h3>
<p class="meta">...</p>
<div class="data-table-wrap">
    <table class="data-table">...</table>
</div>
```

(После Phase 5 — Blocks — это будет внутри `.block` с теми же h3/meta, но в Phase 4 пока в обычном flow.)

#### 4.4 Удалить `.tbl-compact` из всех HTML-вхождений

```bash
# Найти все вхождения
grep -n 'tbl-compact' generate_report.py
# Вручную или через sed убрать класс
```

### Верификация

- Все 14 таблиц рендерятся без пустот под собой
- Длинные таблицы (если появятся) — внутренний scroll со sticky thead
- Высота строки 28px (= кнопкам) — единый ритм с фильтрами

---

## Phase 5 — Blocks v1.0 (NEW, КРИТИЧНАЯ)

**Цель:** заменить цепочку `.h4x6 + .title-area + .cell` единым примитивом `.block.span-N.h-M`. Удалить хардкод `grid-auto-rows: 80px`. Visual ритм переезжает на единые chart-heights. **Это ключевая фаза** — без неё типография v1.1 даёт частичный эффект (`.title-area` font-overrides и 80px-row нивелируют новые правила).
**Время:** ~3-4 часа (большая фаза, 32 блока + 37 title-area + переименование .cell)
**Спецификация:** [`blocks/`](blocks/) → [`tokens.md`](blocks/tokens.md)

### Что меняется в `generate_report.py`

#### 5.1 Заменить CSS .grid

**Было:**
```css
.grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    grid-auto-rows: 80px;          /* ← удалить */
    gap: var(--sp-4);
    margin-bottom: var(--sp-5);
}
```

**Стало:**
```css
.grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: var(--sp-4);
    margin-bottom: var(--sp-5);
    /* grid-auto-rows удалён — ряды auto по контенту */
}
```

#### 5.2 Удалить классы `.h4x*`, `.h2x2`, `.h1x*`

```css
/* Удалить ЦЕЛИКОМ: */
.h4x12, .h4x8, .h4x6, .h4x4 { ... }
.h4x12 { grid-column: span 12; }
.h4x8  { grid-column: span 8; }
.h4x6  { grid-column: span 6; }
.h4x4  { grid-column: span 4; }
.h2x2 { ... } .h1x4 { ... } .h1x2 { ... }
.h4x12 > .cell, .h4x8 > .cell, ... { grid-row: 2; }
.h4x12 > .chart-wrap:only-child, ... { grid-row: 1 / -1; }
```

#### 5.3 Удалить `.title-area` целиком

```css
/* Удалить ЦЕЛИКОМ: */
.title-area { display: flex; flex-direction: column; justify-content: flex-end; padding-bottom: var(--sp-1); grid-row: 1; }
.title-area h3 { font-size: var(--fs-body); font-weight: var(--fw-bold); margin: 0 0 2px 0; }
.title-area .meta { margin: 0; font-size: var(--fs-caption); color: var(--tx-secondary); line-height: 1.3; }
```

#### 5.4 Переименовать `.cell` → `.block` + добавить новые правила

**Было:**
```css
.cell { background: var(--bg-card); border-radius: var(--r-xl); padding: 14px; box-shadow: var(--sh-card); overflow: hidden; display: flex; flex-direction: column; height: 100%; }
.cell h2, .cell h3, .cell h4 { margin-top: 0; }
```

**Стало:**
```css
.block {
    background: var(--bg-card);
    border-radius: var(--r-xl);
    box-shadow: var(--sh-card);
    padding: var(--sp-3);                    /* было хардкод 14px */
    display: flex;
    flex-direction: column;
}
.block > :first-child { margin-top: 0; }   /* более узкое правило */

/* Span-классы (ширина) */
.span-12 { grid-column: span 12; }
.span-8  { grid-column: span 8; }
.span-6  { grid-column: span 6; }
.span-4  { grid-column: span 4; }
.span-3  { grid-column: span 3; }
.span-2  { grid-column: span 2; }

/* Height-варианты (для chart-блоков) */
.block.h-xs .chart-wrap { height: var(--ch-xs); }
.block.h-sm .chart-wrap { height: var(--ch-sm); }
.block.h-md .chart-wrap { height: var(--ch-md); }
.block.h-lg .chart-wrap { height: var(--ch-lg); }
```

#### 5.5 Обновить HTML-разметку всех блоков

Подход: глобальная замена паттернов через sed/grep + ручная проверка.

**Было** (повторяется 32 раза):
```html
<div class="h4x6">
    <div class="title-area"><h3>...</h3><p class="meta">...</p></div>
    <div class="cell"><canvas id="..."></canvas></div>
</div>
```

**Стало:**
```html
<div class="block span-6 h-md">
    <h3>...</h3>
    <p class="meta">...</p>
    <div class="chart-wrap"><canvas id="..."></canvas></div>
</div>
```

**Маппинг классов:**
- `.h4x6` → `.block.span-6.h-md`
- `.h4x12` → `.block.span-12.h-md` (или `.h-lg` если bubble/dual-axis)
- `.h4x8` → `.block.span-8.h-md`
- `.h4x4` → `.block.span-4.h-md`
- `.h8x12` → уже не должно остаться после Phase 4
- `.h2x2 / h1x*` → не используются в main view, можно проигнорировать или преобразовать когда понадобятся

**Внутри:**
- `<div class="title-area">` → удалить, оставить голые `<h3>` + `<p class="meta">`
- `<div class="cell">` → удалить, оставить контент (`<canvas>` или `<div class="chart-wrap"><canvas></div>`)

#### 5.6 Удалить inline overrides на h2

```bash
grep -n 'style="margin-top:32px"' generate_report.py
# Убрать целиком — --mt-h2: 44px справится
```

### Верификация

- ВСЕ блоки используют `.block.span-N.h-M`
- НЕТ упоминаний `.h4x*`, `.h2x2`, `.h1x*`, `.title-area`, `.cell` (кроме комментариев и `.cell-kpi` если он останется как отдельный)
- НЕТ inline `style="margin-top"` на h2
- Visual ритм между блоками сохраняется (одинаковые chart-heights)
- Нет «лишних 43px пустоты» сверху блоков (была главная проблема)

---

## Phase 6 — Финальная верификация и cleanup

### Шаги
1. Перегенерировать всё: `python generate_report.py --grain all`
2. Открыть в браузере все три (`day`, `week`, `month`) + `styleguide.html`
3. Проверить ключевые сценарии:
   - Переключение вкладок
   - Hover на графиках (видны все значения в периоде)
   - Hover на кнопках (плавный transition)
   - Tab по клавиатуре (focus visible)
   - Чекбоксы в bubble-фильтрах работают (скрывают/показывают source)
   - Длинные таблицы скроллятся со sticky-header
4. Сравнить визуально с baseline (Phase 0):
   - `report_week.before-migration.html` vs новый
   - Структурный паритет: одинаковое число графиков, таблиц, KPI-карточек
5. Удалить backup'ы если всё ок:
   ```bash
   rm generate_report.before-migration.py
   rm report_week.before-migration.html
   ```
6. Обновить `CLAUDE.md` — пометить «Дашборд переведён на Design System (Typography v1.1, Charts v1.0, Controls v1.0, Tables v1.0, Blocks v1.0)», обновить TOKENS-структуру в документации

### Контрольный grep — no leftovers

```bash
# Не должно быть старых control-классов
grep -E '\.grain-btn|\.tab-btn|\.grain-sq|grain-active|tab-active|\.tbl-compact' generate_report.py

# Не должно быть старых block-классов
grep -E '\.h4x[0-9]+|\.h8x[0-9]+|\.h2x2|\.h1x[0-9]+|\.title-area' generate_report.py

# Не должно быть .cell (заменено на .block) — кроме .cell-kpi если используется
grep -E '\bclass="[^"]*cell[^"]*"' generate_report.py | grep -v 'cell-kpi'

# Не должно быть удалённых fs-токенов
grep -E "var\(--fs-(h1|kpi-xl|kpi-lg|metric|brand|h4|meta|table|th|label|tag|datalabel)\)" generate_report.py

# Не должно быть inline hex в Chart-конфигах
grep -E "(borderColor|backgroundColor): '#[0-9A-Fa-f]" generate_report.py

# Не должно быть inline overrides на h2
grep -E '<h2 style="margin-top' generate_report.py

# Не должно быть grid-auto-rows: 80px
grep -E 'grid-auto-rows: 80px' generate_report.py

# Должно быть зарегистрировано
grep "Chart.register(ChartDataLabels)" generate_report.py
```

---

## Rollback план

Если что-то идёт не так в любой фазе:

```bash
# Полный откат на состояние до миграции
cp generate_report.before-migration.py generate_report.py
python generate_report.py --grain all
```

Или из git (если коммитили перед миграцией):

```bash
git checkout HEAD generate_report.py
python generate_report.py --grain all
```

**Совет:** коммитить после каждой фазы (Phase 1 → 2 → 3 → 4 → 5 → 6) — даёт точки возврата к промежуточному состоянию. Phase 5 (Blocks) разбить на под-коммиты по группам блоков.

---

## Risk register

| Риск | Фаза | Вероятность | Митигация |
|------|------|-------------|-----------|
| Сломаются datalabels на конкретных графиках после `Chart.register` | 2 | средняя | Phase 0 backup, проверять каждый чарт после Phase 2 |
| Несовпадение размеров шрифта где-то в CSS (oblivion) | 1 | средняя | grep на удалённые `--fs-*` после Phase 1 |
| Потеря active-состояния навигации | 3 | низкая | внимательно проверить JS-функции переключения вкладок |
| Bubble-чарты с `interaction: index` (наследуют global) | 2 | средняя | явно ставить `interaction: { mode: 'point', intersect: true }` per-chart |
| Чекбоксы в bubble-filter перестают фильтровать | 3 | низкая | оставить ту же `<input type="checkbox">` структуру под `.check label`, JS-логика не трогается |
| Graphs с per-dataset datalabels игнорируют global config | 2 | низкая | Combo-графики обязательно обновлять полностью |
| Длинные таблицы перестают скроллиться внутри (Phase 4) | 4 | низкая | проверить `.data-table-wrap` обёртку у каждой таблицы |
| Sticky thead не работает (overflow родителя ломает) | 4 | средняя | `.data-table-wrap` должен иметь `max-height` + `overflow-y: auto` именно на нём (не на родителе) |
| Visual ритм между блоками теряется после удаления `grid-auto-rows: 80px` | 5 | средняя | следить чтобы у chart-блоков одного типа был одинаковый `.h-md` (или `.h-lg`) — высота сохраняется через chart-tokens |
| Контент `<canvas>` без `<div class="chart-wrap">` обёртки потеряет высоту | 5 | средняя | при миграции каждого блока проверить наличие `<div class="chart-wrap">` вокруг canvas |
| `.cell-kpi` (KPI-карточки 2×2) останутся со старыми стилями | 5 | низкая | KPI — будущий Components v1.0, временно оставить `.cell-kpi` как есть до отдельной миграции |
| Замена 32 блоков и 37 .title-area вручную → ошибки | 5 | высокая | sed/grep по паттернам + ручная проверка после каждой группы (h4x6, h4x12, etc.) |

---

## Оценка времени

| Фаза | Время | Сложность |
|------|-------|-----------|
| Phase 0 — подготовка | 10 мин | тривиально |
| Phase 1 — typography v1.1 | 1 час *(часть уже сделана)* | средняя (grep+replace + удаление inline overrides) |
| Phase 2 — charts | 3-4 часа | высокая (25 графиков, разные паттерны) |
| Phase 3 — controls | 1-2 часа | средняя (CSS + HTML + JS) |
| Phase 4 — tables | 1 час | средняя (CSS + обёртки + удаление .tbl-compact) |
| Phase 5 — blocks | 3-4 часа | **высокая** (32 блока + 37 title-area + .cell → .block + grid рефакторинг) |
| Phase 6 — верификация | 30 мин | низкая (визуальный обход + grep) |
| **Итого** | **~10-12 часов** | |

**Рекомендация:** делать поэтапно с коммитом после каждой фазы. Phase 5 (Blocks) — самая объёмная и критичная, имеет смысл разбить на под-этапы:
- 5a. Грубая замена `.h4x6` → `.block.span-6.h-md` через sed (одна группа)
- 5b. Удаление `.title-area` обёрток вокруг h3+meta (требует ручной проверки)
- 5c. Удаление `.cell` обёрток вокруг chart-wrap
- 5d. Чистка CSS (удаление неиспользуемых правил)
- 5e. Проверка что нет regression в layout

Без Phase 5 (Blocks) типография v1.1 даёт частичный эффект — `.title-area` font-overrides и 80px-row продолжают портить визуал. **Phase 5 — самая важная для финального результата.**

---

## Что НЕ входит в эту миграцию

- **Цвета** (`design-system/colors/`) — будут позже, отдельный раздел спецификации
- **Spacing** (`design-system/spacing/`) — позже
- **Components** (KPI-карточки, таблицы, sticky-header) — позже
- **Архитектура `generate_report.py`** — рефакторинг функций, разбиение на модули — отдельная задача
- **`update_analytics.py`** (Google Sheets) — не относится к визуалу

---

## После завершения

Дашборд работает на единой v1.0 системе. Следующие задачи становятся проще:
- Менять любой шрифт/размер/цвет/радиус — правишь токен, всё обновляется автоматически
- Добавлять новые графики — берёшь готовый пресет, не пишешь с нуля
- Делать новый дашборд (другой проект) — копируешь `design-system/`, готова стартовая точка
- Добавлять следующие разделы спецификации (colors, spacing) — встают на ту же архитектуру
