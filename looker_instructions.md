# Настройка Looker Studio — Ping Spinning Analytics

## Шаг 1: Создать отчёт

1. Открой https://lookerstudio.google.com
2. Войди аккаунтом **voorlov@gmail.com**
3. Нажми **+ Create** → **Report** (пустой отчёт)

## Шаг 2: Добавить источники данных

Для каждого из 3 источников повтори:

1. **Add data** (панель справа, или меню Resource → Manage added data sources → Add a data source)
2. Выбери **BigQuery**
3. Выбери **Custom Query**
4. Project: **claude-code-486108**
5. Вставь SQL из соответствующего файла (см. ниже)
6. Нажми **Add** → **Add to report**

### Источник 1: Funnel Daily
- Файл: `looker_sql/funnel_daily.sql`
- Назови источник: **Funnel Daily**
- Быстрое копирование: `python setup_looker.py --copy funnel_daily`

### Источник 2: Sessions Daily
- Файл: `looker_sql/sessions_daily.sql`
- Назови источник: **Sessions Daily**
- Быстрое копирование: `python setup_looker.py --copy sessions_daily`

### Источник 3: Transactions
- Файл: `looker_sql/transactions.sql`
- Назови источник: **Transactions**
- Быстрое копирование: `python setup_looker.py --copy transactions`

## Шаг 3: Добавить фильтры

Перетащи на холст (Insert → Filter control):

1. **Date range control** — привязать к полю `date`
2. **Drop-down filter** → поле `traffic_source` (Paid Ads / Instagram Japan / Instagram Other / Other)
3. **Drop-down filter** → поле `country`

Эти фильтры будут работать на все графики на странице.

## Шаг 4: Создать графики

### Страница 1: Воронка

**График 1 — Воронка (Bar chart)**
- Data source: Funnel Daily
- Dimension: `stage` (сортировка по `stage_order`)
- Metric: `users` (SUM)
- Тип: Horizontal bar chart
- Это покажет: Sessions → View Item → Add to Cart → Checkout → Purchase

**График 2 — Воронка по источникам (Stacked bar)**
- Data source: Funnel Daily
- Dimension: `stage` (sort by `stage_order`)
- Breakdown dimension: `traffic_source`
- Metric: `users` (SUM)

**График 3 — Динамика воронки (Time series)**
- Data source: Funnel Daily
- Dimension: `week` или `month`
- Breakdown dimension: `stage`
- Metric: `users` (SUM)
- Покажет тренды: растёт ли конверсия неделю к неделе

### Страница 2: Поведение

**График 4 — Сессии по источникам (Time series)**
- Data source: Sessions Daily
- Dimension: `date`
- Breakdown: `traffic_source`
- Metric: `sessions` (SUM)

**График 5 — Медианное время (Scorecard или bar chart)**
- Data source: Sessions Daily
- Dimension: `traffic_source`
- Metric: `median_eng_sec` (AVG)

**График 6 — Глубина просмотра (Stacked bar)**
- Data source: Sessions Daily
- Dimension: `traffic_source`
- Metrics: `sessions_1page`, `sessions_2_5pages`, `sessions_over5pages` (SUM)

### Страница 3: Транзакции

**Таблица транзакций**
- Data source: Transactions
- Dimensions: `date`, `transaction_id`, `traffic_source`, `country`, `device`
- Metrics: `revenue`, `items`

## Полезные советы

- **Переключение неделя/месяц**: используй фильтр Date range + dimension `week` или `month` в графике
- **Сравнение периодов**: Date range control → включи "Comparison date range"
- **Автообновление**: данные тянутся из BigQuery в реальном времени, кэш по умолчанию 12 часов
- **Поделиться**: File → Share → добавь email или скопируй ссылку

## Утилиты

```bash
# Проверить что SQL работает:
python setup_looker.py

# Скопировать SQL в буфер обмена:
python setup_looker.py --copy funnel_daily
python setup_looker.py --copy sessions_daily
python setup_looker.py --copy transactions
```
