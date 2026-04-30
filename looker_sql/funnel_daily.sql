-- Looker Studio: Unified Data Source
-- Всё в одном: воронка + поведение сессий + engagement rate + устройства
-- Параметры: @DS_START_DATE, @DS_END_DATE (даты), @grain (day/week/month)

WITH events AS (
    SELECT
        PARSE_DATE('%Y%m%d', event_date) AS date,
        user_pseudo_id,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'session_engaged') AS session_engaged,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec') AS engagement_time_msec,
        event_name,
        REGEXP_EXTRACT((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'), r'https?://[^/]+(/.*)?') AS page_path,
        geo.country,
        device.category AS device,
        IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), IFNULL(traffic_source.source, '(direct)')) AS source,
        IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) AS medium
    FROM `claude-code-486108.analytics_411715710.events_*`
    WHERE _TABLE_SUFFIX BETWEEN @DS_START_DATE AND @DS_END_DATE
),

sessions AS (
    SELECT
        date,
        CASE
            WHEN source IN ('api.scraperforce.com', 'sanganzhu.com', 'jariblog.online') THEN 'Spam'
            WHEN medium IN ('paid', 'cpm') THEN 'Paid'
            WHEN source IN ('ig', 'l.instagram.com') AND medium IN ('social', 'referral') THEN 'Social'
            WHEN medium = 'organic' THEN 'Organic'
            WHEN medium = 'email' THEN 'Email'
            WHEN source = '(direct)' AND medium IN ('(none)', '(not set)') THEN 'Direct'
            WHEN medium = 'referral' THEN 'Referral'
            ELSE 'Other'
        END AS channel,
        source,
        medium,
        country,
        device,
        user_pseudo_id,
        session_id,
        MAX(session_engaged) AS session_engaged,
        SUM(engagement_time_msec) AS eng_ms,
        COUNTIF(event_name = 'page_view') AS pages,
        -- Page-based funnel
        MAX(CASE WHEN event_name = 'page_view' AND REGEXP_CONTAINS(IFNULL(page_path, ''), r'^/(ja|ru)?/?$') THEN 1 ELSE 0 END) AS has_homepage,
        MAX(CASE WHEN event_name = 'page_view' AND REGEXP_CONTAINS(IFNULL(page_path, ''), r'/collections/') AND NOT REGEXP_CONTAINS(IFNULL(page_path, ''), r'/products/') THEN 1 ELSE 0 END) AS has_catalog,
        -- Event-based funnel
        MAX(CASE WHEN event_name = 'view_item' THEN 1 ELSE 0 END) AS has_view_item,
        MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) AS has_atc,
        MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS has_checkout,
        MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS has_purchase
    FROM events
    GROUP BY date, channel, source, medium, country, device, user_pseudo_id, session_id
)

SELECT
    CASE @grain
        WHEN 'day' THEN CAST(date AS STRING)
        WHEN 'week' THEN FORMAT_DATE('%G-W%V', date)
        WHEN 'month' THEN FORMAT_DATE('%Y-%m', date)
        ELSE FORMAT_DATE('%G-W%V', date)
    END AS period,
    channel,
    source,
    medium,
    country,
    device,

    -- Сессии и пользователи
    COUNT(*) AS sessions,
    COUNT(DISTINCT user_pseudo_id) AS users,

    -- Engagement
    COUNTIF(session_engaged = '1') AS engaged_sessions,
    ROUND(SAFE_DIVIDE(COUNTIF(session_engaged = '1'), COUNT(*)) * 100, 1) AS engagement_rate,
    ROUND(APPROX_QUANTILES(eng_ms, 100)[OFFSET(50)] / 1000, 1) AS median_eng_sec,
    ROUND(AVG(pages), 1) AS avg_pages,

    -- Глубина просмотра
    COUNTIF(pages = 1) AS sessions_1page,
    COUNTIF(pages BETWEEN 2 AND 5) AS sessions_2_5pages,
    COUNTIF(pages > 5) AS sessions_over5pages,

    -- Воронка (по этапам)
    COUNTIF(has_homepage = 1) AS funnel_homepage,
    COUNTIF(has_catalog = 1) AS funnel_catalog,
    COUNTIF(has_view_item = 1) AS funnel_product,
    COUNTIF(has_atc = 1) AS funnel_add_to_cart,
    COUNTIF(has_checkout = 1) AS funnel_checkout,
    COUNTIF(has_purchase = 1) AS funnel_purchase

FROM sessions
GROUP BY period, channel, source, medium, country, device
ORDER BY period, channel
