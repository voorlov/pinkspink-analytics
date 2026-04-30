# Exploration Patterns — Pinkspink

Reference for deep analysis: which cuts to make beyond the dashboard, which confounders to check for Pinkspink specifically, and SQL templates for BigQuery (`claude-code-486108.analytics_411715710.events_*`).

All output to the user must still be in Russian — see SKILL.md § Output language.

---

## §1. Catalog of cuts beyond the dashboard

The dashboard aggregates. Reality lives in the details. This catalog is not a checklist for one report — it's a pool to rotate 3–5 cuts from for each weekly report.

### Time-based cuts

**Hour of day × channel.** Japanese traffic at 22:00 JST != American traffic at 22:00 PST, but the dashboard collapses them. Hourly patterns often expose bot activity (uniform around the clock) or non-working creative (peak at night when the target audience is asleep).

**Day of week × channel/country.** Fashion e-commerce typically peaks Sunday evening and Monday, dips Wednesday. If the pattern is different — that's a signal, not an anomaly (either an unusual audience, or content publication on specific days).

**Week of month.** Is there a "got paid → went shopping" pattern? Japan and US have different payday timing.

**Time since first visit.** How long between a user's first session and their ATC, for those who do convert? Hours, days, weeks? This shapes the email/retargeting window length.

### Geo cuts

**City inside country.** `geo.city` in BigQuery. Tokyo vs Osaka vs Fukuoka — different behaviors, different audiences. NY vs LA — different demographics. Sometimes "Japan" is 80% Tokyo, and that's critical for ad targeting.

**Region (state/prefecture).** `geo.region`. Useful for the US — California and New York are a different audience than the South or Midwest.

**City × source.** If New York comes via Direct and LA comes via Social — those are different marketing situations.

### Technical cuts

**Browser × OS.** Safari iOS vs Chrome Android behave differently. Conversion drop only on iOS = bug in iOS Safari checkout. Browser share is a "site health" signal.

**Screen size.** Narrow screens (<375px iPhone SE) often suffer from broken layouts. If conversion is much lower there — there's a UX problem.

**Page load time** (if `page_load_time` event exists) — correlates with scroll and ATC.

### Behavioral cuts

**Session number.** 1st, 2nd, 3rd, 4th+. ATC conversion typically grows with session number. If you have a segment where 1st-session conversion exceeds 3rd-session — that's either bot traffic or impulse-buyer geography.

**Source × landing page** — which specific entry URLs work for each source? Often Instagram traffic lands on a specific "currently selling" item, and a collection redesign can break or improve an entire channel.

**Time-on-site distribution** — not just median. Mode (most common value), 90th percentile, share of <10s sessions. If median is 30s, but 60% of sessions are <10s and 30% are 90s+, you have a bimodal distribution: two different audiences that should be analyzed separately.

**Session paths** — top 5 sequences of pages before ATC. Often it turns out 80% of buyers follow one path, and that's the path to optimize.

### Content cuts

**Which collections work.** `page_path LIKE '/collections/%'` grouped by slug. Top-10 collections by sessions vs by conversion to Product View — these are different lists.

**Which products lead to ATC** relative to their traffic. A product page with 100 views and 5 ATCs beats a page with 1000 views and 8 ATCs.

**Catalog-views to ATC ratio for specific collections** — some collections are "advertising" (drive traffic to catalog), some are "commercial" (drive ATC).

---

## §2. Confounder catalog for Pinkspink

Things that must be explicitly screened before drawing conclusions. If a confounder is plausible and can't be checked from data — ask the user.

### C1. Team VPN traffic

Partially mitigated through excluded countries (China, Hong Kong, South Korea, Singapore). But the team can use VPN from ANY country for testing or simply for service access. **This is the single most common confounder for Pinkspink.**

Indicators:
- Sudden desktop spike from a specific geography.
- Time-of-day overlap with team working hours (UTC+8).
- High engagement (the team browses with intent, unlike typical visitors).
- ATC/checkout without purchase (test runs).

