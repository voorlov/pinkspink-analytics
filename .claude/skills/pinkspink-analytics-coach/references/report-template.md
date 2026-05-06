# Report Templates

Three templates: daily, weekly, monthly. Use the cadence that matches the request. All templates assume the audience is Vladimir (project owner), who reads in Russian and already knows the project context — be terse, skip preamble, lead with the verdict.

## Style rules (daily + weekly)

- **Russian.** Always.
- **Headline first.** One or two sentences right after the date heading — verdict + main reason. Reads like an elevator pitch to a stakeholder. No section header before it.
- **Tables for breakdowns.** Use Markdown tables for ATC sessions, channel deltas, audience candidates. They make the report scannable.
- **Block structure with `###` headers.** The user skims by headers, not by paragraph. Each block answers one question.
- **Plain Russian for numbers.** "Каждый 22-й положил в корзину" beats "ATC rate 4.55%". "Вдвое чаще обычного" beats "+2.6pp vs baseline".
- **Flag emoji for countries** (🇯🇵 🇺🇸 🇩🇪 🇰🇿 🇬🇪) — reinforces visual scanning.
- **Channel and event names stay original.** Social, Paid, Direct, Organic, Referral, ATC, view → ATC → checkout — these are the project's lingua franca, the user knows them.
- **Banned phrases in prose** (ok in table headers): "View→ATC", "ATC rate", "small-sample", "confounder", "baseline", "trailing 7-day". Translate them.
- **Tie observations to actions.** Every "X moved" gets a "and here's what we did" — pull from `changelog.md` and the ad tracker (`PINKSPINK_Ads_Tracker_v2.xlsx`).

---

## Daily template

The daily comes in two shapes: **quiet day** (default — most days) and **day with event**. Pick one.

### Quiet day (≤30 words, no sections)

Use when nothing significant moved (per metrics-playbook small-sample / threshold rules — typically ATC events <2 above weekly trend, sessions within ±25% of trailing 7-day average, no new top-5 country, no missing top-5 country).

```
## [DD.MM] — спокойный день

[N] сессий, всё в пределах нормы. [Опционально, одна строка: чего ждём. Например: "Ждём эффект от новых рекламных сеток к 4–6 мая." Если ждать нечего — пропустить.]
```

That's the entire report. No "цифры" block, no "что посмотрим завтра", no caveats. A fake five-section report on a quiet day is worse than two lines.

### Day with event (≤200 words of prose excluding tables)

Use when something actually moved. Block structure:

```
## [DD.MM]

**[Headline 1–2 фразы. Что произошло простым языком + если есть, привязка к нашим действиям. Например: "Из 66 посетителей 3 положили товар в корзину — в 2.4× выше нормы. Совпало с запуском новых рекламных сеток 30.04–04.05."]**

### Кто положил в корзину

| Страна / город | Канал | Воронка |
|---|---|---|
| 🇯🇵 Сибуя | Direct, мобила | view → ATC |
| 🇺🇸 Сиэтл | Social / ig, мобила | view → ATC → checkout |
...

[Если в ATC попали excluded countries (Грузия = ассистент) или сомнительные (Россия) — короткая ⚠️ строка под таблицей: "Тбилиси — это, скорее всего, ассистент. Если так, реальных клиентских корзин было N → конверсия ближе к X%."]

### Трафик по странам

🇯🇵 Япония N · 🇺🇸 США N · 🇩🇪 Германия N · ... (5–7 стран max, через · разделитель)

### Что важно

- [3–4 буллета. Каждый: 1–2 предложения, конкретные цифры, привязка к рекламе/changelog. Например: "Япония — 41 визит, 0 корзин. Stage-1 реклама гонит трафик, но до действия пока не доводит. Норма для cold-start новых креативов."]

### Смотрим завтра

- [Конкретный индикатор. Например: "Появятся ли первые корзины из Японии — главный сигнал, что реклама работает."]
- [Ещё один при необходимости. Не больше 3.]
```

If on inspection the day is quiet after all (you started writing the long version, then realised nothing real moved) — collapse to the quiet form. Don't pad.

