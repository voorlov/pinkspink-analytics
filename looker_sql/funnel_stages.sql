-- Looker Studio: Funnel Stages (вертикальный формат для диаграммы воронки)
-- Параметры: @DS_START_DATE, @DS_END_DATE, @grain

WITH events AS (
    SELECT
        PARSE_DATE('%Y%m%d', event_date) AS date,
        user_pseudo_id,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
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
            WHEN source = 'facebook' AND medium IN ('paid', 'cpm') THEN 'Paid'
            WHEN source IN ('ig', 'l.instagram.com') AND medium IN ('social', 'referral') THEN 'Social'
            WHEN medium = 'organic' THEN 'Organic'
            WHEN medium = 'email' THEN 'Email'
            WHEN source = '(direct)' AND medium IN ('(none)', '(not set)') THEN 'Direct'
            WHEN medium = 'referral' THEN 'Referral'
            ELSE 'Other'
        END AS channel,
        country,
        device,
        user_pseudo_id,
        session_id,
        MAX(CASE WHEN event_name = 'page_view' AND REGEXP_CONTAINS(IFNULL(page_path, ''), r'^/(ja|ru)?/?$') THEN 1 ELSE 0 END) AS has_homepage,
        MAX(CASE WHEN event_name = 'page_view' AND REGEXP_CONTAINS(IFNULL(page_path, ''), r'/collections/') AND NOT REGEXP_CONTAINS(IFNULL(page_path, ''), r'/products/') THEN 1 ELSE 0 END) AS has_catalog,
        MAX(CASE WHEN event_name = 'view_item' THEN 1 ELSE 0 END) AS has_product,
        MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) AS has_atc,
        MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS has_checkout,
        MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS has_purchase
    FROM events
    GROUP BY date, channel, country, device, user_pseudo_id, session_id
),

funnel AS (
    SELECT date, channel, country, device,
        stage, stage_order, step_hit
    FROM sessions,
    UNNEST([
        STRUCT('1. Homepage' AS stage, 1 AS stage_order, has_homepage AS step_hit),
        STRUCT('2. Catalog', 2, has_catalog),
        STRUCT('3. Product', 3, has_product),
        STRUCT('4. Add to Cart', 4, has_atc),
        STRUCT('5. Checkout', 5, has_checkout),
        STRUCT('6. Purchase', 6, has_purchase)
    ])
)

SELECT
    CASE @grain
        WHEN 'day' THEN CAST(date AS STRING)
        WHEN 'week' THEN FORMAT_DATE('%G-W%V', date)
        WHEN 'month' THEN FORMAT_DATE('%Y-%m', date)
        ELSE FORMAT_DATE('%G-W%V', date)
    END AS period,
    channel,
    country,
    device,
    stage,
    stage_order,
    SUM(step_hit) AS sessions
FROM funnel
GROUP BY period, channel, country, device, stage, stage_order
ORDER BY period, stage_order
