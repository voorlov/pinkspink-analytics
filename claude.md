# Pinkspink — GA4 Analytics Project

## Контекст
- **Бренд:** Pinkspink (одежда, Shopify e-commerce)
- **Google Email:** voorlov@gmail.com
- **GA4 Property ID:** 411715710
- **Google Cloud Project ID:** claude-code-486108
- **BigQuery Dataset:** analytics_411715710
- **Данные в BigQuery:** с 5 февраля 2026, таблицы `events_YYYYMMDD`

## Ресурсы
- **Google Sheets:** https://docs.google.com/spreadsheets/d/1BJlK5UDgikDzszMFnrIFKtnvqoiTefgpvqkRieAbciw/edit
- **Looker Studio:** https://lookerstudio.google.com/reporting/5d23fafe-7f4d-4831-8cdb-b74d06bc4836 (начат, но заменяется на HTML-дашборд)
- **BigQuery:** `claude-code-486108.analytics_411715710.events_*`

## Архитектура

### Основная (HTML-дашборд — в разработке)
```
GA4 → BigQuery (daily export) → generate_report.py → HTML (report_week.html)
                                                    → GitHub Pages (планируется)
                                                    → GitHub Actions (ежедневно + еженедельно)
```

### Вспомогательная (Google Sheets — работает)
```
GA4 → BigQuery → update_analytics.py → Google Sheets (11 вкладок)
```

## Файловая структура
```
google analitics/
├── generate_report.py       # HTML-дашборд генератор (основной)
├── update_analytics.py      # Google Sheets обновление (вспомогательный)
├── setup_looker.py          # Looker Studio утилиты (устаревает)
├── looker_sql/              # SQL для Looker Studio (устаревает)
│   ├── funnel_daily.sql     # Unified SQL (channel/source/funnel/engagement)
│   ├── funnel_stages.sql    # Воронка в вертикальном формате
│   ├── sessions_daily.sql   # Сессии с метриками
│   └── transactions.sql     # Транзакции
├── design-system/           # Дизайн-система (источник правды для UI)
│   ├── README.md            # Главное оглавление, статусы версий
│   ├── MIGRATION.md         # План миграции дашборда (фазы 0-4, выполнен)
│   ├── typography/          # v1.1: 6 fs-токенов, 3 веса, heading-spacing
│   ├── charts/              # v1.0: 6 типов графиков, helpers, presets
│   └── controls/            # v1.0: .btn / .btn-sq / .tab / .check / .filter-*
├── report_week.html         # Сгенерированный HTML-отчёт (понедельный)
├── report_day.html          # Сгенерированный HTML-отчёт (дневной)
├── report_month.html        # Сгенерированный HTML-отчёт (месячный)
├── styleguide.html          # Визуальный референс дизайн-системы
├── requirements.txt         # Python зависимости
├── service_account.json     # GCP credentials (НЕ в git!)
├── .gitignore
├── Code.gs                  # Архивный Apps Script (НЕ ИСПОЛЬЗУЕТСЯ)
├── claude.md                # Этот файл
├── new-solution.md          # Архивные заметки
└── venv/                    # Python 3.9.6 виртуальное окружение

## Дизайн-система (v1.0 + Typography v1.1)

Дашборд переведён на Design System (см. `design-system/`). **Все стили, размеры, веса, цвета — через CSS-токены `var(--…)`. Никакого хардкода.**

- **Typography v1.1**: 6 размеров (`--fs-kpi 28 / --fs-h2 18 / --fs-h3 14 / --fs-body 13 / --fs-caption 11 / --fs-chart-meta 10`), 3 веса (`--fw-regular/semibold/bold`), heading-spacing (`--mt-h2 44 / --mt-h3 24 / --mt-h4 16 / --tight-pair 4 / --content-gap 8`), глобальный `body { line-height: 1.25 }`, фикс `* { font-family: inherit }` для form-элементов.
- **Charts v1.0**: `Chart.register(ChartDataLabels)` + Chart.defaults на старте, helpers (`cssvar`, `fmt {num/pct/sec/cur}`, `dlPad`, `legendLabels`, `legendPresets {bar/line/bubble/mixed/none}`, `dlPresets {barTop/barCenter/line/off}`), 4 ступени высоты (`--ch-xs/sm/md/lg`), `interaction: { mode: 'index', intersect: false }` глобально (override per-chart для bubble), `maxBarThickness: 40` на bar-датасетах.
- **Controls v1.0**: `--h-control 28px`, `--r-control 2px`, компоненты `.btn` / `.btn-sq` / `.tab` / `.check` / `.filter-bar` / `.filter-group` / `.tab-bar`. Активное состояние — через `.is-active` (НЕ `grain-active` / `tab-active` — устаревшие).

**Инвариант:** при добавлении новых компонентов или графиков — брать готовый пресет/токен. Если нужно нечто, чего нет в дизайн-системе — обновляется `design-system/<раздел>/tokens.md` сначала, потом применяется в `generate_report.py`.

**MIGRATION.md** — план перевода дашборда на v1.0/v1.1, все 4 фазы (Typography → Charts → Controls → cleanup) выполнены 2026-04-29.
```