---

## Weekly template (≤700 words of prose excluding tables)

Used Monday morning, comparing the just-closed week vs avg of previous 4 full weeks.

```
## Прошлая неделя · [start_date] – [end_date]

**[Headline 1–2 фразы. Главный сдвиг недели простым языком + связь с нашими действиями. Например: "Сильная неделя: трафик +34%, корзин +43%. 30 апреля запустились 5 новых рекламных сеток на разогрев в IG → со среды весь трафик удвоился. Покупок по-прежнему ноль."]**

### Главные числа

| | Эта неделя | Норма (4 пред.) | Δ |
|---|---|---|---|
| Сессии | N | M | ±X% |
| Положили в корзину | N | M | ±X% |
| Дошли до checkout | N | M | ±X% |
| Покупки | N | M | — |

### Кто положил в корзину (N человек)

| Дата | Страна / город | Канал | Воронка |
|---|---|---|---|
| 28.04 | 🇰🇿 Астана | Social / ig | view → ATC → **checkout** |
| 30.04 | 🇯🇵 Нагоя | Social / ig | view → ATC → **checkout** |
...

[Под таблицей — 1 предложение про распределение. Например: "3 из 5 — Япония (как и должно быть, реклама там). 2 — органика через IG (Казахстан, США). До покупки не дошёл никто."]

### Ритм недели

```
27.04 пн: 16 сес.
28.04 вт: 17
...
30.04 чт: 87 ← запуск 5 новых ad-сетов + ссылки в IG-bio
...
03.05 вс: 100
```

[1 предложение про паттерн — где перелом, бимодальная или ровная.]

### Откуда трафик

🇯🇵 Япония N (X%) · 🇺🇸 США N · 🇩🇪 Германия N · ... · остальные N стран по 1–3

### Каналы — что изменилось

| Канал | Неделя | Норма | Δ |
|---|---|---|---|
| Social | N | M | ±X% [← если есть очевидное объяснение, короткая пометка] |
| Paid | N | M | ±X% |
| Direct | N | M | флэт / ±X% |
| Organic | N | M | ±X% |
| Referral | N | M | ±X% |

[1 предложение, если нужно объяснить движение — особенно про Stage-1 → Social, Stage-2 → Paid.]

### Что важно

- [3–4 буллета. Каждый: 1–2 предложения, конкретные цифры, привязка к рекламе/changelog. Самый важный — первым.]

### Кандидаты на расширение

| Сегмент | Сессии | View | Сигнал |
|---|---|---|---|
| 🇺🇸 США (Сиэтл) | 26 | 14 | 1 ATC, единственный non-JP город с действием |
| 🇰🇿 Казахстан | 2 | 1 | 2 из 2 покупательных событий за всю историю |
...

[Если кандидатов нет — одна строка: "Сегментов с устойчивым сигналом качества выше нормы на этой неделе не обнаружено."]

### Рекомендации

1. **[Конкретное действие]** — [1–2 предложения. Какой блок дашборда / какая цифра мотивирует. Бюджет или время. Метрика, которую ожидаем увидеть.]
2. ...
3. ...

[Максимум 3. Если рекомендовать нечего — "Конкретных рекомендаций по этой неделе нет, продолжаем наблюдение."]

### Что смотрим на этой неделе

- [Конкретный индикатор. Связан с одной из рекомендаций или с гипотезой о поведении.]
- [2–3 максимум.]
```

### Sections that may be skipped on quiet weeks

- **Кто положил в корзину** — если за неделю было 0–1 ATC, можно одну строку: "За неделю — 0 корзин." или "1 корзина: 🇯🇵 Япония, Direct."
- **Каналы — что изменилось** — если ни один канал не сдвинулся больше чем на 20% — пропустить.
- **Кандидаты на расширение** — обязательный, но при отсутствии находок — одна строка вместо таблицы.

### Sections from the old template that didn't survive

