# Charts — v1.0

Раздел дизайн-системы про графики. Шесть типов графиков на Chart.js + datalabels-plugin, четыре стандартных форматтера, четыре пресета легенды, четыре ступени высоты, единый hover-mode, полное соответствие Typography v1.0.

**Зависит от:** [Typography v1.0](../typography/) (шрифт, размеры, веса).

## Шесть типов графиков

| Тип | Когда | Datalabels | Легенда |
|-----|-------|------------|---------|
| **Grouped Bar** | Воронка по периодам, динамика по каналам | Над столбиком (`barTop`) | Квадрат 10×10 |
| **Stacked Bar** | Композиция (доли) | Внутри сегмента (белым) с фильтром >30 | Квадрат 10×10 |
| **Combo (Bar+Line)** | Сессии-stack + покупатели-линия | Per-dataset: bar белым, line зелёным с фоном | Mixed: квадрат + линия |
| **Line** | % конверсии, тренды | Над точкой (с фоном) | Короткая линия 32×2 |
| **Bubble** | Объём × конверсия × размер | Имя source у пузыря (с фоном, clamped) | Круг 10×10 |
| **Sparkline** | Мини-тренды в KPI | Только min/max (10px) + лёгкая сетка | Нет |

## Четыре форматтера

```js
const fmt = {
    num: (v)         => (v == null || v === 0) ? '' : v.toLocaleString('ru-RU'),    // 12 845
    pct: (v, dec=1)  => (v == null || v === 0) ? '' : v.toFixed(dec) + '%',         // 12.4%
    sec: (v)         => (v == null || v === 0) ? '' : v + 's',                      // 31s
    cur: (v, c='$')  => (v == null || v === 0) ? '' : c + v.toLocaleString('ru-RU') // $630
};
```

Все автоматически скрывают `0` и `null`. Локаль `ru-RU` для разделителя тысяч.

## Четыре ступени высоты

```css
:root {
    --ch-xs: 60px;   /* sparkline */
    --ch-sm: 180px;  /* слайдер-карточки */
    --ch-md: 280px;  /* стандартный график */
    --ch-lg: 360px;  /* детализированный */
}
```

## Hover-pattern

Глобально через `Chart.defaults.interaction = { mode: 'index', intersect: false }`. Наводишь на любую x-позицию → видишь значения ВСЕХ датасетов в этом периоде сразу. Для bubble переопределяется на `{ mode: 'point', intersect: true }`.

## Соответствие Typography v1.0

- Datalabels: `--fs-caption` (11px) / regular
- Оси и легенда: `--fs-chart-meta` (10px) / regular
- Sparkline min/max: `--fs-chart-meta` (10px) / regular
- Шрифт: `'Ubuntu Mono'` через `Chart.defaults.font.family`

**Никаких `weight: 'bold'`** в чарт-конфигах. Выделение через цвет, не через толщину.

## Цветовая логика

Только через токены, никаких inline hex:
- **channel** — Social, Paid, Direct, Organic, Referral, Email
- **funnel** — home, catalog, product, ATC, checkout, purchase
- **semantic** — growth, decline, neutral, highlight (для дельт, sparkline по тренду)

## Файлы

| Файл | Для кого / зачем |
|------|------------------|
| [`charts.html`](charts.html) | Открыть в браузере. Визуальная спецификация — живые Chart.js примеры всех 6 типов с их финальными настройками. |
| [`tokens.md`](tokens.md) | Прочитать на спокойную голову. Полная текстовая спецификация: пресеты, паттерны tooltip, инструкция применения. |
| [`tokens.json`](tokens.json) | Импортировать в код. Машиночитаемая версия — для сборщиков/скриптов. |

## Важно: регистрация плагина datalabels

В **Chart.js v4** плагин `chartjs-plugin-datalabels` НЕ авто-регистрируется при подключении через CDN. Нужно явно:

```js
Chart.register(ChartDataLabels);
```

Без этой строки `options.plugins.datalabels` просто игнорируются — datalabels не отображаются.

## Применение в новом проекте

В четыре шага: подключить Chart.js + datalabels плагин, применить Typography v1.0, настроить `Chart.defaults` один раз, использовать пресеты из спецификации. Подробнее — [`tokens.md → Применение в новом проекте`](tokens.md#применение-в-новом-проекте).