Checks:
- Does the spike align with Kè Jǐ's office hours (Guangzhou, UTC+8)?
- Is it desktop Chrome/Safari macOS? (typical team setup)
- Does the city inside the country match a known office location or a known VPN provider exit?

Action: **ask the user**. Phrasing (in Russian): "На прошлой неделе ты или Ксюша делали тестовые заходы через VPN из [country]? Виден всплеск в desktop-сегменте оттуда."

### C2. Bots

Indicators:
- Sessions with >5 pageviews + time-on-site <5 seconds (non-human speed).
- Engagement rate 0% across hundreds of sessions.
- Single-pageview sessions clustered in a narrow time window.
- Unusual browser/OS distribution (e.g. 80% from one user-agent).
- Source `(direct)` or `referral` from suspicious domains.

Checks:
- SQL: count of sessions with `engagement_time_msec < 1000` AND `screen_views >= 3`. Bots produce the unnatural "many pages, zero time" combination.
- `device.web_info.browser_version` distribution — too narrow = bot.

Action: exclude from the sample and explicitly note in the report. "Из этой недели исключено N сессий, идентифицированных как бот-трафик (паттерн: ...)."

### C3. Ad campaign just launched / ended

Indicators:
- Sharp step-change in Paid traffic (not a drift).
- Coincides with a round date (Monday, the 1st).

Checks:
- Ask the user or Ksyusha: "Запускали что-то в Meta Ads на этой неделе? Креатив сменился?"
- Compare the change point to known campaign dates (if logged).

Action: the first week of a campaign always has bad engagement (the algorithm is learning). Don't draw conclusions before week 2. Note in report: "Paid сегмент — неделя 1 после launch, judgement отложен до next week."

### C4. Social mini-virality

Indicators:
- Sudden Direct or Referral spike on a single day, doesn't repeat.
- Spike geography matches a known Instagram audience pattern.
- High engagement without ATC (curious visitors, not buyers).

Checks:
- Did someone repost, story-mention, or get mentioned by an influencer?
- Ask the user: "6 марта был всплеск Direct из Бразилии — кто-то репостил?"

Action: if one-off — note as a "singularity" in the report. If it repeats 1–2 weeks later — consider as a segment for further study.

### C5. Seasonality

Known periods for Pinkspink (primary markets Japan + USA):
- **Japanese Golden Week** (April 29 – May 5) — holidays, e-commerce typically dips or shifts pattern significantly.
- **Obon** (mid-August in Japan) — same.
- **Christmas + New Year** — global e-commerce peak in December, slump in the first week of January.
- **Black Friday** (last Friday of November) — even without your own discounts, behavior pattern shifts.
- **Japanese 月末** (end of month) — payday on the 25th, shopping 25th–30th.

Checks:
- Does the week overlap with a known holiday period?
- Compare to the same calendar period a year ago (when there will be a year of data).

Action: explicitly note in report — "эта неделя совпала с Golden Week, паттерн ожидаемо отличается."

### C6. Site deploy

Indicators:
- Step-change in any UX metric (scroll, time-on-page, ATC) on a specific date.
- The metric "changed" only on mobile or only on desktop.

Checks:
- Ask the user: "Деплоили что-то на сайте около [date]? Метрика [Y] сделала ступеньку."
- If a git/Shopify deploy log exists — cross-reference.

Action: attribute the change to deploy, not behavior. If the deploy improved things — log as a win. If it worsened them — recommend rollback.

### C7. Tracking / sample-rate issues

Indicators:
- A metric that should never halve in a week halved.
- Sharp shift in ratio between event types (e.g., ATC events became 5× rarer relative to view_item).
- Drop across all channels simultaneously — usually this isn't real behavior, it's tracking.

Checks:
- Count `session_start` events for the period — should be stable.
- Compare to GA4 Reporting UI: if those numbers differ from BigQuery — there's an export issue.

Action: notify the user about a potential tracking issue. Do not draw behavioral conclusions from suspect data. "Подозрение на проблему с tracking — ATC events упали в 5 раз без аналогичного падения trafic. Проверь GA4 → DebugView и Tag Manager."

