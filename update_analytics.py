#!/usr/bin/env python3
"""
Ping Spinning — GA4 Analytics (BigQuery) → Google Sheets

Источник данных: BigQuery (GA4 export: events_YYYYMMDD)
Выход: Google Sheets (8 вкладок дашборда)

Использование:
    python update_analytics.py          # обновить все вкладки
    python update_analytics.py daily    # только Daily Overview
    python update_analytics.py ecommerce traffic products pages geo retention transactions

Требования:
    pip install google-cloud-bigquery google-auth gspread
"""

import sys
import gspread
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================

BQ_PROJECT = "claude-code-486108"
BQ_DATASET = "analytics_411715710"
SPREADSHEET_ID = "1BJlK5UDgikDzszMFnrIFKtnvqoiTefgpvqkRieAbciw"
SERVICE_ACCOUNT_FILE = "service_account.json"
DEFAULT_DAYS = 90
EXCLUDED_COUNTRIES = ["China", "Hong Kong", "Kazakhstan", "Russia", "Georgia"]

SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/spreadsheets",
]

# ============================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
bq_client = bigquery.Client(credentials=credentials, project=BQ_PROJECT)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

# ============================================================
# УТИЛИТЫ
# ============================================================

def _date_range():
    """Возвращает start/end в формате YYYYMMDD для _TABLE_SUFFIX."""
    end = datetime.now()
    start = end - timedelta(days=DEFAULT_DAYS)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _events_table():
    return f"`{BQ_PROJECT}.{BQ_DATASET}.events_*`"


def _date_filter():
    start, end = _date_range()
    return f"_TABLE_SUFFIX BETWEEN '{start}' AND '{end}'"


def _country_filter():
    countries = ", ".join(f"'{c}'" for c in EXCLUDED_COUNTRIES)
    return f"geo.country NOT IN ({countries})"


def _base_where(extra=None, use_date_filter=True):
    """Стандартный WHERE: дата + страны + доп. условие."""
    parts = []
    if use_date_filter:
        parts.append(_date_filter())
    parts.append(_country_filter())
    if extra:
        parts.append(extra)
    return " AND ".join(parts)


def _ep(key, vtype="string_value"):
    """Извлечение event_param по ключу. vtype: string_value | int_value | float_value | double_value."""
    return f"(SELECT value.{vtype} FROM UNNEST(event_params) WHERE key = '{key}')"


# Упрощённая версия GA4 Default Channel Grouping
CHANNEL_GROUPING_SQL = f"""
    CASE
        WHEN {_ep('source')} = '(direct)' AND IFNULL({_ep('medium')}, '(none)') IN ('(none)', '(not set)') THEN 'Direct'
        WHEN {_ep('medium')} = 'organic' THEN 'Organic Search'
        WHEN REGEXP_CONTAINS({_ep('medium')}, r'^(cpc|ppc|paidsearch)$') THEN 'Paid Search'
        WHEN REGEXP_CONTAINS({_ep('medium')}, r'^(display|cpm|banner)$') THEN 'Display'
        WHEN REGEXP_CONTAINS({_ep('medium')}, r'^(social|social-network|social-media|sm|social_network|social_media)$')
            OR REGEXP_CONTAINS(IFNULL({_ep('source')}, ''), r'facebook|instagram|twitter|linkedin|pinterest|tiktok|youtube|reddit')
            THEN 'Organic Social'
        WHEN {_ep('medium')} = 'email' THEN 'Email'
        WHEN {_ep('medium')} = 'referral' THEN 'Referral'
        WHEN {_ep('medium')} = 'affiliate' THEN 'Affiliates'
        WHEN REGEXP_CONTAINS({_ep('medium')}, r'^(cpv|cpa|cpp|content-text)$') THEN 'Paid Other'
        ELSE 'Unassigned'
    END
"""


def run_query(sql):
    """Выполняет BigQuery SQL и возвращает список строк."""
    results = bq_client.query(sql).result()
    return [list(row.values()) for row in results]


def fmt_date(yyyymmdd):
    s = str(yyyymmdd)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def fmt_currency(val):
    return f"${float(val or 0):.0f}"


