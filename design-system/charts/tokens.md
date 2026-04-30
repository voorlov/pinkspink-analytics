# Charts Tokens — v1.0

Спецификация графиков для аналитических дашбордов на Chart.js. Шесть типов графиков, четыре стандартных форматтера, четыре пресета легенды, четыре ступени высоты, единые правила hover, цветовая логика. Источник правды — [`tokens.json`](tokens.json). Визуальный референс — [`charts.html`](charts.html).

**Зависимости:** Typography v1.0 (все размеры и веса оттуда).

---

## Библиотека

| Параметр | Значение |
|----------|----------|
| Core | Chart.js 4.4 |
| Plugins | chartjs-plugin-datalabels 2.2 |
| Регистрация | `Chart.register(ChartDataLabels);` (обязательно для v4 — плагин не авто-регистрируется) |

---

## Глобальная настройка (Chart.defaults)

Запускается один раз при загрузке страницы. Все графики наследуют:

```js
// === Chart.js global setup ===
Chart.register(ChartDataLabels);

// Шрифт и базовый цвет
Chart.defaults.font.family = "'Ubuntu Mono', monospace";
Chart.defaults.color       = '#636E72';  // --tx-secondary

// Размеры (из Typography v1.0)
Chart.defaults.font.size                  = 10;            // --fs-chart-meta (оси)
Chart.defaults.plugins.legend.labels.font = { size: 10 };  // --fs-chart-meta (легенда)
Chart.defaults.plugins.datalabels         = Chart.defaults.plugins.datalabels || {};
Chart.defaults.plugins.datalabels.font    = { size: 11 };  // --fs-caption (datalabels)

// Сетка — едва заметная
Chart.defaults.scale.grid.color = 'rgba(0,0,0,0.06)';

// Hover: при наведении показываются ВСЕ значения в этой x-позиции
Chart.defaults.interaction = { mode: 'index', intersect: false };
// (для bubble переопределяется per-chart на { mode: 'point', intersect: true })
```

---

## Форматтеры — четыре функции

Все автоматически скрывают `0` и `null`. Локаль `ru-RU` для разделителя тысяч (12 845).

```js
const fmt = {
    num: (v)         => (v == null || v === 0) ? '' : v.toLocaleString('ru-RU'),  // 12 845
    pct: (v, dec=1)  => (v == null || v === 0) ? '' : v.toFixed(dec) + '%',       // 12.4%
    sec: (v)         => (v == null || v === 0) ? '' : v + 's',                    // 31s
    cur: (v, c='$')  => (v == null || v === 0) ? '' : c + v.toLocaleString('ru-RU') // $630
};
```

---

## Datalabel-пэд (полупрозрачный фон)

Применяется к Line, Combo (line-часть), Bubble — чтобы число/текст читался когда падает на цветную линию или пузырь:

```js
const dlPad = {
    backgroundColor: 'rgba(255,255,255,0.85)',
    borderRadius:    3,
    padding: { top: 1, bottom: 1, left: 4, right: 4 }
};
```

---

## Пресеты datalabel-позиций

| Имя | Когда | Конфиг |
|-----|-------|--------|
| `barTop` | Над столбиком в Grouped Bar | `anchor:'end' · align:'top' · color: --tx-primary` |
| `barCenter` | Внутри сегмента в Stacked Bar / Combo bar-часть | `anchor:'center' · align:'center' · color: --tx-ondark` (обычно с `display: ctx => v > 30` для скрытия мелких) |
| `line` | Над точкой на Line / Combo line-часть | `align:'top' · color: --tx-primary · ...dlPad` |
| `off` | Sparkline (только min/max), Bubble без лейблов | `display: false` |

---

## Пресеты легенды — четыре варианта

Все имеют `position: 'top'`, `align: 'start'` (выравнивание по левому краю).

| Пресет | Маркер | Используется в |
|--------|--------|----------------|
| `bar`    | Квадрат 10×10 | Grouped Bar, Stacked Bar |
| `line`   | Короткая линия 32×2 (≈2 квадрата) | Line чарт |
| `bubble` | Круг 10×10 | Bubble чарт |
| `mixed`  | Per-dataset: bar→квадрат 14×8, line→линия | Combo (Bar + Line) |
| `none`   | (нет) | Sparkline |