## HTML-дашборд (`generate_report.py`)

### Что делает
Забирает данные из BigQuery, генерирует standalone HTML с Chart.js графиками.

### Запуск
```bash
source venv/bin/activate
python generate_report.py                # понедельный (по умолчанию)
python generate_report.py --grain day    # дневной (14 дней)
python generate_report.py --grain month  # месячный
python generate_report.py --grain all    # все три файла
```

### Структура отчёта (страница "Воронки")

**Фильтры (верх страницы):**
- Grain: день / неделя / месяц (переключатель между файлами)
- Исключённые страны: China, Hong Kong, South Korea, Singapore (наш трафик)

**Переключатель Мобилка / Веб** (влияет на все блоки ниже)

**Блок 1: Динамика воронок** (два графика: Мобилка + Веб)
- Grouped bar chart: homepage → catalog → product → ATC → checkout → purchase по неделям

**Блок 2: Динамика мобильной воронки по каналам** (горизонтальный слайдер)
- Карточки: Social, Paid, Direct, Organic, Referral
- В каждой: график воронки, метрики за текущую неделю (сессии, доля, ER, median sec, глубина 2+, ср. карточек)
- Дельты: сравнение с средним за 4 предыдущие недели
- Топ-5 стран (с флагами 🇯🇵🇺🇸)

**Блок 3: Динамика по source** (горизонтальный слайдер)
- Топ-5 source (ig, meta (paid), (direct), google, l.instagram.com)
- Содержимое аналогично блоку 2

**Блок 4: Таблица "Кто добавляет в корзину и покупает"**
- Строки: source + страна, где были ATC/checkout/purchase
- Сортируемая по клику на заголовок
- Период: последняя полная неделя

**Блок 5: Эффективность source** (горизонтальный слайдер бабл-чартов)
- 4 графика: Каталог→Товар, Товар→Корзина, Корзина→Чекаут, Чекаут→Покупка
- X = сессии на этом этапе, Y = конверсия в следующий, размер = сессии
- Чекбоксы для скрытия отдельных source
- Зоны: зелёный (высокая конверсия) / жёлтый / красный (низкая)

**Блок 6: Эффективность по странам** (аналогично блоку 5)
- Топ-10 стран по сессиям, флаги в подписях

### Иерархия каналов (channel)
```
channel (Level 1)          source (Level 2)
├── Social                 ig, l.instagram.com
├── Paid                   meta (paid) — все medium: paid, cpm, Instagram_Feed, Facebook_Right_Column и т.д.
├── Direct                 (direct)
├── Organic                google, bing, yahoo, ecosia.org
├── Referral               facebook, facebook.com, m.facebook.com, jp.pinkspink.company
├── Email                  omnisend
├── Spam (исключён)        api.scraperforce.com, sanganzhu.com, jariblog.online
└── Other                  всё остальное
```

### Воронка (page-based + event-based)
```
Homepage    — page_path = /(ja|ru)?/?$
Catalog     — page_path содержит /collections/ (без /products/)
Product     — event: view_item
Add to Cart — event: add_to_cart
Checkout    — event: begin_checkout
Purchase    — event: purchase
```