def fmt_percent(val):
    return f"{float(val or 0):.1f}%"


def write_to_sheet(sheet_name, headers, rows):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        sheet.clear()
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title=sheet_name, rows=max(len(rows) + 1, 100), cols=len(headers)
        )

    data = [headers] + rows
    if data:
        sheet.update(range_name="A1", values=data)

    sheet.format("1:1", {"textFormat": {"bold": True}})
    print(f"  ✓ {sheet_name}: {len(rows)} строк")
    return sheet


# ============================================================
# 1. DAILY OVERVIEW
# ============================================================

def update_daily_overview():
    print("→ Daily Overview...")
    sql = f"""
    WITH base AS (
        SELECT
            event_date,
            user_pseudo_id,
            {_ep('ga_session_id', 'int_value')} AS session_id,
            {_ep('session_engaged')} AS session_engaged,
            {_ep('engagement_time_msec', 'int_value')} AS engagement_time_msec,
            event_name,
            {_ep('ga_session_number', 'int_value')} AS session_number,
            ecommerce.transaction_id,
            ecommerce.purchase_revenue
        FROM {_events_table()}
        WHERE {_base_where()}
    ),
    sessions AS (
        SELECT
            event_date,
            user_pseudo_id,
            session_id,
            MAX(session_engaged) AS session_engaged,
            SUM(engagement_time_msec) AS eng_ms,
            MIN(session_number) AS session_number,
            COUNTIF(event_name = 'page_view') AS pages
        FROM base
        GROUP BY event_date, user_pseudo_id, session_id
    ),
    daily AS (
        SELECT
            event_date,
            COUNT(*) AS sessions,
            COUNT(DISTINCT user_pseudo_id) AS users,
            COUNTIF(session_number = 1) AS new_users,
            SAFE_DIVIDE(
                COUNTIF(session_engaged = '1'),
                COUNT(*)
            ) AS engagement_rate,
            ROUND(APPROX_QUANTILES(eng_ms, 100)[OFFSET(50)] / 1000, 1) AS median_eng_sec,
            ROUND(AVG(pages), 1) AS avg_pages,
            COUNTIF(pages = 1) AS sessions_1page,
            COUNTIF(pages BETWEEN 2 AND 5) AS sessions_2_5pages,
            COUNTIF(pages > 5) AS sessions_over5pages,
            (SELECT IFNULL(SUM(CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN purchase_revenue END), 0) FROM base b WHERE b.event_date = s.event_date) AS revenue,
            (SELECT COUNT(DISTINCT CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN transaction_id END) FROM base b WHERE b.event_date = s.event_date) AS purchases
        FROM sessions s
        GROUP BY event_date
    )
    SELECT * FROM daily ORDER BY event_date
    """

    rows = run_query(sql)
    headers = ["Date", "Sessions", "Users", "New Users", "Engagement Rate",
               "Median Eng. Time (s)", "Avg Pages/Session",
               "1 Page", "2-5 Pages", ">5 Pages", "Revenue", "Purchases"]

    formatted = []
    for r in rows:
        formatted.append([
            fmt_date(r[0]),
            int(r[1] or 0), int(r[2] or 0), int(r[3] or 0),
            fmt_percent(float(r[4] or 0) * 100),
            float(r[5] or 0),
            float(r[6] or 0),
            int(r[7] or 0),
            int(r[8] or 0),
            int(r[9] or 0),
            fmt_currency(r[10]),
            int(r[11] or 0),
        ])

    write_to_sheet("Daily Overview", headers, formatted)


# ============================================================
# 2. FUNNEL OVERVIEW
# ============================================================