---

## §3. SQL templates for exploration

All templates target BigQuery, dataset `claude-code-486108.analytics_411715710.events_*`, GA4 standard schema.

**Note:** `events_*` refers to all daily partitions (`events_20260201`, `events_20260202`, ...). Use `_TABLE_SUFFIX` to filter by date range.

### S1. Hour of day × channel

```sql
SELECT
  EXTRACT(HOUR FROM TIMESTAMP_MICROS(event_timestamp) AT TIME ZONE 'Asia/Tokyo') AS hour_jst,
  CASE
    WHEN traffic_source.source IN ('ig', 'l.instagram.com') THEN 'Social'
    WHEN traffic_source.source = '(direct)' THEN 'Direct'
    WHEN traffic_source.source IN ('google', 'bing', 'yahoo', 'ecosia.org') THEN 'Organic'
    WHEN traffic_source.source LIKE '%meta%' OR traffic_source.medium IN ('paid', 'cpm') THEN 'Paid'
    WHEN traffic_source.source LIKE '%facebook%' THEN 'Referral'
    ELSE 'Other'
  END AS channel,
  COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING))) AS sessions
FROM `claude-code-486108.analytics_411715710.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20260420' AND '20260426'
  AND geo.country NOT IN ('China', 'Hong Kong', 'South Korea', 'Singapore')
  AND traffic_source.source NOT IN ('api.scraperforce.com', 'sanganzhu.com', 'jariblog.online')
  AND event_name = 'session_start'
GROUP BY hour_jst, channel
ORDER BY hour_jst, sessions DESC;
```

### S2. City × country with quality metrics (for finding expansion candidates)

```sql
WITH session_metrics AS (
  SELECT
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
    geo.country AS country,
    geo.city AS city,
    MAX(IF(event_name = 'add_to_cart', 1, 0)) AS has_atc,
    MAX(IF(event_name = 'view_item', 1, 0)) AS has_view_item,
    SUM(IF(event_name = 'page_view', 1, 0)) AS pageviews,
    SUM(
      IF(event_name = 'user_engagement',
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec'),
        0)
    ) / 1000.0 AS engagement_sec
  FROM `claude-code-486108.analytics_411715710.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20260420' AND '20260426'
    AND geo.country NOT IN ('China', 'Hong Kong', 'South Korea', 'Singapore')
  GROUP BY user_pseudo_id, session_id, country, city
)
SELECT
  country,
  city,
  COUNT(*) AS sessions,
  ROUND(AVG(has_atc) * 100, 2) AS atc_rate_pct,
  ROUND(APPROX_QUANTILES(engagement_sec, 100)[OFFSET(50)], 1) AS median_engagement_sec,
  ROUND(AVG(pageviews), 2) AS avg_pageviews
FROM session_metrics
GROUP BY country, city
HAVING sessions >= 10
ORDER BY atc_rate_pct DESC, median_engagement_sec DESC;
```

After execution — compare ATC rate, median engagement, avg pageviews for each city against the site-wide mean. Any city with ≥1.5× the average is a candidate.

### S3. Bot screening

```sql
WITH session_summary AS (
  SELECT
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
    COUNT(IF(event_name = 'page_view', 1, NULL)) AS pageviews,
    SUM(
      IF(event_name = 'user_engagement',
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec'),
        0)
    ) AS engagement_msec,
    ANY_VALUE(device.web_info.browser) AS browser,
    ANY_VALUE(device.operating_system) AS os
  FROM `claude-code-486108.analytics_411715710.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20260420' AND '20260426'
  GROUP BY user_pseudo_id, session_id
)
SELECT
  CASE
    WHEN pageviews >= 5 AND engagement_msec < 5000 THEN 'suspicious_bot'
    WHEN pageviews = 1 AND engagement_msec = 0 THEN 'bounce'
    ELSE 'human'
  END AS classification,
  COUNT(*) AS sessions,
  ANY_VALUE(browser) AS sample_browser,
  ANY_VALUE(os) AS sample_os