### Исключённые страны (наш трафик)
China, Hong Kong, South Korea, Singapore — выбраны потому что владельцы подключаются из этих стран (VPN из Кореи, живут в Китае и т.д.)

## Google Sheets (`update_analytics.py`)

### Вкладки (11 штук)
1. **Daily Overview** — сессии, users, ER, медианное время, avg pages, глубина (1/2-5/>5), доход (90 дней)
2. **Funnel Overview** — общая воронка: Sessions→View Item→ATC→Checkout→Purchase
3. **Funnel by Source** — воронка по каналам + поведенческие метрики
4. **Funnel Weekly** — понедельная воронка по каналам
5. **Product Views Weekly** — среднее/медианное кол-во просмотренных карточек
6. **Traffic Sources** — каналы + source/medium
7. **Top Products** — 50 товаров с метриками
8. **Top Pages** — 50 страниц с конверсиями
9. **Devices & Geo** — устройства + топ-20 стран
10. **Retention** — new vs returning
11. **Transactions** — все транзакции за всё время (без фильтров)

### Запуск
```bash
source venv/bin/activate
python update_analytics.py              # все вкладки
python update_analytics.py daily        # только Daily Overview
python update_analytics.py funnel       # Funnel Overview + by Source + Weekly + Product Views
python update_analytics.py traffic products pages geo retention transactions
```

### Настройки
- `DEFAULT_DAYS = 90` (период для всех вкладок кроме Transactions и Funnel)
- `EXCLUDED_COUNTRIES = ["China", "Hong Kong", "Kazakhstan", "Russia"]` (для Sheets, отличается от HTML)
- Transactions — без фильтров (все страны, все даты)
- Funnel Overview — без фильтра по дате, с фильтром по странам

## ⚠ ВАЖНО: service_account.json
- Файл НЕ коммитится в git (в .gitignore)
- Сервисный аккаунт: `analytics-dashboard@claude-code-486108.iam.gserviceaccount.com`
- Роли: **BigQuery Data Viewer** + **BigQuery Job User** (НЕ может создавать views)
- Google Sheets расшарена на email сервисного аккаунта (editor)

## Ключевые бизнес-инсайты (из анализа)

### Трафик
- **Social (Instagram)** — 56% трафика, лучшее вовлечение (31s median, 3.5 стр)
- **Paid (Meta Ads)** — 15% трафика, bounce 85%, median 12s, конверсия 0.3%. Реклама неэффективна
- **Direct** — 24% трафика, стабильное вовлечение
- **Organic** — 2.5%, но лучший ER (69%)

### Воронка
- Критическая потеря: View Item → Add to Cart (98% отваливаются)
- Большинство мобильных пользователей заходят сразу в каталог (64%), минуя главную (7%)
- Desktop конвертируется в корзину в 2.7x лучше чем mobile

### География
- Japan — основной рынок (реклама + органика)
- USA — второй по объёму
- Европа (Germany, Netherlands, Finland) — высокая вовлечённость, растёт

### Единственная покупка
- Казахстан, 6 февраля 2026, $630, через Instagram (ig/social), мобилка

## Оформление HTML-дашборда
- Шрифт: Ubuntu Mono
- Цвета каналов: Social=#6C5CE7, Direct=#636E72, Paid=#00B894, Organic=#0984E3, Referral=#FDCB6E, Email=#E17055
- Цвета воронки: home=#636E72, catalog=#2D3436, product=#6C5CE7, ATC=#FDCB6E, checkout=#74B9FF, purchase=#00B894
- Флаги стран в подписях (🇯🇵🇺🇸🇩🇪 и т.д.)

## TODO
- [x] BigQuery Export — данные приходят
- [x] service_account.json — настроен
- [x] update_analytics.py на BigQuery — работает (11 вкладок)
- [x] requirements.txt, .gitignore, venv
- [x] Новая иерархия каналов (channel: Social/Paid/Direct/Organic/Referral/Email/Spam)
- [x] HTML-дашборд (generate_report.py) — страница "Воронки" работает
- [x] Looker Studio — начат, но решение заменено на HTML-дашборд
- [ ] **HTML-дашборд: доработка**
  - [ ] Доработать вёрстку (графики, бабл-чарты)
  - [ ] Добавить блок "Веб" (сейчас заглушка)
  - [ ] Добавить страницу "Трафик" (общая картина по каналам/странам/устройствам)
  - [ ] Добавить AI-выводы (текстовые рекомендации)