CHANNEL_SQL = f"""
    CASE
        WHEN IFNULL({_ep('source')}, traffic_source.source) IN ('api.scraperforce.com', 'sanganzhu.com', 'jariblog.online') THEN 'Spam'
        WHEN IFNULL({_ep('medium')}, traffic_source.medium) IN ('paid', 'cpm') THEN 'Paid'
        WHEN IFNULL({_ep('source')}, traffic_source.source) IN ('ig', 'l.instagram.com')
             AND IFNULL({_ep('medium')}, traffic_source.medium) IN ('social', 'referral') THEN 'Social'
        WHEN IFNULL({_ep('medium')}, traffic_source.medium) = 'organic' THEN 'Organic'
        WHEN IFNULL({_ep('medium')}, traffic_source.medium) = 'email' THEN 'Email'
        WHEN IFNULL({_ep('source')}, IFNULL(traffic_source.source, '(direct)')) = '(direct)'
             AND IFNULL({_ep('medium')}, IFNULL(traffic_source.medium, '(none)')) IN ('(none)', '(not set)') THEN 'Direct'
        WHEN IFNULL({_ep('medium')}, traffic_source.medium) = 'referral' THEN 'Referral'
        ELSE 'Other'
    END
"""


def update_funnel_overview():
    print("→ Funnel Overview...")
    sql = f"""
    SELECT
        COUNT(DISTINCT CASE WHEN event_name = 'session_start' THEN user_pseudo_id END) AS sessions_users,
        COUNT(DISTINCT CASE WHEN event_name = 'session_start' THEN CONCAT(user_pseudo_id, CAST({_ep('ga_session_id', 'int_value')} AS STRING)) END) AS sessions_count,
        COUNT(DISTINCT CASE WHEN event_name = 'view_item' THEN user_pseudo_id END) AS view_item_users,
        COUNTIF(event_name = 'view_item') AS view_item_count,
        COUNT(DISTINCT CASE WHEN event_name = 'add_to_cart' THEN user_pseudo_id END) AS atc_users,
        COUNTIF(event_name = 'add_to_cart') AS atc_count,
        COUNT(DISTINCT CASE WHEN event_name = 'begin_checkout' THEN user_pseudo_id END) AS checkout_users,
        COUNTIF(event_name = 'begin_checkout') AS checkout_count,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' THEN user_pseudo_id END) AS purchase_users,
        COUNTIF(event_name = 'purchase') AS purchase_count
    FROM {_events_table()}
    WHERE {_country_filter()}
    """

    row = list(run_query(sql))[0]

    stages = [
        ("Sessions",       int(row[0] or 0), int(row[1] or 0)),
        ("View Item",      int(row[2] or 0), int(row[3] or 0)),
        ("Add to Cart",    int(row[4] or 0), int(row[5] or 0)),
        ("Begin Checkout", int(row[6] or 0), int(row[7] or 0)),
        ("Purchase",       int(row[8] or 0), int(row[9] or 0)),
    ]

    headers = ["Stage", "Users", "Events", "→ Next %", "Drop-off %"]
    formatted = []
    for i, (name, users, events) in enumerate(stages):
        if i < len(stages) - 1:
            next_users = stages[i + 1][1]
            to_next = f"{next_users / users * 100:.1f}%" if users > 0 else ""
            dropoff = f"{(1 - next_users / users) * 100:.1f}%" if users > 0 else ""
        else:
            to_next = ""
            dropoff = ""
        formatted.append([name, users, events, to_next, dropoff])

    write_to_sheet("Funnel Overview", headers, formatted)


# ============================================================
# 2b. FUNNEL BY SOURCE
# ============================================================

