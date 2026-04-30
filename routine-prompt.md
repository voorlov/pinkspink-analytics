# Routine prompt — для `/schedule` в Claude Code

Готовые промпты для трёх routines: ежедневный, еженедельный, ежемесячный. Скопируй нужный, запусти `/schedule` в проекте.

Routine выполняется на серверах Anthropic (Pro: до 5/день, Max: до 15/день). Daily + weekly + monthly = максимум 3 запуска в самый загруженный день, запас есть.

---

## Подготовка перед первым `/schedule` запуском

1. В корне репо должен лежать `.env.routine` со строками:
   ```
   TELEGRAM_BOT_TOKEN=<token из @BotFather>
   TELEGRAM_CHAT_ID=<твой chat_id>
   ```
   Этот файл в `.gitignore`, не коммитится.
2. Убедись что папки `reports/{daily,weekly,monthly}/` существуют.
3. Скилл `pinkspink-analytics-coach` должен быть в `.claude/skills/` (уже там).
4. BigQuery MCP должен быть подключён к проекту claude-code-486108.

---

## Daily routine — каждый день в 09:00 МСК

```
Запусти skill pinkspink-analytics-coach. Сегодня daily report.

Шаги:
1. Через BigQuery MCP (dataset claude-code-486108.analytics_411715710) подтяни 
   данные за вчера и за trailing 7 days (предыдущие 7 полных дней).
2. Применяй стандартные фильтры из skill: исключи страны China/Hong Kong/South Korea/
   Singapore, исключи Spam-каналы.
3. Сравни вчерашние ключевые метрики (сессии, ATC rate, новые/вернувшиеся, 
   доля каналов, top-3 страны) с trailing-7-day average.
4. По правилам из references/metrics-playbook.md определи, есть ли значимые 
   движения (small-sample floors!). Если нет — отчёт в одну строку "спокойный день".
5. Сгенерируй daily report по шаблону из references/report-template.md (≤300 слов, 
   на русском).
6. Сохрани отчёт в reports/daily/YYYY-MM-DD.md (относительно корня репо).
7. Закоммить файл в git: 
     git add reports/daily/YYYY-MM-DD.md
     git commit -m "daily report YYYY-MM-DD"
     git push
8. Опубликуй текст отчёта в Telegram через прямой вызов Bot API. Загрузи token и 
   chat_id из файла .env.routine в корне репо:
     source .env.routine
     curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
       -d "chat_id=${TELEGRAM_CHAT_ID}" \
       --data-urlencode "text=$(cat reports/daily/YYYY-MM-DD.md)" \
       --data-urlencode "parse_mode=Markdown"
   Если сообщение длиннее 4096 символов (лимит Telegram) — разбей на части по 
   абзацам, отправь несколько раз.

Если данных за вчера в BigQuery ещё нет (export задерживается до 24ч) — повтори 
запрос через 1 час. Если и через час нет — отправь в Telegram отдельное сообщение 
"Данные за [дата] не доступны, отчёт пропущен".
```

Каденс: `0 9 * * *` (каждый день в 9 утра по МСК).

---

## Weekly routine — каждый понедельник в 10:00 МСК