### Кастомная функция `legendLabels`

Нужна потому что Chart.js v4 рисует **точку** для line-датасетов вместо линии. Также нужна для смешанных combo-графиков, чтобы bar получил квадрат, а line — линию.

```js
function legendLabels(chart) {
    return chart.data.datasets.map((ds, i) => {
        const isLine = (ds.type === 'line') || (chart.config.type === 'line' && !ds.type);
        const color  = ds.borderColor || ds.backgroundColor;
        return {
            text:        ds.label,
            fillStyle:   color,
            strokeStyle: color,
            lineWidth:   isLine ? 2 : 0,
            pointStyle:  isLine ? 'line' : (chart.config.type === 'bubble' ? 'circle' : 'rect'),
            hidden:      !chart.isDatasetVisible(i),
            datasetIndex: i
        };
    });
}
```

---

## Высоты — четыре ступени

| Токен | Размер | Где |
|-------|--------|-----|
| `--ch-xs` | 60px | Sparkline в KPI-карточках (`.kpi-spark`) |
| `--ch-sm` | 180px | Графики в слайдер-карточках (компакт) |
| `--ch-md` | 280px | Стандартный график в `.cell` (default) |
| `--ch-lg` | 360px | Детализированные с осями + большая легенда |

```css
:root {
    --ch-xs: 60px;
    --ch-sm: 180px;
    --ch-md: 280px;
    --ch-lg: 360px;
}
```

**Правило:** контейнер графика получает `min-height: var(--ch-X); max-height: var(--ch-X);` — чтобы график не «дышал» при разных данных.

---

## Ширина баров — `maxBarThickness`

Решает «при малом числе периодов бары становятся жирными». На каждом dataset с `type: 'bar'`:

```js
{ type: 'bar', ..., maxBarThickness: 40, categoryPercentage: 0.8, barPercentage: 0.9 }
```

**Что делать когда баров слишком много** (например, 30 дней в day-grain):
- → Первый путь: переключатель grain (day/week/month) — пользователь жмёт «week» и получает 4-5 баров вместо 30
- → Второй путь (fallback): горизонтальный скролл контейнера. Применять только когда агрегация невозможна

---

## Шесть типов графиков

### A · Grouped Bar

Воронка по периодам, динамика по каналам/source.

| Параметр | Значение |
|----------|----------|
| Type | `bar` |
| Цвета | funnel или channel |
| Datalabels | `barTop` preset + `formatter: fmt.num` |
| Legend | `bar` preset |
| Y | `beginAtZero: true · grace: '15%'` |
| BarWidth | `maxBarThickness: 40` |

### B · Stacked Bar

Композиция (доли каналов в общем объёме).

| Параметр | Значение |
|----------|----------|
| Type | `bar` |
| Цвета | channel |
| Datalabels | `barCenter` preset + `display: ctx => v > 30` + `formatter: fmt.num` |
| Legend | `bar` preset |
| Scales | `x: { stacked: true }`, `y: { stacked: true, beginAtZero: true }` |
| Tooltip | `withShare` — значение + доля в % |

### C · Combo (Bar + Line, dual-axis)

Bar + Line на одном графике (например: сессии-stack + покупатели-линия).

**Настройка датасетов:**

```js
datasets: [
    { type: 'bar',  ..., stack: 's', yAxisID: 'y',  order: 2, maxBarThickness: 40 },
    { type: 'line', ..., yAxisID: 'y1', order: 0,
      borderWidth: 2, tension: 0.3,
      pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0 }
]
```

**Правило `order`:** чем БОЛЬШЕ — тем РАНЬШЕ рисуется (= уходит назад). Линии нужен МАЛЫЙ order (0) → рисуется последней → на переднем плане. Bar — БОЛЬШИЙ (2) → на заднем. Без явного order Chart.js может отрисовать линию ЗА барами.