def update_funnel_by_source():
    print("→ Funnel by Source...")
    sql = f"""
    WITH base AS (
        SELECT
            user_pseudo_id,
            {_ep('ga_session_id', 'int_value')} AS session_id,
            event_name,
            {_ep('engagement_time_msec', 'int_value')} AS engagement_time_msec,
            {CHANNEL_SQL} AS channel
        FROM {_events_table()}
    ),
    sessions AS (
        SELECT
            channel,
            user_pseudo_id,
            session_id,
            SUM(engagement_time_msec) AS eng_ms,
            COUNTIF(event_name = 'page_view') AS pages,
            MAX(CASE WHEN event_name = 'view_item' THEN 1 ELSE 0 END) AS has_view_item,
            MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) AS has_atc,
            MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS has_checkout,
            MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS has_purchase
        FROM base
        GROUP BY channel, user_pseudo_id, session_id
    )
    SELECT
        channel,
        COUNT(*) AS sessions,
        ROUND(APPROX_QUANTILES(eng_ms, 100)[OFFSET(50)] / 1000, 1) AS median_eng_sec,
        ROUND(AVG(pages), 1) AS avg_pages,
        COUNTIF(has_view_item = 1) AS view_item,
        COUNTIF(has_atc = 1) AS add_to_cart,
        COUNTIF(has_checkout = 1) AS begin_checkout,
        COUNTIF(has_purchase = 1) AS purchase
    FROM sessions
    GROUP BY channel
    ORDER BY sessions DESC
    """

    rows = run_query(sql)
    headers = ["Source", "Sessions", "Median Eng. Time (s)", "Avg Pages/Session",
               "View Item", "Add to Cart", "Begin Checkout", "Purchase",
               "View→Cart %", "Cart→Purchase %"]

    formatted = []
    for r in rows:
        sessions = int(r[1] or 0)
        view_item = int(r[4] or 0)
        atc = int(r[5] or 0)
        checkout = int(r[6] or 0)
        purchase = int(r[7] or 0)

        view_to_cart = fmt_percent(atc / view_item * 100) if view_item > 0 else ""
        cart_to_purchase = fmt_percent(purchase / atc * 100) if atc > 0 else ""

        formatted.append([
            r[0],
            sessions,
            float(r[2] or 0),
            float(r[3] or 0),
            view_item,
            atc,
            checkout,
            purchase,
            view_to_cart,
            cart_to_purchase,
        ])

    write_to_sheet("Funnel by Source", headers, formatted)


# ============================================================
# 2c. FUNNEL WEEKLY
# ============================================================

def update_funnel_weekly():
    print("→ Funnel Weekly...")
    sql = f"""
    WITH events AS (
        SELECT
            FORMAT_DATE('%G-W%V', PARSE_DATE('%Y%m%d', event_date)) AS week,
            user_pseudo_id,
            event_name,
            {CHANNEL_SQL} AS channel
        FROM {_events_table()}
        WHERE event_name IN ('session_start', 'view_item', 'add_to_cart', 'begin_checkout', 'purchase')
    )
    SELECT
        week,
        channel,
        COUNT(DISTINCT CASE WHEN event_name = 'session_start' THEN user_pseudo_id END) AS sessions,
        COUNT(DISTINCT CASE WHEN event_name = 'view_item' THEN user_pseudo_id END) AS view_item,
        COUNT(DISTINCT CASE WHEN event_name = 'add_to_cart' THEN user_pseudo_id END) AS atc,
        COUNT(DISTINCT CASE WHEN event_name = 'begin_checkout' THEN user_pseudo_id END) AS checkout,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' THEN user_pseudo_id END) AS purchase
    FROM events
    GROUP BY week, channel
    ORDER BY week, channel
    """

    rows = run_query(sql)
    headers = ["Week", "Source", "Sessions", "View Item", "Add to Cart",
               "Checkout", "Purchase", "Sess→VI %", "VI→ATC %"]

    formatted = []
    for r in rows:
        sess = int(r[2] or 0)
        vi = int(r[3] or 0)
        atc = int(r[4] or 0)
        chk = int(r[5] or 0)
        pur = int(r[6] or 0)

        s2vi = fmt_percent(vi / sess * 100) if sess > 0 else ""
        vi2atc = fmt_percent(atc / vi * 100) if vi > 0 else ""

        formatted.append([r[0], r[1], sess, vi, atc, chk, pur, s2vi, vi2atc])

    write_to_sheet("Funnel Weekly", headers, formatted)


# ============================================================
# 2d. PRODUCT VIEWS WEEKLY
# ============================================================

