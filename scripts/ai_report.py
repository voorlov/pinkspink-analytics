#!/usr/bin/env python3
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
EXCLUDED_COUNTRIES = ("China", "Hong Kong", "South Korea", "Singapore")
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
    """Roll up rows belonging to `days` into a flat metric summary."""
    subset = [r for r in rows if r["day"] in days]
    n = max(len(days), 1)
    sessions = sum(r["sessions"] for r in subset)
    atc = sum(r["sessions_with_atc"] for r in subset)
    checkouts = sum(r["sessions_with_checkout"] for r in subset)
    purchases = sum(r["sessions_with_purchase"] for r in subset)
    views = sum(r["sessions_with_view"] for r in subset)
    new_sessions = sum(r["new_user_sessions"] for r in subset)

    by_channel: dict[str, int] = {}
    by_country: dict[str, int] = {}
    by_device: dict[str, int] = {}
    for r in subset:
        by_channel[r["channel"]] = by_channel.get(r["channel"], 0) + r["sessions"]
        by_country[r["country"]] = by_country.get(r["country"], 0) + r["sessions"]
        by_device[r["device"]] = by_device.get(r["device"], 0) + r["sessions"]

    def pct(num: int, den: int) -> float:
        return round(100.0 * num / den, 2) if den else 0.0

    return {
        "days_count": len(days),
        "sessions_total": sessions,
        "sessions_per_day_avg": round(sessions / n, 1),
        "atc_rate_pct": pct(atc, sessions),
        "view_to_atc_pct": pct(atc, views),
        "checkout_rate_pct": pct(checkouts, sessions),
        "purchase_rate_pct": pct(purchases, sessions),
        "new_sessions_share_pct": pct(new_sessions, sessions),
        "channels_sessions": dict(sorted(by_channel.items(), key=lambda x: -x[1])),
        "top_countries_sessions": dict(
            sorted(by_country.items(), key=lambda x: -x[1])[:8]
        ),
        "devices_sessions": dict(sorted(by_device.items(), key=lambda x: -x[1])),
    }


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


def build_daily_prompt(
    target: date,
    today_utc: date,
    target_data: dict,
    baseline_data: dict,
    changelog_entries: str,
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
        f"{changelog_block(changelog_entries)}\n\n"
        "Сгенерируй daily report по шаблону из references/report-template.md "
        "(≤300 слов, на русском). Применяй small-sample rules из metrics-playbook.md. "
        "Если значимых движений нет — одна строка «спокойный день». "
        "Не добавляй секции которых нет в шаблоне daily."
    )


def build_weekly_prompt(
    week_start: date,
    week_end: date,
    target_data: dict,
    baseline_data: dict,
    changelog_entries: str,
) -> str:
    return (
        f"Сегодня weekly report для Pinkspink за неделю "
        f"{week_start.isoformat()}..{week_end.isoformat()}.\n\n"
        f"Данные за прошлую неделю:\n```json\n"
        f"{json.dumps(target_data, indent=2, ensure_ascii=False)}\n```\n\n"
        f"Данные за baseline (среднее по 4 предыдущим неделям, агрегировано):\n"
        f"```json\n{json.dumps(baseline_data, indent=2, ensure_ascii=False)}\n```"
        f"{changelog_block(changelog_entries)}\n\n"
        "Сгенерируй weekly report по шаблону из references/report-template.md "
        "(≤700 слов, на русском). Включи до 3 рекомендаций.\n\n"
        "ВАЖНО: у тебя нет прямого доступа к BigQuery в этом контексте, только "
        "переданные выше агрегаты. Если в шаблоне есть секция «что я исследовал "
        "за пределами дашборда» — пометь её одной строкой «требует ad-hoc "
        "запроса в Claude Code, в этом автоотчёте недоступно». Это норма для "
        "автоматического weekly. Остальные секции заполняй полностью."
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
        changelog_entries = load_recent_changelog(today_utc, window_days=14)
        prompt = build_daily_prompt(
            target_day, today_utc, target_data, baseline_data, changelog_entries
        )
        max_tokens = 800
        out_path = report_path("daily", target_day, None)
    else:
        week_monday, week_sunday, target_set, baseline_set = weekly_window(today_utc)
        start = min(baseline_set | target_set)
        end = max(baseline_set | target_set)
        rows = fetch_session_facts(client, start, end)
        target_data = aggregate_period(rows, target_set)
        baseline_data = aggregate_period(rows, baseline_set)
        changelog_entries = load_recent_changelog(today_utc, window_days=60)
        prompt = build_weekly_prompt(
            week_monday, week_sunday, target_data, baseline_data, changelog_entries
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