**Datalabels per-dataset:**
- bars: `barCenter` preset + `display > 30` + `fmt.num`
- line: `{ anchor: 'end', align: 'top', offset: 6, color: 'var(--c-growth)', formatter: fmt.num, ...dlPad }` — без `weight: 'bold'`!

**Legend:** `mixed` preset (custom `generateLabels` — bar квадрат + line линия в одной легенде).

**Scales:** `y` слева (`stacked`), `y1` справа (`grid.drawOnChartArea: false`).

### D · Line

% конверсии (этапы воронки), тренды.

| Параметр | Значение |
|----------|----------|
| Type | `line` |
| Цвета | funnel или semantic |
| Dataset defaults | `borderWidth: 2 · tension: 0.3 · pointRadius: 4 · pointHoverRadius: 6 · pointBorderWidth: 0` |
| Datalabels | `line` preset (с `dlPad`) + `formatter: v => fmt.pct(v, 1)` |
| Legend | `line` preset (custom generateLabels) |
| Y | `beginAtZero: true · grace: '15%' · ticks.callback: v => v + '%'` |
| Tooltip | `customByFmt` — `ctx.dataset.label + ': ' + fmt.pct(ctx.parsed.y, 1)` |

### E · Bubble

Эффективность source/страны: объём × конверсия × размер.

| Параметр | Значение |
|----------|----------|
| Type | `bubble` |
| Цвета | channel (по source) |
| Datalabels | `{ anchor: 'end', align: 'right', offset: 6, clamp: true, color: 'var(--tx-primary)', formatter: (v, ctx) => ctx.dataset.label, ...dlPad }` |
| Legend | `bubble` preset (круг 10×10) |
| Interaction | `{ mode: 'point', intersect: true }` (override global 'index') |
| Layout padding | `{ top: 16, right: 32, bottom: 4, left: 4 }` (место для лейблов у краёв) |
| X | `title: 'Сессии'` |
| Y | `title: 'Конверсия %'`, `ticks: v => v + '%'` |
| Tooltip | `twoDimensions` — `label + ': ' + fmt.num(p.x) + ' сес. → ' + fmt.pct(p.y, 1)` |

### F · Sparkline

Мини-тренды в KPI-карточках. «Тренд глазом», без интерактива.

| Параметр | Значение |
|----------|----------|
| Type | `line` |
| Цвета | channel или semantic (по тренду — рост → growth, падение → decline) |
| Dataset defaults | `borderWidth: 1.5 · tension: 0.4 · pointRadius: 0 · fill: false` |
| Min/max labels | font 10 / regular, color: max=growth · min=decline, align: max='top' · min='bottom', offset: 4, formatter: fmt.num |
| Min/max points | `pointRadius: 2.5` только в min/max (через ctx-функцию) |
| X axis | `display: true · grid: 'rgba(0,0,0,0.06)' · ticks: false · border: false` (лёгкая вертикальная сетка) |
| Y axis | `display: false` |
| Tooltip | `false` |
| Legend | `false` |
| Container height | 100px (с min/max метками) или `--ch-xs` 60px (без меток) |
| Layout padding | `{ top: 14, bottom: 20, left: 4, right: 18 }` |

---

## Tooltip-паттерны

### `withShare` — для Stacked Bar

```js
tooltip: { callbacks: { label: ctx => {
    const total = ctx.chart.data.datasets.reduce((s, d) => s + (d.data[ctx.dataIndex] || 0), 0);
    const share = total > 0 ? (ctx.parsed.y / total * 100).toFixed(1) : 0;
    return ctx.dataset.label + ': ' + fmt.num(ctx.parsed.y) + ' (' + share + '%)';
}}}
```

### `customByFmt` — для Line с %

```js
tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmt.pct(ctx.parsed.y, 1) } }
```

### `twoDimensions` — для Bubble

```js
tooltip: { callbacks: { label: ctx => {
    const p = ctx.raw;
    return ctx.dataset.label + ': ' + fmt.num(p.x) + ' сес. → ' + fmt.pct(p.y, 1);
}}}
```