def update_product_views_weekly():
    print("→ Product Views Weekly...")
    sql = f"""
    WITH events AS (
        SELECT
            FORMAT_DATE('%G-W%V', PARSE_DATE('%Y%m%d', event_date)) AS week,
            user_pseudo_id,
            {CHANNEL_SQL} AS channel
        FROM {_events_table()}
        WHERE event_name = 'view_item'
    ),
    user_views AS (
        SELECT
            week,
            channel,
            user_pseudo_id,
            COUNT(*) AS view_count
        FROM events
        GROUP BY week, channel, user_pseudo_id
    )
    SELECT
        week,
        channel,
        COUNT(*) AS users,
        ROUND(AVG(view_count), 1) AS avg_views,
        APPROX_QUANTILES(view_count, 100)[OFFSET(50)] AS median_views,
        COUNTIF(view_count = 1) AS viewed_1,
        COUNTIF(view_count BETWEEN 2 AND 5) AS viewed_2_5,
        COUNTIF(view_count > 5) AS viewed_over5
    FROM user_views
    GROUP BY week, channel
    ORDER BY week, channel
    """

    rows = run_query(sql)
    headers = ["Week", "Source", "Users", "Avg Products Viewed",
               "Median Products Viewed", "Viewed 1", "Viewed 2-5", "Viewed >5"]

    formatted = []
    for r in rows:
        formatted.append([
            r[0], r[1],
            int(r[2] or 0),
            float(r[3] or 0),
            int(r[4] or 0),
            int(r[5] or 0),
            int(r[6] or 0),
            int(r[7] or 0),
        ])

    write_to_sheet("Product Views Weekly", headers, formatted)


# ============================================================
# 3. TRAFFIC SOURCES
# ============================================================

def update_traffic_sources():
    print("→ Traffic Sources...")

    # Часть 1: Каналы
    sql_channels = f"""
    WITH sessions AS (
        SELECT
            user_pseudo_id,
            {_ep('ga_session_id', 'int_value')} AS session_id,
            {CHANNEL_GROUPING_SQL} AS channel,
            {_ep('session_engaged')} AS session_engaged,
            event_name,
            ecommerce.transaction_id,
            ecommerce.purchase_revenue
        FROM {_events_table()}
        WHERE {_base_where()}
    )
    SELECT
        channel,
        COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING))) AS sessions,
        COUNT(DISTINCT user_pseudo_id) AS users,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_engaged = '1' THEN CONCAT(user_pseudo_id, CAST(session_id AS STRING)) END),
            COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING)))
        ) AS engagement_rate,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN transaction_id END) AS purchases,
        IFNULL(SUM(CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN purchase_revenue END), 0) AS revenue
    FROM sessions
    GROUP BY channel
    ORDER BY sessions DESC
    """

    ch_rows = run_query(sql_channels)
    ch_headers = ["Channel", "Sessions", "Users", "Engagement Rate", "Purchases", "Revenue"]
    ch_data = [[r[0], int(r[1] or 0), int(r[2] or 0), fmt_percent(float(r[3] or 0) * 100),
                 int(r[4] or 0), fmt_currency(r[5])] for r in ch_rows]

    # Часть 2: Source / Medium
    sql_source = f"""
    WITH sessions AS (
        SELECT
            user_pseudo_id,
            {_ep('ga_session_id', 'int_value')} AS session_id,
            IFNULL({_ep('source')}, '(direct)') AS source,
            IFNULL({_ep('medium')}, '(none)') AS medium,
            {_ep('session_engaged')} AS session_engaged,
            event_name,
            ecommerce.transaction_id,
            ecommerce.purchase_revenue
        FROM {_events_table()}
        WHERE {_base_where()}
    )
    SELECT
        source,
        medium,
        COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING))) AS sessions,
        COUNT(DISTINCT user_pseudo_id) AS users,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_engaged = '1' THEN CONCAT(user_pseudo_id, CAST(session_id AS STRING)) END),
            COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING)))
        ) AS engagement_rate,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN transaction_id END) AS purchases,
        IFNULL(SUM(CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN purchase_revenue END), 0) AS revenue
    FROM sessions
    GROUP BY source, medium
    ORDER BY sessions DESC
    LIMIT 20
    """

    sm_rows = run_query(sql_source)
    sm_headers = ["Source", "Medium", "Sessions", "Users", "Engagement Rate", "Revenue"]
    sm_data = [[r[0], r[1], int(r[2] or 0), int(r[3] or 0),
                 fmt_percent(float(r[4] or 0) * 100), fmt_currency(r[6])] for r in sm_rows]

    # Записываем обе таблицы на один лист
    all_data = (
        [ch_headers] + ch_data +
        [[""]] +
        [["Source / Medium"]] +
        [sm_headers] + sm_data
    )

    try:
        sheet = spreadsheet.worksheet("Traffic Sources")
        sheet.clear()
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="Traffic Sources", rows=100, cols=6)

    sheet.update(range_name="A1", values=all_data)
    sheet.format("1:1", {"textFormat": {"bold": True}})
    sm_header_row = len(ch_data) + 3
    sheet.format(f"{sm_header_row}:{sm_header_row}", {"textFormat": {"bold": True}})
    sm_col_row = sm_header_row + 1
    sheet.format(f"{sm_col_row}:{sm_col_row}", {"textFormat": {"bold": True}})
    print(f"  ✓ Traffic Sources: {len(ch_data)} channels + {len(sm_data)} sources")


