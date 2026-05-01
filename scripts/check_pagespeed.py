#!/usr/bin/env python3
"""Probe Pinkspink key URLs via Google PageSpeed Insights API.

Saves a JSON snapshot to reports/perf/YYYY-MM-DD.json and a markdown
digest to reports/perf/latest.md, posts a compact summary to Telegram.

PSI returns Lighthouse synthetic perf metrics (always available) plus
CrUX real-user p75 percentiles (if site/origin has enough Chrome traffic).
For pinkspink.company at ~24 sessions/day, URL-level CrUX is unlikely;
origin-level CrUX may be present.

Run:
    python scripts/check_pagespeed.py
    python scripts/check_pagespeed.py --dry-run   # skip Telegram
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _telegram import send_telegram  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PERF_DIR = ROOT / "reports" / "perf"

URLS: list[tuple[str, str]] = [
    ("intl homepage", "https://pinkspink.company/"),
    ("jp homepage", "https://pinkspink.company/ja"),
    ("intl catalog", "https://pinkspink.company/collections/shop-all"),
    ("jp catalog", "https://pinkspink.company/ja/collections/shop-all"),
]
STRATEGIES = ("mobile", "desktop")

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Google's official thresholds (2024-2025).
THRESHOLDS = {
    "LCP_ms": (2500, 4000),       # good ≤ 2500, poor > 4000
    "INP_ms": (200, 500),
    "CLS": (0.10, 0.25),
    "FCP_ms": (1800, 3000),
    "TTFB_ms": (800, 1800),
    "TBT_ms": (200, 600),
    "SpeedIndex_ms": (3400, 5800),
}


def classify(metric: str, value: float | None) -> str:
    """Return 'good' | 'needs-improvement' | 'poor' | '?' based on Google thresholds."""
    if value is None:
        return "?"
    good, poor = THRESHOLDS[metric]
    if value <= good:
        return "good"
    if value <= poor:
        return "needs-improvement"
    return "poor"


def emoji(rating: str) -> str:
    return {"good": "✅", "needs-improvement": "⚠", "poor": "❌"}.get(rating, "·")


def fetch_psi(url: str, strategy: str, attempts: int = 3) -> dict:
    """Call PSI API; return parsed JSON. Retries transient errors with backoff."""
    params = {"url": url, "strategy": strategy, "category": "performance"}
    api_key = os.environ.get("PAGESPEED_API_KEY")
    if api_key:
        params["key"] = api_key
    qs = urllib.parse.urlencode(params)
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(f"{PSI_ENDPOINT}?{qs}")
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read())
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if i < attempts - 1:
                time.sleep(2 ** i)  # 1s, 2s
    raise last_exc  # type: ignore[misc]


def parse_psi(payload: dict) -> dict:
    """Extract Lighthouse + CrUX fields we care about."""
    lh = payload.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    score = lh.get("categories", {}).get("performance", {}).get("score")

    def num(audit: str) -> float | None:
        v = audits.get(audit, {}).get("numericValue")
        return float(v) if v is not None else None

    out = {
        "fetched_at": payload.get("analysisUTCTimestamp"),
        "lighthouse": {
            "perf_score_0_100": int(round(score * 100)) if score is not None else None,
            "LCP_ms": num("largest-contentful-paint"),
            "FCP_ms": num("first-contentful-paint"),
            "TBT_ms": num("total-blocking-time"),
            "CLS": num("cumulative-layout-shift"),
            "SpeedIndex_ms": num("speed-index"),
        },
    }

    # CrUX url-level
    le = payload.get("loadingExperience", {})
    out["crux_url"] = _crux_metrics(le.get("metrics", {}))
    out["crux_url"]["overall_category"] = le.get("overall_category")
    out["crux_url"]["has_data"] = bool(le.get("metrics"))
    # CrUX origin-level
    ole = payload.get("originLoadingExperience", {})
    out["crux_origin"] = _crux_metrics(ole.get("metrics", {}))
    out["crux_origin"]["overall_category"] = ole.get("overall_category")
    out["crux_origin"]["has_data"] = bool(ole.get("metrics"))
    return out


def _crux_metrics(metrics: dict) -> dict:
    """Pull p75 percentiles for the metrics we care about."""
    mapping = {
        "LCP_ms": "LARGEST_CONTENTFUL_PAINT_MS",
        "INP_ms": "INTERACTION_TO_NEXT_PAINT",
        "CLS": "CUMULATIVE_LAYOUT_SHIFT_SCORE",
        "FCP_ms": "FIRST_CONTENTFUL_PAINT_MS",
        "TTFB_ms": "EXPERIMENTAL_TIME_TO_FIRST_BYTE",
    }
    out: dict = {}
    for ours, psi in mapping.items():
        m = metrics.get(psi)
        if not m:
            continue
        p = m.get("percentile")
        # CLS arrives as integer * 100 in CrUX (e.g. 8 means 0.08)
        if ours == "CLS" and p is not None:
            p = p / 100.0
        out[ours] = p
    return out


def probe_all() -> list[dict]:
    """Run PSI for every (url, strategy) pair. Returns list of records."""
    results: list[dict] = []
    for label, url in URLS:
        for strategy in STRATEGIES:
            print(f"  {strategy:7s} {url}")
            try:
                payload = fetch_psi(url, strategy)
                rec = {"label": label, "url": url, "strategy": strategy, **parse_psi(payload)}
            except Exception as exc:  # noqa: BLE001
                rec = {"label": label, "url": url, "strategy": strategy, "error": str(exc)}
            results.append(rec)
    return results


def render_markdown(results: list[dict], date_str: str) -> str:
    lines = [f"# PageSpeed snapshot — {date_str}", ""]
    lines.append("Источник: Google PageSpeed Insights (Lighthouse synthetic + CrUX p75 real-user, если есть достаточно трафика).")
    lines.append("")
    lines.append("| URL | устройство | perf | LCP | FCP | CLS | TBT | INP (CrUX p75) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        if "error" in r:
            lines.append(f"| {r['label']} | {r['strategy']} | ERROR | {r['error'][:60]} |  |  |  |  |")
            continue
        lh = r["lighthouse"]
        score = lh["perf_score_0_100"]
        score_str = f"{score}/100" if score is not None else "—"
        lcp = _fmt_ms(lh["LCP_ms"])
        lcp_rating = emoji(classify("LCP_ms", lh["LCP_ms"]))
        fcp = _fmt_ms(lh["FCP_ms"])
        fcp_rating = emoji(classify("FCP_ms", lh["FCP_ms"]))
        cls = f"{lh['CLS']:.3f}" if lh["CLS"] is not None else "—"
        cls_rating = emoji(classify("CLS", lh["CLS"]))
        tbt = _fmt_ms(lh["TBT_ms"])
        tbt_rating = emoji(classify("TBT_ms", lh["TBT_ms"]))
        # INP only from CrUX (origin-level fallback)
        inp_source = r["crux_url"] if r["crux_url"].get("INP_ms") else r["crux_origin"]
        inp_val = inp_source.get("INP_ms")
        if inp_val is not None:
            inp_str = f"{int(inp_val)}ms {emoji(classify('INP_ms', inp_val))}"
            scope = " (origin)" if not r["crux_url"].get("INP_ms") else ""
            inp_str += scope
        else:
            inp_str = "нет данных"
        lines.append(
            f"| {r['label']} | {r['strategy']} | **{score_str}** | "
            f"{lcp} {lcp_rating} | {fcp} {fcp_rating} | "
            f"{cls} {cls_rating} | {tbt} {tbt_rating} | {inp_str} |"
        )

    lines.append("")
    lines.append("**Пороги Google:** LCP ≤2.5s ✅ ≤4s ⚠ >4s ❌  ·  INP ≤200ms ✅ ≤500ms ⚠  ·  CLS ≤0.1 ✅ ≤0.25 ⚠  ·  perf score ≥90 ✅ ≥50 ⚠ <50 ❌.")
    lines.append("")
    lines.append("LCP/FCP/CLS/TBT — Lighthouse synthetic test (один заход с эмулированного устройства). INP — CrUX p75 за 28 дней реальных пользователей; обычно доступен только origin-level если у URL мало трафика.")
    return "\n".join(lines)


def _fmt_ms(v: float | None) -> str:
    if v is None:
        return "—"
    if v >= 1000:
        return f"{v/1000:.1f}s"
    return f"{int(v)}ms"


def render_telegram(results: list[dict], date_str: str) -> str:
    """Compact Telegram summary with one line per (url, strategy)."""
    lines = [f"⚡ Pinkspink perf — {date_str}", ""]
    poor_flags: list[str] = []
    for r in results:
        if "error" in r:
            lines.append(f"• {r['label']} ({r['strategy']}): ERROR — {r['error'][:80]}")
            continue
        lh = r["lighthouse"]
        score = lh["perf_score_0_100"]
        score_str = f"{score}/100" if score is not None else "—"
        lcp_rating = classify("LCP_ms", lh["LCP_ms"])
        cls_rating = classify("CLS", lh["CLS"])
        tbt_rating = classify("TBT_ms", lh["TBT_ms"])
        bits = []
        bits.append(f"LCP {_fmt_ms(lh['LCP_ms'])} {emoji(lcp_rating)}")
        bits.append(f"CLS {lh['CLS']:.2f} {emoji(cls_rating)}" if lh["CLS"] is not None else "CLS —")
        bits.append(f"TBT {_fmt_ms(lh['TBT_ms'])} {emoji(tbt_rating)}")
        # INP from CrUX if available
        inp_source = r["crux_url"] if r["crux_url"].get("INP_ms") else r["crux_origin"]
        inp_val = inp_source.get("INP_ms")
        if inp_val is not None:
            inp_rating = classify("INP_ms", inp_val)
            bits.append(f"INP {int(inp_val)}ms {emoji(inp_rating)}")
            if inp_rating == "poor":
                poor_flags.append(f"INP poor у {r['label']} ({r['strategy']})")
        if lcp_rating == "poor":
            poor_flags.append(f"LCP poor у {r['label']} ({r['strategy']})")
        lines.append(f"• {r['label']} {r['strategy']} — *{score_str}*  " + " · ".join(bits))

    lines.append("")
    if poor_flags:
        lines.append("🔴 *Проблемы:* " + "; ".join(poor_flags))
    else:
        lines.append("✅ Серьёзных проблем не обнаружено")
    lines.append("")
    lines.append("Источник: PageSpeed Insights (синтетика + CrUX). Замер 1 раз в неделю по понедельникам.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram POST")
    args = parser.parse_args()

    print(f"Probing {len(URLS)} URLs × {len(STRATEGIES)} strategies = {len(URLS) * len(STRATEGIES)} PSI calls")
    results = probe_all()

    today = datetime.now(timezone.utc).date().isoformat()
    PERF_DIR.mkdir(parents=True, exist_ok=True)

    snap_path = PERF_DIR / f"{today}.json"
    snap_path.write_text(
        json.dumps(
            {"date": today, "results": results}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    print(f"Saved snapshot: {snap_path}")

    md = render_markdown(results, today)
    (PERF_DIR / "latest.md").write_text(md, encoding="utf-8")
    print(f"Saved digest: {PERF_DIR / 'latest.md'}")

    if not args.dry_run:
        send_telegram(render_telegram(results, today))
        print("Sent to Telegram")

    return 0


if __name__ == "__main__":
    sys.exit(main())