```
Запусти skill pinkspink-analytics-coach. Сегодня weekly report.

Шаги:
1. Через BigQuery MCP подтяни данные за прошлую полную ISO-неделю (Пн-Вс) и за 
   4 предыдущие полные недели.
2. Применяй стандартные фильтры из skill.
3. По всем трём вкладкам дашборда (Сводка / Воронки / Карточка товара) сравни 
   неделю vs avg(4 предыдущих недель). Это та же логика, что в самом дашборде.
4. Особое внимание: View→ATC mobile, Paid bounce/median, новые входы в top-10 стран, 
   изменения в Топ-30 карточек.
5. Применяй small-sample rules. Не выдумывай инсайты.

6. Exploratory-проход (обязательно). Выбери 3 среза из 
   references/exploration-patterns.md §1 (роттируй каждую неделю — не повторяй 
   те же три, что в прошлый раз). Запусти SQL под каждый. Найденные outlier'ы 
   входят в раздел "Что я исследовал за пределами дашборда".

7. Audience expansion screen (обязательно). Запусти шаблон S2 из 
   exploration-patterns.md (city × country с метриками качества). Найди все 
   сегменты с индексом ≥1.5× от site-wide. Прогони каждый через confounder-чек 
   (§2 того же файла).

8. Confounder screen для всех значимых аномалий. Если нужен ответ от пользователя 
   для подтверждения — сформулируй короткий вопрос на русском в разделе 
   "Гипотезы и проверка confounders".

9. Сгенерируй weekly report по шаблону из references/report-template.md (≤700 слов, 
   на русском). Включай до 3 рекомендаций (formula из 
   references/recommendations-library.md).
10. Сохрани отчёт в reports/weekly/YYYY-Www.md
11. Закоммить и запушь:
     git add reports/weekly/YYYY-Www.md
     git commit -m "weekly report YYYY-Www"
     git push
12. Опубликуй в Telegram через прямой Bot API:
     source .env.routine
     curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
       -d "chat_id=${TELEGRAM_CHAT_ID}" \
       --data-urlencode "text=$(cat reports/weekly/YYYY-Www.md)" \
       --data-urlencode "parse_mode=Markdown"
    Если >4096 символов — разбей на части по абзацам.
13. Дополнительно: сгенерируй краткий список (5–8 пунктов) задач для команды на 
    эту неделю на основе рекомендаций — отправь отдельным сообщением в Telegram 
    с заголовком "Действия на неделю".
```

Каденс: `0 10 * * 1` (каждый понедельник в 10 утра МСК).

---

## Monthly routine — 1-го числа каждого месяца в 11:00 МСК

```
Запусти skill pinkspink-analytics-coach. Сегодня monthly report.

Шаги:
1. Через BigQuery MCP подтяни данные за прошлый полный календарный месяц 
   и за месяц до него.
2. Применяй стандартные фильтры из skill.
3. Сначала прочитай 4 еженедельных отчёта из reports/weekly/ за последний месяц 
   — это контекст для месячного.
4. По всем трём вкладкам сравни месяц vs предыдущий месяц.
5. Отдельно поработай с retention/cohorts — это единственный блок, который 
   реально считается на месячном горизонте.
6. Сгенерируй monthly report по шаблону из references/report-template.md (≤1500 слов).
7. В блоке "Гипотезы — статус" обнови состояние standing hypotheses из SKILL.md: 
   подтвердилась/опровергнулась/без изменений за этот месяц.
8. Сохрани отчёт в reports/monthly/YYYY-MM.md
9. Закоммить и запушь:
     git add reports/monthly/YYYY-MM.md
     git commit -m "monthly report YYYY-MM"
     git push
10. Отправь в Telegram через прямой Bot API (как в daily/weekly). 
    Длинный текст разбить на 2-3 сообщения по разделам.
```

Каденс: `0 11 1 * *` (1-го числа каждого месяца в 11 утра МСК).

---

## Заметки

**Лимиты `/schedule`:**
- Pro: 5 routines/день. Все три (daily + weekly понедельник + monthly первое число) активны = в самый загруженный день 3 запуска. Запас есть.
- Max: 15/день — запас огромный.

**Отладка:**
- Если routine не запустилась — `/schedule list` в Claude Code → проверь статус.
- Если skill не подцепился — проверь description в SKILL.md, должен быть достаточно «пушистым» (Skill автотриггерится по описанию).
- Если BigQuery MCP вернул пусто — это нормально для первых 24ч после конца дня, routine должна это обрабатывать (см. шаг с «повторить через час»).

**После 2-3 недель работы:**
- Прочитай 10-15 отчётов подряд. Где Claude систематически промахивается?
- Обнови skill: добавь правила, уточни пороги, скорректируй шаблоны.