# ============================================================
# 4. TOP PRODUCTS (Item-scoped)
# ============================================================

def update_top_products():
    print("→ Top Products...")
    sql = f"""
    WITH item_events AS (
        SELECT
            event_name,
            item.item_name AS item_name,
            item.item_revenue AS item_revenue,
            item.quantity AS quantity
        FROM {_events_table()},
            UNNEST(items) AS item
        WHERE {_date_filter()}
            AND item.item_name IS NOT NULL
    )
    SELECT
        item_name,
        COUNTIF(event_name = 'view_item') AS views,
        COUNTIF(event_name = 'add_to_cart') AS added_to_cart,
        COUNTIF(event_name = 'begin_checkout') AS checked_out,
        COUNTIF(event_name = 'purchase') AS purchased,
        IFNULL(SUM(CASE WHEN event_name = 'purchase' THEN item_revenue END), 0) AS revenue
    FROM item_events
    GROUP BY item_name
    ORDER BY views DESC
    LIMIT 50
    """

    rows = run_query(sql)
    headers = ["Product", "Views", "Added to Cart", "Checked Out",
               "Purchased", "Revenue", "View-to-Cart Rate"]

    formatted = []
    for r in rows:
        views = int(r[1] or 0)
        atc = int(r[2] or 0)
        vtc = f"{atc / views * 100:.1f}%" if views > 0 else "0.0%"
        formatted.append([r[0], views, atc, int(r[3] or 0), int(r[4] or 0), fmt_currency(r[5]), vtc])

    write_to_sheet("Top Products", headers, formatted)


# ============================================================
# 5. TOP PAGES
# ============================================================

def update_top_pages():
    print("→ Top Pages...")
    sql = f"""
    WITH page_data AS (
        SELECT
            IFNULL({_ep('page_location')}, {_ep('page_path')}) AS page_path,
            user_pseudo_id,
            {_ep('session_engaged')} AS session_engaged,
            event_name,
            ecommerce.transaction_id,
            ecommerce.purchase_revenue
        FROM {_events_table()}
        WHERE {_base_where("event_name IN ('page_view', 'purchase')")}
    )
    SELECT
        REGEXP_EXTRACT(page_path, r'https?://[^/]+(/.*)') AS path,
        COUNTIF(event_name = 'page_view') AS views,
        COUNT(DISTINCT user_pseudo_id) AS users,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_engaged = '1' THEN user_pseudo_id END),
            COUNT(DISTINCT user_pseudo_id)
        ) AS engagement_rate,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN transaction_id END) AS purchases,
        IFNULL(SUM(CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN purchase_revenue END), 0) AS revenue
    FROM page_data
    WHERE page_path IS NOT NULL
    GROUP BY path
    HAVING path IS NOT NULL
    ORDER BY views DESC
    LIMIT 50
    """

    rows = run_query(sql)
    headers = ["Page", "Views", "Users", "Engagement Rate", "Purchases", "Revenue"]
    formatted = [[r[0] or '/', int(r[1] or 0), int(r[2] or 0),
                   fmt_percent(float(r[3] or 0) * 100), int(r[4] or 0), fmt_currency(r[5])]
                  for r in rows]

    write_to_sheet("Top Pages", headers, formatted)


# ============================================================
# 6. DEVICES & GEO
# ============================================================

