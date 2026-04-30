-- Looker Studio: Transactions
-- Каждая строка = одна транзакция с полной атрибуцией
-- Используй как Custom Query в Looker Studio Data Source

SELECT
    ecommerce.transaction_id,
    PARSE_DATE('%Y%m%d', event_date) AS date,
    IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), traffic_source.source) AS source,
    IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), traffic_source.medium) AS medium,
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
    END AS traffic_source,
    geo.country,
    device.category AS device,
    ecommerce.purchase_revenue AS revenue,
    ecommerce.total_item_quantity AS items
FROM `claude-code-486108.analytics_411715710.events_*`
WHERE event_name = 'purchase'
    AND ecommerce.transaction_id IS NOT NULL
ORDER BY date DESC