The old weekly template required separate sections "Что я исследовал за пределами дашборда" and "Гипотезы и проверка confounders" with explicit hypothesis-confounder structure. **In the automated weekly cron these are NOT possible** — the cron has only pre-aggregated JSON, no BigQuery access. The hypothesis logic is now woven into the "Что важно" block instead. For ad-hoc weekly analysis in interactive Claude Code, the deeper exploration belongs in a separate response, not the standard template.

---

## Monthly template (≤1500 words)

Use when the routine fires on the 1st of the month, comparing previous full calendar month vs the one before it. The monthly is heavier and more strategic — fuller prose is OK here, but still prefer block structure over walls of text.

```
## Pinkspink — [Month Year]

**[Headline 2–3 фразы. Главное за месяц. Это TL;DR — должно читаться отдельно от остального и быть достаточным для понимания.]**

### Главные числа за месяц

| | [Month] | [Prev Month] | Δ |
|---|---|---|---|
| Сессии | N | M | ±X% |
| Положили в корзину | N | M | ±X% |
| Дошли до checkout | N | M | ±X% |
| Покупки | N | M | — |
| Уникальные посетители | N | M | ±X% |

### Динамика по неделям

[ASCII-блок или короткая таблица: 4–5 недель, sessions/ATC/checkout по неделям. 1–2 предложения про тренд внутри месяца — рос/падал/двигался.]

### Каналы за месяц

| Канал | Месяц | Прошлый | Δ |
| ... |

[1–2 предложения. Ключевые сдвиги. Связь со Stage-1/Stage-2 рекламой и любыми событиями из changelog.]

### География

[Top-5 стран за месяц + 1–2 предложения про новых entries в топ-10. Особое внимание устойчивым (≥2 недели подряд) кандидатам на расширение.]

### Воронка и узкие места

[2–3 предложения. Главное горлышко — что именно теряет больше всего пользователей. На месячном горизонте уже можно делать осмысленные выводы.]

### Карточка товара

[1–2 предложения. Что в топе по просмотрам, средняя глубина, паттерны времени. Берётся из вкладки "Карточка товара" дашборда.]

### Когорты и retention

[1–2 предложения. Возвращаются ли люди, у каких источников лучший retention. Это **единственный** блок, который имеет смысл смотреть только на месячном горизонте — на дневном/недельном он шумный.]

### Standing hypotheses — статус

[Список стоячих гипотез из SKILL.md. Для каждой одно предложение: подтвердилась/опровергнулась/без изменений за месяц.]

### Кандидаты на расширение — итог месяца

[Свести все недельные находки в один список. Что появлялось 2+ раза за месяц = устойчивый сигнал. Что было разовое — отбросить. По каждому устойчивому: тестируем / откладываем / отбрасываем (с причиной).]

### Confounders за месяц

[Если что-то приходилось разоблачать (VPN-всплески, кампании, деплои, баги) — короткий список с датами. Полезно для будущих расследований.]

### Рекомендации на следующий месяц

[Максимум 3. Тот же формат, что в недельном. На месячном горизонте — стратегические, не "поправить кнопку". Например, "запустить тест X на четыре недели".]

### Что бы посмотрел в следующий раз

[3–5 вопросов или дополнительных разрезов, которые не влезли в этот отчёт но накопились как любопытные.]
```

---

## Делая отчёт впервые

Если это первый отчёт за неделю/месяц после установки skill — не имеет смысла сразу выдавать рекомендации. Первый отчёт должен установить baseline. В таком случае:
- Опиши текущее состояние без сравнений ("сейчас N сессий/неделю, конверсия M%")
- Не выдумывай "просадки" из ничего — нет данных для сравнения
- В разделе "Что смотрим дальше" попроси у пользователя 2-3 решения: какие пороги считать аномальными, какие метрики приоритизировать, нужны ли отдельные срезы

---

## Если данных нет

Если за период не пришло данных (BigQuery export пропустил день, или MCP-вызов вернул пусто) — не выдумывай числа. Скажи прямо: *"Данные за [дата] не доступны на момент запроса. Возможные причины: задержка GA4→BigQuery export (обычно до 24ч), проблема с MCP, отсутствие активности."* и предложи что сделать дальше (повторить запрос через час, проверить BigQuery напрямую и т.д.).