def update_devices_geo():
    print("→ Devices & Geo...")

    # Устройства
    sql_devices = f"""
    SELECT
        device.category AS device_category,
        COUNT(DISTINCT CONCAT(user_pseudo_id,
            CAST({_ep('ga_session_id', 'int_value')} AS STRING))) AS sessions,
        COUNT(DISTINCT user_pseudo_id) AS users,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN {_ep('session_engaged')} = '1'
                THEN CONCAT(user_pseudo_id, CAST({_ep('ga_session_id', 'int_value')} AS STRING)) END),
            COUNT(DISTINCT CONCAT(user_pseudo_id,
                CAST({_ep('ga_session_id', 'int_value')} AS STRING)))
        ) AS engagement_rate,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' AND ecommerce.transaction_id IS NOT NULL
            THEN ecommerce.transaction_id END) AS purchases,
        IFNULL(SUM(CASE WHEN event_name = 'purchase' AND ecommerce.transaction_id IS NOT NULL
            THEN ecommerce.purchase_revenue END), 0) AS revenue
    FROM {_events_table()}
    WHERE {_base_where()}
    GROUP BY device_category
    ORDER BY sessions DESC
    """

    dev_rows = run_query(sql_devices)
    dev_headers = ["Device", "Sessions", "Users", "Engagement Rate", "Purchases", "Revenue"]
    dev_data = [[r[0], int(r[1] or 0), int(r[2] or 0), fmt_percent(float(r[3] or 0) * 100),
                  int(r[4] or 0), fmt_currency(r[5])] for r in dev_rows]

    # Страны
    sql_geo = f"""
    SELECT
        geo.country,
        COUNT(DISTINCT CONCAT(user_pseudo_id,
            CAST({_ep('ga_session_id', 'int_value')} AS STRING))) AS sessions,
        COUNT(DISTINCT user_pseudo_id) AS users,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN {_ep('session_engaged')} = '1'
                THEN CONCAT(user_pseudo_id, CAST({_ep('ga_session_id', 'int_value')} AS STRING)) END),
            COUNT(DISTINCT CONCAT(user_pseudo_id,
                CAST({_ep('ga_session_id', 'int_value')} AS STRING)))
        ) AS engagement_rate,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' AND ecommerce.transaction_id IS NOT NULL
            THEN ecommerce.transaction_id END) AS purchases,
        IFNULL(SUM(CASE WHEN event_name = 'purchase' AND ecommerce.transaction_id IS NOT NULL
            THEN ecommerce.purchase_revenue END), 0) AS revenue
    FROM {_events_table()}
    WHERE {_base_where()}
    GROUP BY geo.country
    ORDER BY sessions DESC
    LIMIT 20
    """

    geo_rows = run_query(sql_geo)
    geo_headers = ["Country", "Sessions", "Users", "Engagement Rate", "Purchases", "Revenue"]
    geo_data = [[r[0], int(r[1] or 0), int(r[2] or 0), fmt_percent(float(r[3] or 0) * 100),
                  int(r[4] or 0), fmt_currency(r[5])] for r in geo_rows]

    # Обе таблицы на один лист
    all_data = (
        [dev_headers] + dev_data +
        [[""]] +
        [["Geography"]] +
        [geo_headers] + geo_data
    )

    try:
        sheet = spreadsheet.worksheet("Devices & Geo")
        sheet.clear()
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="Devices & Geo", rows=100, cols=6)

    sheet.update(range_name="A1", values=all_data)
    sheet.format("1:1", {"textFormat": {"bold": True}})
    geo_label_row = len(dev_data) + 2
    sheet.format(f"{geo_label_row}:{geo_label_row}", {"textFormat": {"bold": True}})
    geo_header_row = geo_label_row + 1
    sheet.format(f"{geo_header_row}:{geo_header_row}", {"textFormat": {"bold": True}})
    print(f"  ✓ Devices & Geo: {len(dev_data)} devices + {len(geo_data)} countries")


# ============================================================
# 7. RETENTION
# ============================================================

