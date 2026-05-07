#!/usr/bin/env python3
from __future__ import annotations
"""Generate Pinkspink daily/weekly AI report via Claude API.

Pulls metrics from BigQuery, asks Claude to interpret them using the
pinkspink-analytics-coach skill content as the system prompt, saves the
markdown report locally, and POSTs it to Telegram.

Run:
    python scripts/ai_report.py --grain daily
    python scripts/ai_report.py --grain weekly

Required environment:
    ANTHROPIC_API_KEY     — Claude API key
    TELEGRAM_BOT_TOKEN    — Telegram bot token
    TELEGRAM_CHAT_ID      — Telegram chat id
    GOOGLE_APPLICATION_CREDENTIALS optional, otherwise looks for
        service_account.json in repo root
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import anthropic
from google.cloud import bigquery
from google.oauth2 import service_account

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _telegram import send_telegram  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / ".claude" / "skills" / "pinkspink-analytics-coach"
REPORTS_DIR = ROOT / "reports"
CHANGELOG_FILE = ROOT / "changelog.md"
SERVICE_ACCOUNT_FILE = ROOT / "service_account.json"

BQ_PROJECT = "claude-code-486108"
BQ_DATASET = "analytics_411715710"
EXCLUDED_COUNTRIES = ("China", "Hong Kong", "South Korea", "Singapore", "Georgia", "Kazakhstan")
SPAM_SOURCES = ("api.scraperforce.com", "sanganzhu.com", "jariblog.online")

CLAUDE_MODEL = "claude-sonnet-4-6"


def bq_client() -> bigquery.Client:
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE)
    )
    return bigquery.Client(credentials=creds, project=BQ_PROJECT)


def fetch_session_facts(client: bigquery.Client, start: date, end: date) -> list[dict]:
    """Daily session-level aggregates by channel/country/device for date range.

    Returns rows with: day, channel, country, device, sessions,
    sessions_with_view, sessions_with_atc, sessions_with_checkout,
    sessions_with_purchase, new_users.
    """
    sql = f"""
    WITH events AS (
      SELECT
        PARSE_DATE('%Y%m%d', event_date) AS day,
        user_pseudo_id,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
        event_name,
        geo.country AS country,
        device.category AS device,
        IFNULL(traffic_source.source, '(direct)') AS source,
        IFNULL(traffic_source.medium, '(none)') AS medium
      FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
      WHERE _TABLE_SUFFIX BETWEEN @start AND @end
        AND geo.country NOT IN UNNEST(@excluded_countries)
        AND IFNULL(traffic_source.source, '') NOT IN UNNEST(@spam_sources)
    ),
    classified AS (
      SELECT
        *,
        CASE
          WHEN medium IN ('paid', 'cpm') OR REGEXP_CONTAINS(medium, r'(?i)instagram_|facebook_') THEN 'Paid'
          WHEN source IN ('ig', 'l.instagram.com') AND medium IN ('social', 'referral') THEN 'Social'
          WHEN medium = 'organic' THEN 'Organic'
          WHEN medium = 'email' THEN 'Email'
          WHEN source = '(direct)' AND medium IN ('(none)', '(not set)') THEN 'Direct'
          WHEN medium = 'referral' THEN 'Referral'
          ELSE 'Other'
        END AS channel
      FROM events
    ),
    sessions AS (
      SELECT
        day,
        user_pseudo_id,
        session_id,
        ANY_VALUE(country) AS country,
        ANY_VALUE(device) AS device,
        ANY_VALUE(channel) AS channel,
        MAX(IF(event_name = 'first_visit', 1, 0)) AS is_new,
        MAX(IF(event_name = 'view_item', 1, 0)) AS has_view,
        MAX(IF(event_name = 'add_to_cart', 1, 0)) AS has_atc,
        MAX(IF(event_name = 'begin_checkout', 1, 0)) AS has_checkout,
        MAX(IF(event_name = 'purchase', 1, 0)) AS has_purchase
      FROM classified
      WHERE session_id IS NOT NULL
      GROUP BY day, user_pseudo_id, session_id
    )
    SELECT
      day,
      channel,
      country,
      device,
      COUNT(*) AS sessions,
      SUM(is_new) AS new_user_sessions,
      SUM(has_view) AS sessions_with_view,
      SUM(has_atc) AS sessions_with_atc,
      SUM(has_checkout) AS sessions_with_checkout,
      SUM(has_purchase) AS sessions_with_purchase
    FROM sessions
    GROUP BY day, channel, country, device
    """

    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start", "STRING", start.strftime("%Y%m%d")),
                bigquery.ScalarQueryParameter("end", "STRING", end.strftime("%Y%m%d")),
                bigquery.ArrayQueryParameter("excluded_countries", "STRING", list(EXCLUDED_COUNTRIES)),
                bigquery.ArrayQueryParameter("spam_sources", "STRING", list(SPAM_SOURCES)),
            ]
        ),
    )
    return [dict(r) for r in job]


def aggregate_period(rows: list[dict], days: set[date]) -> dict:
    """Roll up rows belonging to `days` into per-week metric averages.

    All session counts are normalized to weekly averages (÷ len(days)/7),
    so target (7d) and baseline (28d) are directly comparable.
    """
    subset = [r for r in rows if r["day"] in days]
    n = max(len(days), 1)
    n_weeks = n / 7.0  # 7d → 1.0, 28d → 4.0

    sessions = sum(r["sessions"] for r in subset)
    atc = sum(r["sessions_with_atc"] for r in subset)
    checkouts = sum(r["sessions_with_checkout"] for r in subset)
    purchases = sum(r["sessions_with_purchase"] for r in subset)
    views = sum(r["sessions_with_view"] for r in subset)
    new_sessions = sum(r["new_user_sessions"] for r in subset)

    by_channel: dict[str, int] = {}
    by_country: dict[str, int] = {}
    by_device: dict[str, int] = {}
    country_channel: dict[str, dict[str, int]] = {}
    country_funnel: dict[str, dict] = {}
    for r in subset:
        c, ch = r["country"], r["channel"]
        by_channel[ch] = by_channel.get(ch, 0) + r["sessions"]
        by_country[c] = by_country.get(c, 0) + r["sessions"]
        by_device[r["device"]] = by_device.get(r["device"], 0) + r["sessions"]
        if c not in country_channel:
            country_channel[c] = {}
        country_channel[c][ch] = country_channel[c].get(ch, 0) + r["sessions"]
        if c not in country_funnel:
            country_funnel[c] = {"sessions": 0, "view": 0, "atc": 0, "checkout": 0, "purchase": 0}
        cf = country_funnel[c]
        cf["sessions"] += r["sessions"]
        cf["view"] += r["sessions_with_view"]
        cf["atc"] += r["sessions_with_atc"]
        cf["checkout"] += r["sessions_with_checkout"]
        cf["purchase"] += r["sessions_with_purchase"]

    top8 = sorted(country_funnel.items(), key=lambda x: -x[1]["sessions"])[:8]

    def pct(num: int, den: int) -> float:
        return round(100.0 * num / den, 2) if den else 0.0

    def w(v: int | float) -> float:
        return round(v / n_weeks, 1)

    return {
        "days_count": len(days),
        "weeks_count": round(n_weeks, 2),
        # All session counts below are PER-WEEK averages
        "sessions_per_week": w(sessions),
        "atc_per_week": w(atc),
        "checkouts_per_week": w(checkouts),
        "purchases_per_week": w(purchases),
        "atc_rate_pct": pct(atc, sessions),
        "view_to_atc_pct": pct(atc, views),
        "checkout_rate_pct": pct(checkouts, sessions),
        "purchase_rate_pct": pct(purchases, sessions),
        "new_sessions_share_pct": pct(new_sessions, sessions),
        # Per-week averages by channel / country
        "channels_sessions_per_week": {
            k: w(v) for k, v in sorted(by_channel.items(), key=lambda x: -x[1])
        },
        "devices_sessions": dict(sorted(by_device.items(), key=lambda x: -x[1])),
        # Cross-dimensional: weekly avg sessions per country per channel
        "country_channel_sessions_per_week": {
            c: {ch: w(v) for ch, v in sorted(country_channel[c].items(), key=lambda x: -x[1])}
            for c, _ in top8
        },
        # Per-country funnel depth as weekly averages (top 8 by sessions)
        "top_countries_funnel_per_week": [
            {
                "country": c,
                "sessions": w(fv["sessions"]),
                "view": w(fv["view"]),
                "atc": w(fv["atc"]),
                "checkout": w(fv["checkout"]),
                "purchase": w(fv["purchase"]),
            }
            for c, fv in top8
        ],
    }


def fetch_atc_sessions(client: bigquery.Client, start: date, end: date) -> list[dict]:
    """Individual sessions with ATC events — includes city, channel, full funnel."""
    sql = f"""
    WITH events AS (
      SELECT
        PARSE_DATE('%Y%m%d', event_date) AS day,
        user_pseudo_id,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
        event_name,
        geo.country AS country,
        geo.city AS city,
        device.category AS device,
        IFNULL(traffic_source.source, '(direct)') AS source,
        IFNULL(traffic_source.medium, '(none)') AS medium
      FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
      WHERE _TABLE_SUFFIX BETWEEN @start AND @end
        AND geo.country NOT IN UNNEST(@excluded_countries)
        AND IFNULL(traffic_source.source, '') NOT IN UNNEST(@spam_sources)
    ),
    classified AS (
      SELECT *,
        CASE
          WHEN medium IN ('paid', 'cpm') OR REGEXP_CONTAINS(medium, r'(?i)instagram_|facebook_') THEN 'Paid'
          WHEN source IN ('ig', 'l.instagram.com') AND medium IN ('social', 'referral') THEN 'Social'
          WHEN medium = 'organic' THEN 'Organic'
          WHEN medium = 'email' THEN 'Email'
          WHEN source = '(direct)' AND medium IN ('(none)', '(not set)') THEN 'Direct'
          WHEN medium = 'referral' THEN 'Referral'
          ELSE 'Other'
        END AS channel
      FROM events
    ),
    sessions AS (
      SELECT
        day, user_pseudo_id, session_id,
        ANY_VALUE(country) AS country,
        ANY_VALUE(city) AS city,
        ANY_VALUE(device) AS device,
        ANY_VALUE(channel) AS channel,
        ANY_VALUE(source) AS source,
        MAX(IF(event_name = 'view_item', 1, 0)) AS has_view,
        MAX(IF(event_name = 'add_to_cart', 1, 0)) AS has_atc,
        MAX(IF(event_name = 'begin_checkout', 1, 0)) AS has_checkout,
        MAX(IF(event_name = 'purchase', 1, 0)) AS has_purchase
      FROM classified
      WHERE session_id IS NOT NULL
      GROUP BY day, user_pseudo_id, session_id
    )
    SELECT day, country, city, device, channel, source,
           has_view, has_atc, has_checkout, has_purchase
    FROM sessions
    WHERE has_atc = 1
    ORDER BY day, country
    """
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start", "STRING", start.strftime("%Y%m%d")),
                bigquery.ScalarQueryParameter("end", "STRING", end.strftime("%Y%m%d")),
                bigquery.ArrayQueryParameter("excluded_countries", "STRING", list(EXCLUDED_COUNTRIES)),
                bigquery.ArrayQueryParameter("spam_sources", "STRING", list(SPAM_SOURCES)),
            ]
        ),
    )
    result = []
    for r in job:
        stages = ["view"] if r["has_view"] else []
        stages.append("ATC")
        if r["has_checkout"]:
            stages.append("checkout")
        if r["has_purchase"]:
            stages.append("purchase")
        result.append({
            "date": r["day"].isoformat(),
            "country": r["country"],
            "city": r["city"] or "",
            "device": r["device"],
            "channel": r["channel"],
            "source": r["source"],
            "funnel": " → ".join(stages),
        })
    return result


DAILY_LOOKBACK_DAYS = 10


def daily_lookback_window(today_utc: date) -> tuple[date, date]:
    """Date range for the daily probe query (covers latest target + baseline)."""
    return today_utc - timedelta(days=DAILY_LOOKBACK_DAYS), today_utc - timedelta(days=1)


def pick_latest_day(rows: list[dict]) -> date | None:
    """Return the most recent date in rows that has sessions > 0."""
    days = sorted({r["day"] for r in rows if r["sessions"] > 0}, reverse=True)
    return days[0] if days else None


def weekly_window(today_utc: date) -> tuple[date, date, set[date], set[date]]:
    """Last completed Mon-Sun + 4 prior full weeks as baseline."""
    weekday = today_utc.weekday()  # Monday=0
    days_to_last_sunday = weekday + 1
    last_sunday = today_utc - timedelta(days=days_to_last_sunday)
    last_monday = last_sunday - timedelta(days=6)
    target = {last_monday + timedelta(days=i) for i in range(7)}
    baseline = {last_monday - timedelta(days=i) for i in range(1, 29)}
    return last_monday, last_sunday, target, baseline


def load_recent_changelog(today_utc: date, window_days: int) -> str:
    """Return changelog entries from last `window_days` days as markdown bullets.

    Empty string if file missing or no entries match.
    """
    if not CHANGELOG_FILE.exists():
        return ""
    cutoff = today_utc - timedelta(days=window_days)
    entry_re = re.compile(r"^-\s+\*\*(\d{4}-\d{2}-\d{2})")
    entries = []
    for line in CHANGELOG_FILE.read_text(encoding="utf-8").splitlines():
        m = entry_re.match(line)
        if not m:
            continue
        try:
            entry_date = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if entry_date >= cutoff:
            entries.append(line.strip())
    return "\n".join(entries)


def load_skill() -> str:
    parts = [(SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")]
    refs_dir = SKILL_DIR / "references"
    if refs_dir.exists():
        for f in sorted(refs_dir.glob("*.md")):
            parts.append(
                f"\n\n---\n# References file: {f.name}\n\n"
                + f.read_text(encoding="utf-8")
            )
    return "".join(parts)


def call_claude(skill_content: str, user_prompt: str, max_tokens: int) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": skill_content,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(b.text for b in response.content if b.type == "text")


def changelog_block(entries: str) -> str:
    if not entries:
        return ""
    return (
        "\n\nИзменения с нашей стороны (из changelog.md). Используй для "
        "confounder-чека — если метрика двинулась после такого изменения, явно "
        "свяжи их в отчёте:\n```\n" + entries + "\n```"
    )


def atc_block(atc_sessions: list[dict]) -> str:
    if not atc_sessions:
        return "\n\nATC sessions in target period: none."
    lines = [
        f"  {s['date']} | {s['country']}/{s['city'] or '?'} | {s['device']} "
        f"| {s['channel']}/{s['source']} | {s['funnel']}"
        for s in atc_sessions
    ]
    return (
        "\n\nИндивидуальные ATC-сессии целевого периода (с городом, каналом, воронкой):\n"
        + "\n".join(lines)
    )


def build_daily_prompt(
    target: date,
    today_utc: date,
    target_data: dict,
    baseline_data: dict,
    changelog_entries: str,
    atc_sessions: list[dict],
) -> str:
    age = (today_utc - target).days
    if age <= 1:
        freshness = "Данные за вчера:"
    else:
        freshness = (
            f"Данные за {target.isoformat()} (это {age} дн. назад — GA4-export "
            f"за более свежие даты ещё не готов, что нормально):"
        )
    return (
        f"Сегодня daily report для Pinkspink за {target.isoformat()} (UTC).\n\n"
        f"{freshness}\n```json\n"
        f"{json.dumps(target_data, indent=2, ensure_ascii=False)}\n```\n\n"
        f"Данные за trailing-7-day baseline (7 дней до целевого дня):\n```json\n"
        f"{json.dumps(baseline_data, indent=2, ensure_ascii=False)}\n```"
        f"{atc_block(atc_sessions)}"
        f"{changelog_block(changelog_entries)}\n\n"
        "Сгенерируй daily report по шаблону из references/report-template.md (на русском).\n"
        "ВАЖНО ПРО ДАННЫЕ:\n"
        "- Все счётчики сессий (sessions_per_week, channels_sessions_per_week, "
        "country_channel_sessions_per_week, top_countries_funnel_per_week) — "
        "это средние за НЕДЕЛЮ. Baseline (7 дней до целевого дня) и target — в одних единицах.\n"
        "- Используй индивидуальные ATC-сессии выше для секции «Корзины» — там есть город и канал.\n"
        "- Используй country_channel_sessions_per_week чтобы точно знать, какой канал откуда пришёл. "
        "НЕ делай предположений о каналах если данные не подтверждают.\n"
        "- Если США выросли/упали — смотри их channel split в country_channel_sessions_per_week.\n"
        "- changelog.md объясняет только те изменения, которые туда записаны. "
        "Не применяй одно событие как объяснение всего подряд.\n"
        "Если значимых движений нет — одна строка «спокойный день»."
    )


def build_weekly_prompt(
    week_start: date,
    week_end: date,
    target_data: dict,
    baseline_data: dict,
    changelog_entries: str,
    atc_sessions: list[dict],
) -> str:
    return (
        f"Сегодня weekly report для Pinkspink за неделю "
        f"{week_start.isoformat()}..{week_end.isoformat()}.\n\n"
        f"Данные за прошлую неделю (weeks_count=1.0, все счётчики = фактические значения за неделю):\n```json\n"
        f"{json.dumps(target_data, indent=2, ensure_ascii=False)}\n```\n\n"
        f"Данные за baseline — СРЕДНЕЕ за неделю по 4 предыдущим неделям (weeks_count=4.0, все счётчики уже поделены на 4):\n"
        f"```json\n{json.dumps(baseline_data, indent=2, ensure_ascii=False)}\n```"
        f"{atc_block(atc_sessions)}"
        f"{changelog_block(changelog_entries)}\n\n"
        "Сгенерируй weekly report по шаблону из references/report-template.md "
        "(≤700 слов, на русском). Включи до 3 рекомендаций.\n"
        "ВАЖНО ПРО ДАННЫЕ:\n"
        "- Все счётчики сессий (sessions_per_week, channels_sessions_per_week, "
        "country_channel_sessions_per_week, top_countries_funnel_per_week) уже "
        "нормированы до СРЕДНИХ ЗА НЕДЕЛЮ — и в target (1 неделя), и в baseline (28 дней ÷ 4). "
        "Сравнивай напрямую, НЕ делая дополнительных пересчётов.\n"
        "- Используй индивидуальные ATC-сессии выше для секции «Корзины».\n"
        "- Используй country_channel_sessions_per_week чтобы точно знать откуда пришла каждая страна. "
        "НЕ приписывай каналу трафик страны без подтверждения в данных.\n"
        "- Если страна выросла/упала — объясняй только через её channel split в данных.\n"
        "- Changelog — только конкретные механизмы. Не применяй одно изменение "
        "как объяснение несвязанных метрик."
    )


def report_path(grain: str, target_date: date, week_monday: date | None) -> Path:
    if grain == "daily":
        return REPORTS_DIR / "daily" / f"{target_date.isoformat()}.md"
    iso_year, iso_week, _ = (week_monday or target_date).isocalendar()
    return REPORTS_DIR / "weekly" / f"{iso_year}-W{iso_week:02d}.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grain", choices=["daily", "weekly"], required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Telegram POST (still queries BigQuery and Claude)",
    )
    args = parser.parse_args()

    today_utc = datetime.now(timezone.utc).date()
    client = bq_client()

    if args.grain == "daily":
        start, end = daily_lookback_window(today_utc)
        rows = fetch_session_facts(client, start, end)
        target_day = pick_latest_day(rows)
        if target_day is None:
            print(
                f"WARN: no data in last {DAILY_LOOKBACK_DAYS} days — отчёт пропущен"
            )
            if not args.dry_run:
                send_telegram(
                    f"⚠ В BigQuery нет данных за последние {DAILY_LOOKBACK_DAYS} дней. Daily отчёт пропущен.",
                    os.environ["TELEGRAM_BOT_TOKEN"],
                    os.environ["TELEGRAM_CHAT_ID"],
                )
            return 0
        baseline_set = {target_day - timedelta(days=i) for i in range(1, 8)}
        target_data = aggregate_period(rows, {target_day})
        baseline_data = aggregate_period(rows, baseline_set)
        atc_sessions = fetch_atc_sessions(client, target_day, target_day)
        changelog_entries = load_recent_changelog(today_utc, window_days=14)
        prompt = build_daily_prompt(
            target_day, today_utc, target_data, baseline_data, changelog_entries, atc_sessions
        )
        max_tokens = 1000
        out_path = report_path("daily", target_day, None)
    else:
        week_monday, week_sunday, target_set, baseline_set = weekly_window(today_utc)
        start = min(baseline_set | target_set)
        end = max(baseline_set | target_set)
        rows = fetch_session_facts(client, start, end)
        target_data = aggregate_period(rows, target_set)
        baseline_data = aggregate_period(rows, baseline_set)
        atc_sessions = fetch_atc_sessions(client, week_monday, week_sunday)
        changelog_entries = load_recent_changelog(today_utc, window_days=60)
        prompt = build_weekly_prompt(
            week_monday, week_sunday, target_data, baseline_data, changelog_entries, atc_sessions
        )
        max_tokens = 1800
        out_path = report_path("weekly", week_monday, week_monday)

    skill = load_skill()
    print(f"Calling Claude ({CLAUDE_MODEL}, system={len(skill)} chars)...")
    report = call_claude(skill, prompt, max_tokens)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Saved: {out_path}")

    if not args.dry_run:
        send_telegram(
            report,
            os.environ["TELEGRAM_BOT_TOKEN"],
            os.environ["TELEGRAM_CHAT_ID"],
        )
        print("Sent to Telegram")

    return 0


if __name__ == "__main__":
    sys.exit(main())