FROM session_summary
GROUP BY classification
ORDER BY sessions DESC;
```

If `suspicious_bot` count is comparable to real-user count — that's a serious confounder, do not ignore.

### S4. Session number for user (returning behavior)

```sql
WITH user_sessions AS (
  SELECT
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
    MIN(event_timestamp) AS session_start,
    MAX(IF(event_name = 'add_to_cart', 1, 0)) AS has_atc
  FROM `claude-code-486108.analytics_411715710.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20260301' AND '20260426'
    AND geo.country NOT IN ('China', 'Hong Kong', 'South Korea', 'Singapore')
  GROUP BY user_pseudo_id, session_id
),
ranked AS (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY user_pseudo_id ORDER BY session_start) AS session_number
  FROM user_sessions
)
SELECT
  CASE
    WHEN session_number = 1 THEN '1st'
    WHEN session_number = 2 THEN '2nd'
    WHEN session_number = 3 THEN '3rd'
    WHEN session_number BETWEEN 4 AND 10 THEN '4-10'
    ELSE '11+'
  END AS session_bucket,
  COUNT(*) AS sessions,
  ROUND(AVG(has_atc) * 100, 2) AS atc_rate_pct
FROM ranked
GROUP BY session_bucket
ORDER BY MIN(session_number);
```

Shows how ATC rate changes as a user returns. If ATC grows by the 2nd–3rd session, the return loop works and there's a case for investing in retargeting.

### S5. Top landing pages × source

```sql
WITH first_pages AS (
  SELECT
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
    ARRAY_AGG(
      (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location')
      ORDER BY event_timestamp ASC LIMIT 1
    )[OFFSET(0)] AS landing_url,
    ANY_VALUE(traffic_source.source) AS source,
    MAX(IF(event_name = 'add_to_cart', 1, 0)) AS has_atc
  FROM `claude-code-486108.analytics_411715710.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20260420' AND '20260426'
    AND geo.country NOT IN ('China', 'Hong Kong', 'South Korea', 'Singapore')
  GROUP BY user_pseudo_id, session_id
)
SELECT
  REGEXP_EXTRACT(landing_url, r'pinkspink\.[a-z]+/[^?#]*') AS landing_path,
  source,
  COUNT(*) AS sessions,
  ROUND(AVG(has_atc) * 100, 2) AS atc_rate_pct
FROM first_pages
WHERE landing_url IS NOT NULL
GROUP BY landing_path, source
HAVING sessions >= 5
ORDER BY sessions DESC
LIMIT 30;
```

Shows which specific landing URLs work best for each source.

### S6. Browser × OS health-check

```sql
SELECT
  device.web_info.browser AS browser,
  device.operating_system AS os,
  COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING))) AS sessions,
  ROUND(AVG(IF(event_name = 'add_to_cart', 1, 0)) * 100, 2) AS atc_rate_pct
FROM `claude-code-486108.analytics_411715710.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20260420' AND '20260426'
  AND geo.country NOT IN ('China', 'Hong Kong', 'South Korea', 'Singapore')
GROUP BY browser, os
HAVING sessions >= 20
ORDER BY sessions DESC;
```

If ATC rate drops sharply on one browser/OS combination (e.g., Safari + iOS), that may be a UX bug.

---

## §4. Adapting the templates

All SQL templates are starting points. If a query returns something interesting, run a follow-up that adds another dimension or tightens the condition. Don't be afraid to iterate through 5–6 queries within one investigation — that's normal.

If a query is slow or returns too much data, narrow the period (`_TABLE_SUFFIX` range) and add `LIMIT`. BigQuery prices on scanned-data volume — tight filters save both time and money.

If event schema differs from expectations (sometimes `events_intraday_*` has different fields), inspect the schema via BigQuery MCP — `INFORMATION_SCHEMA.COLUMNS` or just `SELECT * FROM events_* LIMIT 1`.