---

## Цветовая логика

Все цвета на графиках берутся **только из токенов** (Color v1.0 когда будет создан, или Python-словарей `CHANNEL_COLORS` / `FUNNEL_STAGES`). **Никаких inline hex.**

| Тип датасета | Источник цветов |
|--------------|-----------------|
| Каналы (Social, Paid, Direct, Organic, Referral, Email) | channel-палитра |
| Этапы воронки (home, catalog, product, ATC, checkout, purchase) | funnel-палитра |
| Дельты (рост/падение/нейтрал), sparkline по тренду, акценты | semantic-палитра (growth, decline, neutral, highlight) |

---

## Соответствие Typography v1.0

Все размеры и веса берутся из шкалы типографики — никаких новых значений:

| Что | Размер | Вес | Где задано |
|-----|--------|-----|-----------|
| Datalabels (значения, source-имена на пузырях) | `--fs-caption` 11px | regular (400) | `Chart.defaults.plugins.datalabels.font.size = 11` |
| Подписи осей и легенды | `--fs-chart-meta` 10px | regular (400) | `Chart.defaults.font.size = 10` |
| Sparkline min/max | `--fs-chart-meta` 10px | regular (400) | per-chart override |
| Шрифт | `'Ubuntu Mono'` | — | `Chart.defaults.font.family` |

**Правило:** никаких `font: { weight: 'bold' }` в чарт-конфигах. Если хочется выделить — используем **цвет** (`--c-growth`, `--tx-ondark`, `--c-decline`), не толщину.

---

## Применение в новом проекте

### Шаг 1. Подключить Chart.js + datalabels-plugin

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
```

### Шаг 2. Применить Typography v1.0 (см. соседнюю папку)

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Ubuntu+Mono:wght@400;700&display=swap">
<style>
:root {
    --ff-mono: 'Ubuntu Mono', monospace;
    --fs-caption: 11px;
    --fs-chart-meta: 10px;
    /* ... остальное из Typography v1.0 ... */
    --ch-xs: 60px; --ch-sm: 180px; --ch-md: 280px; --ch-lg: 360px;
}
* { font-family: inherit; }
</style>
```

### Шаг 3. Настроить Chart.defaults один раз (см. секцию выше)

### Шаг 4. Для каждого графика — взять подходящий пресет из этой спецификации

См. раздел «Шесть типов графиков». В каждом — готовые `datalabels`, `legend`, `scales`.

### Шаг 5. Цвета — через токены

```js
const cssvar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
// ...
backgroundColor: cssvar('--c-channel-social'),  // не '#6C5CE7'
```

---

## Совместимость с Typography v1.1

Typography v1.1 добавил глобальный `body { line-height: 1.25 }`. **Charts v1.0 совместим без изменений** — графики рендерятся в `<canvas>` через Chart.js со своей font-системой. **Body line-height на canvas не влияет**.

| Что | Где задаётся | Влияет body line-height? |
|-----|--------------|--------------------------|
| Datalabels (значения над/в столбиках) | `Chart.defaults.plugins.datalabels.font` (canvas) | Нет |
| Подписи осей (X/Y ticks) | `Chart.defaults.font` (canvas) | Нет |
| Текст легенды | `Chart.defaults.plugins.legend.labels.font` (canvas) | Нет |
| `.chart-wrap` | div-контейнер без текста | Не критично |

Если потребуется управлять line-height в чартах — Chart.js поддерживает `Chart.defaults.font.lineHeight` (по умолчанию 1.2). На v1.0 спеке не задаём — Chart.js сам управляет vertical metrics адекватно.

## История версий

- **v1.0 · 2026-04-28** — старт. 6 типов графиков, 4 форматтера, 4 пресета легенды, 4 ступени высоты, правила barWidth, sparkline с min/max и сеткой, общий hover-mode 'index', полное соответствие Typography v1.0.
- **v1.0 совместим с Typography v1.1** (2026-04-29) — никаких правок не требуется. Canvas-рендеринг независим от body line-height.
