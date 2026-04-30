-- Looker Studio: Sessions Daily
-- Каждая строка = период + источник трафика + страна + метрики поведения
-- Параметры: @DS_START_DATE, @DS_END_DATE (даты), @grain (day/week/month)

WITH events AS (
    SELECT
        PARSE_DATE('%Y%m%d', event_date) AS date,
        user_pseudo_id,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'session_engaged') AS session_engaged,
        event_name,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec') AS engagement_time_msec,
        geo.country,
        CASE
            WHEN IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), traffic_source.source) = 'facebook'
                 AND IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), traffic_source.medium) IN ('paid', 'cpm')
                 THEN 'Paid Ads'
            WHEN IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), traffic_source.source) IN ('ig', 'l.instagram.com')
                 AND IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), traffic_source.medium) IN ('social', 'referral')
                 AND geo.country = 'Japan'
                 THEN 'Instagram (Japan)'
            WHEN IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), traffic_source.source) IN ('ig', 'l.instagram.com')
                 AND IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), traffic_source.medium) IN ('social', 'referral')
                 THEN 'Instagram (Other)'
            ELSE 'Other'
        END AS traffic_source
    FROM `claude-code-486108.analytics_411715710.events_*`
    WHERE _TABLE_SUFFIX BETWEEN @DS_START_DATE AND @DS_END_DATE
),

sessions AS (
    SELECT
        date,
        traffic_source,
        country,
        user_pseudo_id,
        session_id,
        MAX(session_engaged) AS session_engaged,
        SUM(engagement_time_msec) AS eng_ms,
        COUNTIF(event_name = 'page_view') AS pages
    FROM events
    GROUP BY date, traffic_source, country, user_pseudo_id, session_id
)

SELECT
    CASE @grain
        WHEN 'day' THEN CAST(date AS STRING)
        WHEN 'week' THEN FORMAT_DATE('%G-W%V', date)
        WHEN 'month' THEN FORMAT_DATE('%Y-%m', date)
        ELSE FORMAT_DATE('%G-W%V', date)
    END AS period,
    traffic_source,
    country,
    COUNT(*) AS sessions,
    COUNTIF(session_engaged = '1') AS engaged_sessions,
    ROUND(SAFE_DIVIDE(COUNTIF(session_engaged = '1'), COUNT(*)) * 100, 1) AS engagement_rate,
    ROUND(APPROX_QUANTILES(eng_ms, 100)[OFFSET(50)] / 1000, 1) AS median_eng_sec,
    ROUND(AVG(pages), 1) AS avg_pages,
    COUNTIF(pages = 1) AS sessions_1page,
    COUNTIF(pages BETWEEN 2 AND 5) AS sessions_2_5pages,
    COUNTIF(pages > 5) AS sessions_over5pages
FROM sessions
GROUP BY period, traffic_source, country
ORDER BY period, traffic_source