def update_retention():
    print("→ Retention...")
    sql = f"""
    WITH user_sessions AS (
        SELECT
            user_pseudo_id,
            {_ep('ga_session_id', 'int_value')} AS session_id,
            {_ep('ga_session_number', 'int_value')} AS session_number,
            {_ep('session_engaged')} AS session_engaged,
            event_name,
            ecommerce.transaction_id,
            ecommerce.purchase_revenue
        FROM {_events_table()}
        WHERE {_base_where()}
    ),
    classified AS (
        SELECT
            CASE WHEN session_number = 1 THEN 'new' ELSE 'returning' END AS user_type,
            user_pseudo_id,
            session_id,
            session_engaged,
            event_name,
            transaction_id,
            purchase_revenue
        FROM user_sessions
    )
    SELECT
        user_type,
        COUNT(DISTINCT user_pseudo_id) AS users,
        COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING))) AS sessions,
        IFNULL(SUM(CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN purchase_revenue END), 0) AS revenue,
        COUNT(DISTINCT CASE WHEN event_name = 'purchase' AND transaction_id IS NOT NULL THEN transaction_id END) AS purchases,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_engaged = '1' THEN CONCAT(user_pseudo_id, CAST(session_id AS STRING)) END),
            COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id AS STRING)))
        ) AS engagement_rate
    FROM classified
    GROUP BY user_type
    ORDER BY users DESC
    """

    rows = run_query(sql)
    headers = ["User Type", "Users", "Sessions", "Revenue", "Purchases", "Engagement Rate"]
    formatted = [[r[0], int(r[1] or 0), int(r[2] or 0), fmt_currency(r[3]),
                   int(r[4] or 0), fmt_percent(float(r[5] or 0) * 100)]
                  for r in rows]

    write_to_sheet("Retention", headers, formatted)


# ============================================================
# 8. TRANSACTIONS
# ============================================================

def update_transactions():
    print("→ Transactions...")
    sql = f"""
    SELECT
        ecommerce.transaction_id,
        event_date,
        IFNULL({_ep('source')}, traffic_source.source) AS source,
        IFNULL({_ep('medium')}, traffic_source.medium) AS medium,
        {CHANNEL_GROUPING_SQL} AS channel,
        geo.country,
        device.category AS device,
        ecommerce.purchase_revenue AS revenue,
        ecommerce.total_item_quantity AS items
    FROM {_events_table()}
    WHERE event_name = 'purchase' AND ecommerce.transaction_id IS NOT NULL
    ORDER BY event_date DESC
    LIMIT 500
    """

    rows = run_query(sql)
    headers = ["Transaction ID", "Date", "Source", "Medium", "Channel",
               "Country", "Device", "Revenue", "Items"]

    formatted = []
    for r in rows:
        tid = r[0]
        if tid == "(not set)" or not tid:
            continue
        formatted.append([
            tid,
            fmt_date(r[1]),
            r[2] or '(direct)',
            r[3] or '(none)',
            r[4],
            r[5] or '',
            r[6] or '',
            fmt_currency(r[7]),
            int(r[8] or 0),
        ])

    write_to_sheet("Transactions", headers, formatted)


# ============================================================
# MAIN
# ============================================================

REPORTS = {
    "daily": update_daily_overview,
    "funnel": lambda: (update_funnel_overview(), update_funnel_by_source(), update_funnel_weekly(), update_product_views_weekly()),
    "traffic": update_traffic_sources,
    "products": update_top_products,
    "pages": update_top_pages,
    "geo": update_devices_geo,
    "retention": update_retention,
    "transactions": update_transactions,
}


def update_all():
    print(f"Ping Spinning — GA4 Analytics Update (BigQuery)")
    print(f"Period: last {DEFAULT_DAYS} days")
    print(f"Excluded countries: {', '.join(EXCLUDED_COUNTRIES)}")
    print("=" * 50)

    for name, func in REPORTS.items():
        try:
            func()
        except Exception as e:
            print(f"  ✗ Error in {name}: {e}")

    print("=" * 50)
    print("Done!")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        update_all()
    else:
        for arg in args:
            if arg in REPORTS:
                REPORTS[arg]()
            else:
                print(f"Unknown report: {arg}")
                print(f"Available: {', '.join(REPORTS.keys())}")