- [x] **Автоматизация**
  - [x] GitHub репо `voorlov/pinkspink-analytics` (public — нужно для бесплатного Pages)
  - [x] GitHub Actions — `build-dashboard.yml` cron 06:00 UTC (HTML) + `ai-reports.yml` cron daily/weekly (AI)
  - [x] GitHub Pages — https://voorlov.github.io/pinkspink-analytics/
  - [x] AI-отчёты через GitHub Actions + Anthropic API → Telegram
- [ ] Подключить Facebook Ads API (расходы, ROAS)
- [ ] Подключить email-маркетинг (Omnisend)

## Автоматизация — как устроено

**Track A — HTML-дашборд:**
- Workflow: `.github/workflows/build-dashboard.yml`, cron `0 2 * * *` UTC (10:00 Пекин / 05:00 МСК) + кнопка Run workflow.
- Запускает `python generate_report.py --grain all`, копирует HTML в `docs/`, коммитит и пушит.
- GitHub Pages раздаёт `docs/` по адресу https://voorlov.github.io/pinkspink-analytics/.
- Репо публичный (бесплатный план GitHub не поддерживает Pages на приватных репо). Данные — агрегатная аналитика без PII.

**Track B — AI-отчёты:**
- Workflow: `.github/workflows/ai-reports.yml`. Два cron в UTC: `0 2 * * *` (daily) и `0 2 * * 1` (weekly понедельник). Это 10:00 Пекин / 05:00 МСК. По понедельникам сработают оба run одновременно (daily за вчерашний день + weekly за прошлую неделю). Также workflow_dispatch для ручного запуска.
- Скрипт: `scripts/ai_report.py --grain daily|weekly`.
  1. BigQuery: подтягивает session-level метрики за нужный период (yesterday + trailing-7d, или прошлая неделя + 4 предыдущие).
  2. Aggregate: каналы, страны, девайсы, ATC rate, View→ATC, etc.
  3. Загружает контент скилла (`SKILL.md` + `references/*.md`) как system prompt.
  4. Зовёт Anthropic API (model: `claude-sonnet-4-6`) с pre-computed JSON-данными.
  5. Сохраняет markdown в `reports/{daily,weekly}/YYYY-*.md`, коммитит и пушит.
  6. POST в Telegram через Bot API (с chunking >4096 символов).
- Telegram bot: `@pink_analitics_bot`.
- Секреты в GitHub: `GCP_SERVICE_ACCOUNT_JSON`, `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Локально: `.env.routine` (gitignored) хранит Telegram-учётки на случай ad-hoc прогона `python scripts/ai_report.py`.

**Ограничение weekly-автоотчёта:** скрипт не делает "exploratory pass" и "audience expansion screen" из скилла — для этих секций нужны ad-hoc BigQuery-запросы по решению модели, а в Actions модель работает с pre-computed данными. Эти секции отчёт помечает как «требует ad-hoc запроса в Claude Code». Для глубокого weekly-анализа — запросить вручную в Claude Code, скилл подцепится.

**Файл `routine-prompt.md`** — устарел (был под /schedule с BigQuery MCP, который оказался недоступен на cloud-стороне). Можно удалить или оставить как референс если когда-то добавим BigQuery MCP в claude.ai connectors.

## Changelog — `changelog.md`

Лог сделанного, что может повлиять на метрики (правки сайта, навигация, IG-посты, рекламные кампании, email-рассылки). При появлении новой записи AI-отчёты автоматически её увидят:
- daily-промпт включает записи за последние **14 дней**
- weekly-промпт — за последние **60 дней**

Это включено в `scripts/ai_report.py` через функцию `load_recent_changelog()`. Модель использует записи для confounder-чека: если метрика двинулась после конкретного изменения, AI явно свяжет одно с другим в отчёте.

**Как добавлять:** одной строкой в файл `changelog.md`, формат `- **YYYY-MM-DD** — описание.` Изменение видно в следующем daily/weekly прогоне без перезапуска.
