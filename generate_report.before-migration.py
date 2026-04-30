#!/usr/bin/env python3
"""
Pinkspink Analytics — HTML Dashboard Generator
Pulls data from BigQuery, generates a standalone HTML report with Chart.js.

Usage:
    python generate_report.py              # default: weekly, last 12 weeks
    python generate_report.py --grain day  # daily, last 14 days
    python generate_report.py --grain month # monthly, all data
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

from google.cloud import bigquery
from google.oauth2.service_account import Credentials

# ============================================================
# CONFIG
# ============================================================

BQ_PROJECT = "claude-code-486108"
BQ_DATASET = "analytics_411715710"
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_account.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.html")

EXCLUDED_COUNTRIES_DEFAULT = ["China", "Hong Kong", "South Korea", "Singapore", "Georgia"]

COUNTRY_FLAGS = {
    "Japan": "🇯🇵", "United States": "🇺🇸", "Germany": "🇩🇪", "France": "🇫🇷",
    "Mexico": "🇲🇽", "Italy": "🇮🇹", "United Kingdom": "🇬🇧", "Australia": "🇦🇺",
    "Brazil": "🇧🇷", "Canada": "🇨🇦", "Spain": "🇪🇸", "Netherlands": "🇳🇱",
    "Poland": "🇵🇱", "Russia": "🇷🇺", "South Korea": "🇰🇷", "Finland": "🇫🇮",
    "Switzerland": "🇨🇭", "Colombia": "🇨🇴", "Chile": "🇨🇱", "Argentina": "🇦🇷",
    "Israel": "🇮🇱", "Belgium": "🇧🇪", "Austria": "🇦🇹", "Norway": "🇳🇴",
    "Sweden": "🇸🇪", "Portugal": "🇵🇹", "Greece": "🇬🇷", "Czechia": "🇨🇿",
    "Ireland": "🇮🇪", "New Zealand": "🇳🇿", "India": "🇮🇳", "Thailand": "🇹🇭",
    "Vietnam": "🇻🇳", "Indonesia": "🇮🇩", "Malaysia": "🇲🇾", "Singapore": "🇸🇬",
    "Türkiye": "🇹🇷", "Ukraine": "🇺🇦", "Kazakhstan": "🇰🇿", "Georgia": "🇬🇪",
    "Hungary": "🇭🇺", "Slovakia": "🇸🇰", "Latvia": "🇱🇻", "Estonia": "🇪🇪",
    "Lithuania": "🇱🇹", "Romania": "🇷🇴", "Croatia": "🇭🇷", "Serbia": "🇷🇸",
    "China": "🇨🇳", "Hong Kong": "🇭🇰", "Taiwan": "🇹🇼", "Philippines": "🇵🇭",
    "Peru": "🇵🇪", "Ecuador": "🇪🇨", "Uruguay": "🇺🇾", "Costa Rica": "🇨🇷",
    "Puerto Rico": "🇵🇷", "Belarus": "🇧🇾",
}

def flag(country):
    return f"{COUNTRY_FLAGS.get(country, '🏳️')} {country}"

CHANNEL_SQL = """
    CASE
        WHEN source IN ('api.scraperforce.com', 'sanganzhu.com', 'jariblog.online') THEN 'Spam'
        WHEN medium IN ('paid', 'cpm') OR REGEXP_CONTAINS(medium, r'(?i)instagram_|facebook_') THEN 'Paid'
        WHEN source IN ('ig', 'l.instagram.com') AND medium IN ('social', 'referral') THEN 'Social'
        WHEN medium = 'organic' THEN 'Organic'
        WHEN medium = 'email' THEN 'Email'
        WHEN source = '(direct)' AND medium IN ('(none)', '(not set)') THEN 'Direct'
        WHEN medium = 'referral' THEN 'Referral'
        ELSE 'Other'
    END
"""

# ============================================================
# DESIGN TOKENS — single source of truth for visual style
# Edit values here → CSS :root vars and Chart.js defaults regenerate.
# Run `python generate_report.py --styleguide` to preview.
# ============================================================

TOKENS = {
    "channel": {
        "social":   "#6C5CE7",
        "paid":     "#00B894",
        "direct":   "#636E72",
        "organic":  "#0984E3",
        "referral": "#FDCB6E",
        "email":    "#E17055",
        "other":    "#B2BEC3",
    },
    "funnel": {
        "home":     "#636E72",
        "catalog":  "#2D3436",
        "product":  "#6C5CE7",
        "atc":      "#FDCB6E",
        "checkout": "#74B9FF",
        "purchase": "#00B894",
    },
    "semantic": {
        "growth":    "#00B894",
        "decline":   "#E17055",
        "neutral":   "#636E72",
        "highlight": "#6C5CE7",
    },
    "surface": {
        "page":      "#FAFAFA",
        "card":      "#FFFFFF",
        "muted":     "#F0F0F0",
        "hover":     "#F8F9FA",
        "alert":     "#FFEAE0",
        "border":    "#DFE6E9",
        "divider":   "#F0F0F0",
        "inverse":   "#2D3436",
        "inverse2":  "#636E72",
    },
    "text": {
        "primary":   "#2D3436",
        "secondary": "#636E72",
        "muted":     "#B2BEC3",
        "ondark":    "#FFFFFF",
    },
    "type": {
        "family": "'Ubuntu Mono', monospace",
        "scale": {
            "h1":        "32px",
            "h2":        "20px",
            "kpi-xl":    "28px",
            "kpi-lg":    "20px",
            "metric":    "18px",
            "brand":     "16px",
            "h3":        "14px",
            "h4":        "13px",
            "body":      "13px",
            "meta":      "12px",
            "table":     "12px",
            "th":        "11px",
            "label":     "11px",
            "tag":       "10px",
            "datalabel": "10px",
        },
        "weight": {
            "regular":  "400",
            "semibold": "600",
            "bold":     "700",
        },
        "letter": {
            "label": "0.5px",
        },
    },
    "space": {
        "1": "4px", "2": "8px", "3": "12px", "4": "16px", "5": "24px", "6": "32px",
    },
    "radius": {
        "sm": "3px", "md": "4px", "lg": "6px", "xl": "8px", "pill": "999px",
    },
    "shadow": {
        "card":   "0 1px 3px rgba(0,0,0,0.08)",
        "sticky": "rgba(255,255,255,0.95)",
    },
    "chart": {
        "axis_color":               "#636E72",
        "axis_label_size":          11,
        "grid_color":               "rgba(0,0,0,0.06)",
        "datalabel_size":           10,
        "datalabel_color_on_light": "#2D3436",
        "datalabel_color_on_dark":  "#FFFFFF",
        "legend_size":              12,
    },
}


def chart_defaults_js(tokens=TOKENS):
    """Generate Chart.defaults overrides — applies once, propagates to all charts."""
    c = tokens["chart"]
    return f"""
    // === Chart.js global defaults (from TOKENS["chart"]) ===
    Chart.defaults.font.family = {tokens['type']['family']!r};
    Chart.defaults.font.size = {c['axis_label_size']};
    Chart.defaults.color = {c['axis_color']!r};
    Chart.defaults.borderColor = {c['grid_color']!r};
    Chart.defaults.scale.grid.color = {c['grid_color']!r};
    Chart.defaults.scale.ticks.color = {c['axis_color']!r};
    Chart.defaults.plugins.legend.labels.font = {{ size: {c['legend_size']} }};
    Chart.defaults.plugins.datalabels = Chart.defaults.plugins.datalabels || {{}};
    Chart.defaults.plugins.datalabels.font = {{ size: {c['datalabel_size']} }};
    Chart.defaults.plugins.datalabels.color = {c['datalabel_color_on_light']!r};
    """.strip()


def render_css_vars(tokens=TOKENS):
    """Generate the :root { --... } block from TOKENS."""
    lines = [":root {"]
    for k, v in tokens["channel"].items():
        lines.append(f"    --c-channel-{k}: {v};")
    for k, v in tokens["funnel"].items():
        lines.append(f"    --c-funnel-{k}: {v};")
    for k, v in tokens["semantic"].items():
        lines.append(f"    --c-{k}: {v};")
    for k, v in tokens["surface"].items():
        lines.append(f"    --bg-{k}: {v};")
    for k, v in tokens["text"].items():
        lines.append(f"    --tx-{k}: {v};")
    lines.append(f"    --ff-mono: {tokens['type']['family']};")
    for k, v in tokens["type"]["scale"].items():
        lines.append(f"    --fs-{k}: {v};")
    for k, v in tokens["type"]["weight"].items():
        lines.append(f"    --fw-{k}: {v};")
    for k, v in tokens["type"]["letter"].items():
        lines.append(f"    --ls-{k}: {v};")
    for k, v in tokens["space"].items():
        lines.append(f"    --sp-{k}: {v};")
    for k, v in tokens["radius"].items():
        lines.append(f"    --r-{k}: {v};")
    for k, v in tokens["shadow"].items():
        lines.append(f"    --sh-{k}: {v};")
    lines.append("}")
    return "\n".join(lines)


def generate_styleguide(tokens=TOKENS):
    """Build a visual styleguide HTML showing every token in TOKENS."""
    css_vars = render_css_vars(tokens)
    chart_js_defaults = chart_defaults_js(tokens)

    # Detailed info per surface for the styleguide
    # demo: HTML inside the colored area (shows what typically lives on this surface)
    # text: which --tx-* token pairs with it
    # where: short usage line
    # contains: what visual elements typically sit on top
    SURFACE_DETAILS = {
        "page": {
            "where":    "Фон всей страницы (<code>body</code>)",
            "text":     "primary",
            "contains": "Все карточки <code>.cell</code>, таблицы, фильтры",
            "demo":     '<div class="mini-card">Карточка на фоне страницы</div>',
        },
        "card": {
            "where":    "Карточки <code>.cell</code>, <code>.data-table</code>, <code>.filters</code>, <code>.bubble-filters</code>",
            "text":     "primary",
            "contains": "Заголовки h3/h4, графики, таблицы, KPI-числа",
            "demo":     '<div class="demo-text" style="color:var(--tx-primary);font-weight:var(--fw-bold)">Заголовок 13px</div><div class="demo-meta" style="color:var(--tx-secondary)">Подпись .meta 11px</div>',
        },
        "muted": {
            "where":    "Default-фон <code>.grain-btn</code>, фон <code>.kpi-spark</code>, фон спарклайнов",
            "text":     "secondary",
            "contains": "Кнопки в неактивном состоянии, мини-графики",
            "demo":     '<button class="grain-btn" style="background:var(--bg-muted)">grain-btn</button>',
        },
        "hover": {
            "where":    "<code>tr:hover</code> в <code>.data-table</code>",
            "text":     "primary",
            "contains": "Подсветка строки таблицы под курсором",
            "demo":     '<div class="mini-row">Строка таблицы под курсором</div>',
        },
        "alert": {
            "where":    "Резерв — пока не используется",
            "text":     "primary",
            "contains": "Будущие предупреждения / нотификации",
            "demo":     '<div class="demo-meta" style="color:var(--tx-secondary)">не задействовано</div>',
        },
        "border": {
            "where":    "Бордер <code>.sticky-header</code>, <code>.tab-btn</code>, hover у <code>.grain-sq</code>",
            "text":     "secondary",
            "contains": "Тонкие линии-разделители крупных областей",
            "demo":     '<div style="background:var(--bg-card);border:1px solid var(--bg-border);border-radius:var(--r-md);padding:6px var(--sp-2);font-size:var(--fs-th)">card · 1px solid border</div>',
        },
        "divider": {
            "where":    "<code>border-bottom</code> в строках таблицы и <code>.country-row</code>",
            "text":     "secondary",
            "contains": "Очень тонкие разделители <em>внутри</em> блоков",
            "demo":     '<div style="font-size:var(--fs-th)">Row 1</div><div style="border-top:1px solid var(--bg-divider);font-size:var(--fs-th);padding-top:4px">Row 2</div>',
        },
        "inverse": {
            "where":    "Тёмные <code>&lt;th&gt;</code>, активные <code>.grain-active</code> / <code>.tab-active</code>",
            "text":     "ondark",
            "contains": "Заголовки таблиц, активные состояния кнопок",
            "demo":     '<div class="mini-th">КАНАЛ</div>',
        },
        "inverse2": {
            "where":    "<code>th:hover</code> на тёмных таблицах",
            "text":     "ondark",
            "contains": "Подсветка заголовка колонки при наведении",
            "demo":     '<div class="mini-th" style="background:var(--bg-inverse2)">th:hover</div>',
        },
    }
    TEXT_USAGE = {
        "primary":   "Основной текст body, h1-h3, brand",
        "secondary": ".meta, h4, кнопки grain-btn, .header-meta",
        "muted":     ".agg-tag, .kpi-bench, scrollbar",
        "ondark":    "Текст на тёмных кнопках, на <code>&lt;th&gt;</code>",
    }
    NATIVE_WEIGHT = {
        "h1": ("bold", 700), "h2": ("semibold", 600), "h3": ("semibold", 600), "h4": ("semibold", 600),
        "kpi-xl": ("bold", 700), "kpi-lg": ("bold", 700), "metric": ("semibold", 600), "brand": ("bold", 700),
        "body": ("regular", 400), "meta": ("regular", 400), "table": ("regular", 400),
        "th": ("semibold", 600), "label": ("regular", 400), "tag": ("regular", 400), "datalabel": ("regular", 400),
    }
    TYPE_USAGE = {
        "h1":        "Заголовок страницы (Pinkspink Analytics)",
        "h2":        "Заголовки секций внутри вкладок",
        "h3":        "Заголовки блоков внутри карточек (.cell)",
        "h4":        "Подзаголовки, .filters label, .grain-btn",
        "kpi-xl":    "KPI value в 2×2 карточке (.kpi-value)",
        "kpi-lg":    "KPI value в .kpi-grid (Сводка: меньшие карточки)",
        "metric":    "Числа в .metric .value (3-колоночная сетка в слайдер-карточках)",
        "brand":     "Логотип Pinkspink в шапке",
        "body":      "Тело текста, кнопки",
        "meta":      ".meta (даты, описания), .delta, .country-row, .tab-btn",
        "table":     "Содержимое <td>",
        "th":        "<th>, .kpi-bench, .header-meta, заголовки в .title-area",
        "label":     ".kpi-label (UPPERCASE), .metric .label, .bubble-filters label",
        "tag":       ".agg-tag, .kpi-label в .kpi-grid (мелкие)",
        "datalabel": "Подписи на графиках (Chart.js datalabels)",
    }
    SPACE_USAGE = {
        "1": "Мелкие зазоры: gap у .tab-nav, padding в .grain-btn, margin у .agg-tag",
        "2": "Gap внутри блоков: .metrics, .kpi-grid, padding в .data-table th",
        "3": "Padding в .filters, gap между .data-table td, margin-bottom у .meta",
        "4": "Gap в .grid (12-кол. сетка), padding страницы, gap в .header-left/.slider",
        "5": "Margin-top у h2, padding-x у .main-container, margin-bottom у блоков",
        "6": "Резерв для крупных отступов между секциями",
    }

    def swatches(group_key, prefix, usage_map=None):
        cells = []
        for name, hex_val in tokens[group_key].items():
            usage = f'<div class="sw-use">{usage_map[name]}</div>' if usage_map and name in usage_map else ""
            cells.append(f"""
            <div class="sw">
                <div class="sw-color" style="background:{hex_val}"></div>
                <div class="sw-name">--{prefix}{name}</div>
                <div class="sw-val">{hex_val}</div>
                {usage}
            </div>""")
        return "".join(cells)

    def surface_cards():
        cells = []
        for name, hex_val in tokens["surface"].items():
            d = SURFACE_DETAILS.get(name, {})
            demo = d.get("demo", "")
            cells.append(f"""
            <div class="surf-card">
                <div class="surf-demo" style="background:{hex_val}">
                    {demo}
                </div>
                <div class="surf-name">
                    <code>--bg-{name}</code>
                    <span class="hex">{hex_val}</span>
                </div>
                <div class="surf-meta">
                    <div class="row"><span class="k">Где:</span><span class="v">{d.get("where", "")}</span></div>
                    <div class="row"><span class="k">Сверху:</span><span class="v">{d.get("contains", "")}</span></div>
                    <div class="row"><span class="k">Текст:</span><span class="v"><code>--tx-{d.get("text", "primary")}</code></span></div>
                </div>
            </div>""")
        return "".join(cells)

    type_rows = []
    for size_name, size_val in tokens["type"]["scale"].items():
        wname, wnum = NATIVE_WEIGHT.get(size_name, ("regular", 400))
        usage = TYPE_USAGE.get(size_name, "")
        type_rows.append(f"""
        <div class="ty-row">
            <span style="font-size:{size_val};font-weight:{wnum}">Pinkspink Analytics</span>
            <div class="ty-meta">
                <code>--fs-{size_name}</code> · {size_val} · <code>--fw-{wname}</code> ({wnum})
                <div class="ty-use">{usage}</div>
            </div>
        </div>""")

    weight_rows = []
    for wname, wnum in tokens["type"]["weight"].items():
        weight_rows.append(f"""
        <div class="ty-row">
            <span style="font-size:var(--fs-h2);font-weight:{wnum}">Pinkspink Analytics</span>
            <div class="ty-meta"><code>--fw-{wname}</code> · {wnum}</div>
        </div>""")

    space_rows = []
    for k, v in tokens["space"].items():
        usage = SPACE_USAGE.get(k, "")
        space_rows.append(f"""
        <div class="sp-row">
            <div class="sp-bar" style="width:{v};background:var(--c-channel-social)"></div>
            <code>--sp-{k}</code> <span class="meta">{v}</span>
            <span class="sp-use">{usage}</span>
        </div>""")

    radius_cards = []
    for k, v in tokens["radius"].items():
        radius_cards.append(f"""
        <div class="rad-cell">
            <div class="rad-box" style="border-radius:{v}"></div>
            <code>--r-{k}</code> <span class="meta">{v}</span>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Pinkspink — Styleguide</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu+Mono:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    <style>
        {css_vars}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: var(--ff-mono); background: var(--bg-page); color: var(--tx-primary); padding: var(--sp-5); }}
        h1 {{ font-size: var(--fs-h1); font-weight: var(--fw-bold); margin-bottom: var(--sp-2); }}
        h2 {{ font-size: var(--fs-h2); font-weight: var(--fw-semibold); margin: var(--sp-6) 0 var(--sp-3); padding-bottom: 6px; border-bottom: 2px solid var(--bg-inverse); }}
        .sub {{ color: var(--tx-secondary); font-size: var(--fs-meta); margin-bottom: var(--sp-5); }}
        code {{ font-family: var(--ff-mono); font-size: var(--fs-th); background: var(--bg-muted); padding: 1px 4px; border-radius: var(--r-sm); }}
        .meta {{ color: var(--tx-secondary); font-size: var(--fs-th); }}

        /* Color swatches */
        .sw-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--sp-3); margin-bottom: var(--sp-4); }}
        .sw {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); overflow: hidden; }}
        .sw-color {{ height: 60px; }}
        .sw-name {{ padding: var(--sp-2) var(--sp-3) 0; font-size: var(--fs-th); font-weight: var(--fw-bold); }}
        .sw-val {{ padding: 0 var(--sp-3) 2px; font-size: var(--fs-th); color: var(--tx-secondary); }}
        .sw-use {{ padding: 0 var(--sp-3) var(--sp-3); font-size: var(--fs-tag); color: var(--tx-secondary); line-height: 1.4; }}
        .sw-use code {{ font-size: var(--fs-tag); padding: 0 2px; }}

        /* Buttons demo */
        .btn-row {{ display: flex; gap: var(--sp-2); flex-wrap: wrap; align-items: center; padding: var(--sp-3); background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); margin-bottom: var(--sp-3); }}
        .btn-row .label {{ font-size: var(--fs-th); color: var(--tx-secondary); margin-right: var(--sp-3); min-width: 140px; }}
        .grain-btn {{ padding: var(--sp-1) var(--sp-3); border-radius: var(--r-md); font-size: var(--fs-body); color: var(--tx-secondary); background: var(--bg-muted); border: none; cursor: pointer; }}
        .grain-btn.is-hover {{ background: var(--bg-border); }}
        .grain-btn.is-active {{ background: var(--bg-inverse); color: var(--tx-ondark); }}
        .tab-btn {{ padding: 6px 14px; border-radius: var(--r-md); font-size: var(--fs-meta); font-weight: var(--fw-semibold); border: 1px solid var(--bg-border); cursor: pointer; background: var(--bg-card); color: var(--tx-secondary); }}
        .tab-btn.is-hover {{ background: var(--bg-muted); }}
        .tab-btn.is-active {{ background: var(--bg-inverse); color: var(--tx-ondark); border-color: var(--bg-inverse); }}
        .grain-sq {{ width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; font-size: var(--fs-meta); font-weight: var(--fw-bold); background: var(--bg-muted); color: var(--tx-secondary); border-radius: var(--r-md); }}
        .grain-sq.is-hover {{ background: var(--bg-border); }}
        .bubble-filters-demo {{ display: flex; flex-wrap: wrap; gap: var(--sp-2); padding: var(--sp-2) var(--sp-3); background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); }}
        .bubble-filters-demo label {{ font-size: var(--fs-label); display: flex; align-items: center; gap: var(--sp-1); }}

        /* Typography rows */
        .ty-row {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); padding: var(--sp-3) var(--sp-4); margin-bottom: var(--sp-2); display: flex; align-items: center; justify-content: space-between; gap: var(--sp-4); flex-wrap: wrap; }}
        .ty-meta {{ color: var(--tx-secondary); font-size: var(--fs-th); text-align: right; }}
        .ty-use {{ font-size: var(--fs-tag); margin-top: 2px; opacity: 0.85; }}

        /* Spacing rows */
        .sp-row {{ display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-2); padding: var(--sp-2) var(--sp-3); background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); }}
        .sp-bar {{ height: 16px; border-radius: var(--r-sm); flex-shrink: 0; }}
        .sp-use {{ font-size: var(--fs-tag); color: var(--tx-secondary); margin-left: var(--sp-2); }}

        /* Radius cards */
        .rad-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: var(--sp-3); }}
        .rad-cell {{ background: var(--bg-card); padding: var(--sp-3); border-radius: var(--r-xl); box-shadow: var(--sh-card); text-align: center; }}
        .rad-box {{ width: 60px; height: 60px; background: var(--c-channel-social); margin: 0 auto var(--sp-2); }}

        /* Shadow cards */
        .sh-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--sp-4); }}
        .sh-cell {{ background: var(--bg-card); padding: var(--sp-4); border-radius: var(--r-xl); }}
        .sh-cell.card-sh {{ box-shadow: var(--sh-card); }}

        /* Semantic / state examples */
        .sem-row {{ display: flex; gap: var(--sp-3); flex-wrap: wrap; margin-bottom: var(--sp-3); }}
        .sem-tag {{ padding: var(--sp-1) var(--sp-3); border-radius: var(--r-pill); font-size: var(--fs-th); font-weight: var(--fw-semibold); }}
        .sem-tag.growth   {{ background: var(--c-growth);    color: var(--tx-ondark); }}
        .sem-tag.decline  {{ background: var(--c-decline);   color: var(--tx-ondark); }}
        .sem-tag.neutral  {{ background: var(--c-neutral);   color: var(--tx-ondark); }}
        .sem-tag.highlight{{ background: var(--c-highlight); color: var(--tx-ondark); }}

        /* Data tables */
        .data-table {{ width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: var(--r-xl); overflow: hidden; box-shadow: var(--sh-card); }}
        .data-table th {{ background: var(--bg-inverse); color: var(--tx-ondark); padding: var(--sp-2) var(--sp-3); font-size: var(--fs-th); text-align: left; font-weight: var(--fw-semibold); }}
        .data-table td {{ padding: 6px var(--sp-3); font-size: var(--fs-table); border-bottom: 1px solid var(--bg-divider); }}
        .data-table tr:hover {{ background: var(--bg-hover); }}
        .data-table .highlight {{ font-weight: var(--fw-bold); color: var(--c-highlight); }}

        /* KPI demo */
        .kpi-demo {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--sp-3); }}
        .cell-kpi {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); padding: var(--sp-3); display: flex; flex-direction: column; }}
        .kpi-label {{ font-size: var(--fs-label); text-transform: uppercase; color: var(--tx-secondary); letter-spacing: var(--ls-label); }}
        .kpi-value {{ font-size: var(--fs-kpi-xl); font-weight: var(--fw-bold); margin: var(--sp-1) 0; }}
        .kpi-value-sm {{ font-size: var(--fs-kpi-lg); font-weight: var(--fw-bold); line-height: 1.1; margin: var(--sp-1) 0; }}
        .kpi-bench {{ font-size: var(--fs-label); color: var(--tx-muted); }}
        .kpi-spark {{ background: var(--bg-muted); border-radius: var(--r-lg); margin-top: var(--sp-2); padding: var(--sp-1); flex: 1; min-height: 50px; }}

        /* KPI grid block (Сводка) */
        .kpi-grid-demo {{ display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(4, 70px); gap: var(--sp-2); max-width: 460px; }}
        .kpi-grid-demo .kg {{ padding: var(--sp-2) var(--sp-3); }}
        .kpi-grid-demo .kg .kpi-label {{ font-size: var(--fs-tag); }}
        .kg-rps {{ grid-column: 1; grid-row: 1; }}
        .kg-rev {{ grid-column: 2; grid-row: 1; }}
        .kg-atc {{ grid-column: 1; grid-row: 2 / span 2; }}
        .kg-pr  {{ grid-column: 2; grid-row: 2 / span 2; }}
        .kg-c2p {{ grid-column: 1 / span 2; grid-row: 4; }}

        /* Chart preview */
        .chart-wrap {{ position: relative; width: 100%; height: 360px; background: var(--bg-card); border-radius: var(--r-xl); padding: var(--sp-3); box-shadow: var(--sh-card); margin-bottom: var(--sp-4); }}

        /* Surfaces — detailed cards */
        .surf-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: var(--sp-3); margin-bottom: var(--sp-4); }}
        .surf-card {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); overflow: hidden; }}
        .surf-demo {{ height: 130px; padding: var(--sp-3); position: relative; display: flex; flex-direction: column; gap: var(--sp-1); justify-content: center; align-items: center; }}
        .surf-demo .demo-text {{ font-size: var(--fs-body); }}
        .surf-demo .demo-meta {{ font-size: var(--fs-th); }}
        .surf-demo .mini-card {{ background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); padding: var(--sp-2) var(--sp-3); font-size: var(--fs-th); color: var(--tx-primary); }}
        .surf-demo .mini-row {{ background: var(--bg-hover); border-radius: var(--r-sm); padding: 4px var(--sp-2); font-size: var(--fs-th); color: var(--tx-primary); }}
        .surf-demo .mini-th {{ background: var(--bg-inverse); color: var(--tx-ondark); border-radius: var(--r-sm); padding: 4px var(--sp-2); font-size: var(--fs-th); font-weight: var(--fw-semibold); }}
        .surf-name {{ padding: var(--sp-2) var(--sp-3); font-size: var(--fs-th); font-weight: var(--fw-bold); border-top: 1px solid var(--bg-divider); display: flex; justify-content: space-between; align-items: baseline; }}
        .surf-name .hex {{ color: var(--tx-secondary); font-weight: var(--fw-regular); }}
        .surf-meta {{ padding: var(--sp-2) var(--sp-3) var(--sp-3); font-size: var(--fs-tag); }}
        .surf-meta .row {{ display: grid; grid-template-columns: 70px 1fr; gap: var(--sp-2); padding: 2px 0; line-height: 1.4; }}
        .surf-meta .k {{ color: var(--tx-secondary); }}
        .surf-meta .v {{ color: var(--tx-primary); }}
    </style>
</head>
<body>
    <h1>Pinkspink — Styleguide</h1>
    <p class="sub">Все визуальные токены проекта. Источник правды — словарь <code>TOKENS</code> в <code>generate_report.py</code>.<br>
    Чтобы что-то изменить: правишь значение в TOKENS → запускаешь <code>python generate_report.py --styleguide</code> для проверки и <code>--grain all</code> для пересборки отчётов.</p>

    <h2>1. Цвета каналов</h2>
    <div class="sw-grid">{swatches("channel", "c-channel-")}</div>

    <h2>2. Цвета воронки</h2>
    <div class="sw-grid">{swatches("funnel", "c-funnel-")}</div>

    <h2>3. Семантика</h2>
    <div class="sem-row">
        <span class="sem-tag growth">↑ +12.4%</span>
        <span class="sem-tag decline">↓ −8.1%</span>
        <span class="sem-tag neutral">— 0%</span>
        <span class="sem-tag highlight">★ Подсветка</span>
    </div>
    <div class="sw-grid">{swatches("semantic", "c-")}</div>

    <h2>4. Поверхности</h2>
    <p class="sub">Цвета фонов и бордеров. Каждая карточка показывает: <strong>как выглядит сама поверхность</strong> с типичным содержимым сверху, <strong>где</strong> она применяется, <strong>что</strong> на ней обычно лежит, и <strong>какой цвет текста</strong> с ней сочетается.</p>
    <div class="surf-grid">{surface_cards()}</div>

    <h2>5. Текст</h2>
    <p class="sub">Цвета текста на разных поверхностях.</p>
    <div class="sw-grid">{swatches("text", "tx-", TEXT_USAGE)}</div>

    <h2>6. Типографика — шкала размеров</h2>
    <p class="meta" style="margin-bottom:var(--sp-3)">Шрифт: <code>{tokens['type']['family']}</code>. Каждая ступень показана с её <em>родным</em> весом — тем, который реально применяется в дашборде.</p>
    {''.join(type_rows)}

    <h2>7. Типографика — веса</h2>
    <p class="sub">Три толщины начертания. Используются на разных размерах в зависимости от роли (см. шкалу выше).</p>
    {''.join(weight_rows)}

    <h2>8. Кнопки и переключатели</h2>
    <p class="sub">Три типа кнопок в дашборде: <code>.grain-btn</code> (фильтры grain), <code>.tab-btn</code> (вкладки), <code>.grain-sq</code> (квадратные day/W/M в шапке). Показаны три состояния: default, hover, active.</p>

    <div class="btn-row">
        <span class="label"><code>.grain-btn</code></span>
        <button class="grain-btn">default</button>
        <button class="grain-btn is-hover">hover</button>
        <button class="grain-btn is-active">active</button>
    </div>
    <div class="btn-row">
        <span class="label"><code>.tab-btn</code></span>
        <button class="tab-btn">default</button>
        <button class="tab-btn is-hover">hover</button>
        <button class="tab-btn is-active">active</button>
    </div>
    <div class="btn-row">
        <span class="label"><code>.grain-sq</code></span>
        <span class="grain-sq">D</span>
        <span class="grain-sq is-hover">W</span>
        <span class="grain-sq">M</span>
    </div>
    <div class="btn-row">
        <span class="label"><code>.bubble-filters</code></span>
        <div class="bubble-filters-demo">
            <label><input type="checkbox" checked> ig</label>
            <label><input type="checkbox" checked> meta (paid)</label>
            <label><input type="checkbox"> google</label>
            <label><input type="checkbox" checked> (direct)</label>
        </div>
    </div>

    <h2>9. Spacing (4/8 шкала)</h2>
    {''.join(space_rows)}

    <h2>10. Радиусы</h2>
    <div class="rad-grid">{''.join(radius_cards)}</div>

    <h2>11. Тени</h2>
    <div class="sh-grid">
        <div class="sh-cell card-sh"><code>--sh-card</code><br><span class="meta">{tokens['shadow']['card']}</span></div>
    </div>

    <h2>12. Таблица (пример)</h2>
    <table class="data-table">
        <thead><tr><th>Канал</th><th>Сессии</th><th>ATC</th><th>Конверсия</th></tr></thead>
        <tbody>
            <tr><td>Social</td><td>1 234</td><td>56</td><td class="highlight">4.5%</td></tr>
            <tr><td>Paid</td><td>342</td><td>3</td><td>0.9%</td></tr>
            <tr><td>Direct</td><td>523</td><td>21</td><td class="highlight">4.0%</td></tr>
        </tbody>
    </table>

    <h2>13. KPI-карточки — три варианта</h2>
    <p class="sub">В дашборде используются три формата KPI: компактная 2×2 без графика, 2×2 со спарклайном внизу, и блок-сетка <code>.kpi-grid</code> на странице «Сводка» (карточки разной ширины/высоты). Цифры в них — это <code>--fs-kpi-xl</code> (28px) или <code>--fs-kpi-lg</code> (20px) в зависимости от плотности.</p>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-3);margin-bottom:var(--sp-2)">A — Компактная (без спарклайна)</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)">Для случаев, когда динамика не важна — только текущее значение и дельта.</p>
    <div class="kpi-demo">
        <div class="cell-kpi" style="height:140px">
            <div class="kpi-label">Сессии</div>
            <div class="kpi-value">12 845</div>
            <div class="kpi-bench">vs 4w avg: <span style="color:var(--c-growth)">+12.4%</span></div>
        </div>
        <div class="cell-kpi" style="height:140px">
            <div class="kpi-label">Доход</div>
            <div class="kpi-value">$630</div>
            <div class="kpi-bench">vs 4w avg: <span style="color:var(--c-decline)">−8.1%</span></div>
        </div>
        <div class="cell-kpi" style="height:140px">
            <div class="kpi-label">Конверсия</div>
            <div class="kpi-value">0.3%</div>
            <div class="kpi-bench">vs 4w avg: <span style="color:var(--c-neutral)">— 0%</span></div>
        </div>
    </div>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-4);margin-bottom:var(--sp-2)">B — Со спарклайном</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)">Когда нужно показать тренд за период. Спарклайн рисуется в <code>.kpi-spark</code> (фон <code>--bg-muted</code>, радиус <code>--r-lg</code>).</p>
    <div class="kpi-demo">
        <div class="cell-kpi" style="height:200px">
            <div class="kpi-label">Сессии</div>
            <div class="kpi-value">12 845</div>
            <div class="kpi-bench">vs 4w avg: <span style="color:var(--c-growth)">+12.4%</span></div>
            <div class="kpi-spark"><div class="chart-wrap" style="position:relative;height:100%;padding:0;box-shadow:none;background:transparent"><canvas id="spark-1"></canvas></div></div>
        </div>
        <div class="cell-kpi" style="height:200px">
            <div class="kpi-label">Доход</div>
            <div class="kpi-value">$630</div>
            <div class="kpi-bench">vs 4w avg: <span style="color:var(--c-decline)">−8.1%</span></div>
            <div class="kpi-spark"><div class="chart-wrap" style="position:relative;height:100%;padding:0;box-shadow:none;background:transparent"><canvas id="spark-2"></canvas></div></div>
        </div>
    </div>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-4);margin-bottom:var(--sp-2)">C — Блок <code>.kpi-grid</code> (страница «Сводка»)</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)">Сетка из 5 карточек разной ширины/высоты — <code>--fs-kpi-lg</code> (20px), <code>--fs-tag</code> (10px) для лейблов. Все цифры рядом, на одном «дыхании».</p>
    <div class="kpi-grid-demo">
        <div class="cell-kpi kg kg-rps"><div class="kpi-label">Сессии</div><div class="kpi-value-sm">12 845</div></div>
        <div class="cell-kpi kg kg-rev"><div class="kpi-label">Доход</div><div class="kpi-value-sm">$630</div></div>
        <div class="cell-kpi kg kg-atc"><div class="kpi-label">ATC</div><div class="kpi-value-sm">2.1%</div><div class="kpi-bench" style="font-size:var(--fs-tag)">vs 4w: <span style="color:var(--c-growth)">+0.3pp</span></div></div>
        <div class="cell-kpi kg kg-pr"><div class="kpi-label">Покупки</div><div class="kpi-value-sm">0.3%</div><div class="kpi-bench" style="font-size:var(--fs-tag)">vs 4w: <span style="color:var(--c-decline)">−0.1pp</span></div></div>
        <div class="cell-kpi kg kg-c2p"><div class="kpi-label">Cart→Purchase</div><div class="kpi-value-sm">14.3%</div></div>
    </div>

    <h2>14. Графики — пять типов</h2>
    <p class="sub">В дашборде используется 5 паттернов Chart.js. У каждого свои конвенции по подписям (datalabels), легенде и формату значений. Шрифт, цвет осей и сетки берутся из <code>TOKENS["chart"]</code> через <code>Chart.defaults</code> (применяется один раз при загрузке).</p>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-4);margin-bottom:var(--sp-2)">A — Grouped Bar (воронка по периодам)</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)"><strong>Где:</strong> блок «Динамика воронок».
    <strong>Подписи:</strong> <code>anchor:'end'</code>, <code>align:'top'</code> — над столбиком, формат <code>v &gt; 0 ? v : ''</code> (нули прячем).
    <strong>Легенда:</strong> сверху. <strong>Шкала Y:</strong> <code>beginAtZero:true</code>, <code>grace:'15%'</code> для воздуха над столбиками.</p>
    <div class="chart-wrap"><canvas id="demo-grouped-bar"></canvas></div>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-4);margin-bottom:var(--sp-2)">B — Line с подписями (конверсия %)</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)"><strong>Где:</strong> «catalog→product», «product→ATC» и т.п. в воронке.
    <strong>Подписи:</strong> <code>align:'top'</code>, формат <code>v.toFixed(1) + '%'</code>.
    <strong>Tooltip:</strong> custom callback с <code>%</code>. <strong>Шкала Y:</strong> ticks с <code>v + '%'</code>.</p>
    <div class="chart-wrap"><canvas id="demo-line"></canvas></div>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-4);margin-bottom:var(--sp-2)">C — Stacked Bar + Line (комбо, dual-axis)</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)"><strong>Где:</strong> Сессии по каналам (stacked) + Покупатели (линия) на одном графике.
    <strong>Подписи:</strong> <code>display:false</code> для bar, или внутри столбиков (<code>color:#FFF</code>).
    <strong>Оси:</strong> Y слева для bar, Y1 справа для line, <code>grid.drawOnChartArea:false</code> у Y1.</p>
    <div class="chart-wrap"><canvas id="demo-stacked-line"></canvas></div>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-4);margin-bottom:var(--sp-2)">D — Bubble (эффективность source)</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)"><strong>Где:</strong> «Каталог→Товар», «Товар→Корзина» — соотношение объём × конверсия × размер.
    <strong>Оси:</strong> X = сессии на этапе, Y = конверсия в следующий, размер пузыря = объём.
    <strong>Подписи:</strong> по умолчанию выключены, label виден в tooltip.</p>
    <div class="chart-wrap"><canvas id="demo-bubble"></canvas></div>

    <h3 style="font-size:var(--fs-h3);margin-top:var(--sp-4);margin-bottom:var(--sp-2)">E — Sparkline (мини-линия в KPI)</h3>
    <p class="meta" style="margin-bottom:var(--sp-2)"><strong>Где:</strong> внутри <code>.kpi-spark</code> в KPI-карточках.
    <strong>Подписи и легенда:</strong> <code>display:false</code>.
    <strong>Оси:</strong> скрыты (<code>display:false</code>). Только линия и точки. Нужна для тренда «глазом», не для считывания значений.</p>
    <div style="background:var(--bg-muted);border-radius:var(--r-lg);padding:var(--sp-1);height:60px;width:240px"><div class="chart-wrap" style="height:100%;padding:0;box-shadow:none;background:transparent"><canvas id="demo-spark"></canvas></div></div>

    <script>
    {chart_js_defaults}

    const cssvar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

    // A — Grouped Bar (funnel)
    new Chart(document.getElementById('demo-grouped-bar'), {{
        type: 'bar',
        data: {{
            labels: ['W04', 'W05', 'W06', 'W07', 'W08'],
            datasets: [
                {{ label: 'home',     backgroundColor: cssvar('--c-funnel-home'),     data: [80, 95, 92, 110, 125] }},
                {{ label: 'catalog',  backgroundColor: cssvar('--c-funnel-catalog'),  data: [120, 145, 132, 178, 201] }},
                {{ label: 'product',  backgroundColor: cssvar('--c-funnel-product'),  data: [60, 72, 68, 85, 96] }},
                {{ label: 'ATC',      backgroundColor: cssvar('--c-funnel-atc'),      data: [12, 14, 11, 18, 22] }},
                {{ label: 'purchase', backgroundColor: cssvar('--c-funnel-purchase'), data: [1, 2, 1, 3, 4] }}
            ]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'top' }},
                datalabels: {{ anchor: 'end', align: 'top', formatter: v => v > 0 ? v : '' }}
            }},
            scales: {{ y: {{ beginAtZero: true, grace: '15%' }} }}
        }}
    }});

    // B — Line с подписями
    new Chart(document.getElementById('demo-line'), {{
        type: 'line',
        data: {{
            labels: ['W04', 'W05', 'W06', 'W07', 'W08'],
            datasets: [
                {{ label: 'catalog→product', borderColor: cssvar('--c-funnel-product'), backgroundColor: cssvar('--c-funnel-product'), tension: 0.3, data: [42.1, 49.6, 51.5, 47.8, 52.4] }},
                {{ label: 'product→ATC',     borderColor: cssvar('--c-funnel-atc'),     backgroundColor: cssvar('--c-funnel-atc'),     tension: 0.3, data: [20.0, 19.4, 16.2, 21.2, 22.9] }}
            ]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'top' }},
                datalabels: {{ align: 'top', formatter: v => v != null ? v.toFixed(1) + '%' : '' }},
                tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%' }} }}
            }},
            scales: {{ y: {{ beginAtZero: true, grace: '15%', ticks: {{ callback: v => v + '%' }} }} }}
        }}
    }});

    // C — Stacked Bar + Line (dual axis)
    new Chart(document.getElementById('demo-stacked-line'), {{
        data: {{
            labels: ['W04', 'W05', 'W06', 'W07', 'W08'],
            datasets: [
                {{ type: 'bar', label: 'Social',  backgroundColor: cssvar('--c-channel-social'),  data: [120, 145, 132, 178, 201], stack: 's', yAxisID: 'y' }},
                {{ type: 'bar', label: 'Paid',    backgroundColor: cssvar('--c-channel-paid'),    data: [45, 52, 48, 60, 55],     stack: 's', yAxisID: 'y' }},
                {{ type: 'bar', label: 'Direct',  backgroundColor: cssvar('--c-channel-direct'),  data: [80, 75, 82, 95, 98],     stack: 's', yAxisID: 'y' }},
                {{ type: 'line', label: 'Покупатели', borderColor: cssvar('--c-growth'), borderWidth: 2, tension: 0.3, data: [4, 5, 4, 7, 8], yAxisID: 'y1' }}
            ]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            plugins: {{ legend: {{ position: 'top' }}, datalabels: {{ display: false }} }},
            scales: {{
                x: {{ stacked: true }},
                y:  {{ stacked: true, beginAtZero: true, position: 'left' }},
                y1: {{ beginAtZero: true, position: 'right', grid: {{ drawOnChartArea: false }} }}
            }}
        }}
    }});

    // D — Bubble
    new Chart(document.getElementById('demo-bubble'), {{
        type: 'bubble',
        data: {{
            datasets: [
                {{ label: 'ig',          backgroundColor: cssvar('--c-channel-social'),  data: [{{x: 1234, y: 4.5, r: 18}}] }},
                {{ label: 'meta (paid)', backgroundColor: cssvar('--c-channel-paid'),    data: [{{x: 342, y: 0.9, r: 8}}] }},
                {{ label: '(direct)',    backgroundColor: cssvar('--c-channel-direct'),  data: [{{x: 523, y: 4.0, r: 12}}] }},
                {{ label: 'google',      backgroundColor: cssvar('--c-channel-organic'), data: [{{x: 89, y: 6.7, r: 5}}] }}
            ]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            plugins: {{ legend: {{ position: 'top' }}, datalabels: {{ display: false }} }},
            scales: {{
                x: {{ title: {{ display: true, text: 'Сессии на этапе' }} }},
                y: {{ title: {{ display: true, text: 'Конверсия в след. этап, %' }}, ticks: {{ callback: v => v + '%' }} }}
            }}
        }}
    }});

    // E — Sparkline (mini-line, no axes/labels)
    function spark(id, data, color) {{
        new Chart(document.getElementById(id), {{
            type: 'line',
            data: {{
                labels: data.map((_, i) => i),
                datasets: [{{ data, borderColor: color, borderWidth: 1.5, tension: 0.4, pointRadius: 0, fill: false }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }}, datalabels: {{ display: false }}, tooltip: {{ enabled: false }} }},
                scales: {{ x: {{ display: false }}, y: {{ display: false }} }}
            }}
        }});
    }}
    spark('demo-spark', [120, 145, 132, 178, 201, 188, 220], cssvar('--c-channel-social'));
    spark('spark-1',    [120, 145, 132, 178, 201, 188, 220], cssvar('--c-channel-social'));
    spark('spark-2',    [60, 55, 65, 50, 45, 48, 42],         cssvar('--c-decline'));
    </script>
</body>
</html>"""


# ============================================================
# DATA FETCHING
# ============================================================

def get_client():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/bigquery"]
    )
    return bigquery.Client(credentials=creds, project=BQ_PROJECT)


def get_date_range(grain):
    end = datetime.now()
    if grain == "day":
        start = end - timedelta(days=14)
    elif grain == "week":
        start = end - timedelta(weeks=12)
    else:
        start = datetime(2026, 2, 5)  # beginning of data
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def period_sql(grain):
    if grain == "day":
        return "CAST(date AS STRING)"
    elif grain == "week":
        return "FORMAT_DATE('%G-W%V', date)"
    else:
        return "FORMAT_DATE('%Y-%m', date)"


def fetch_session_data(client, grain):
    """Fetch all session-level data grouped by period/channel/source/country/device."""
    start, end = get_date_range(grain)
    period = period_sql(grain)

    sql = f"""
    WITH events AS (
        SELECT
            PARSE_DATE('%Y%m%d', event_date) AS date,
            user_pseudo_id,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'session_engaged') AS session_engaged,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec') AS engagement_time_msec,
            event_name,
            REGEXP_EXTRACT((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'), r'https?://[^/]+(/.*)?') AS page_path,
            IFNULL(ecommerce.purchase_revenue, 0) AS purchase_revenue,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_number') AS ga_session_number,
            geo.country,
            device.category AS device,
            CASE
                WHEN IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) IN ('paid', 'cpm')
                    OR REGEXP_CONTAINS(IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')), r'(?i)instagram_|facebook_') THEN 'meta (paid)'
                ELSE IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), IFNULL(traffic_source.source, '(direct)'))
            END AS source,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) AS medium
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
    ),
    sessions AS (
        SELECT
            {period} AS period,
            {CHANNEL_SQL} AS channel,
            source,
            country,
            device,
            user_pseudo_id,
            session_id,
            MAX(session_engaged) AS session_engaged,
            SUM(engagement_time_msec) AS eng_ms,
            COUNTIF(event_name = 'page_view') AS pages,
            MAX(CASE WHEN event_name = 'page_view' AND REGEXP_CONTAINS(IFNULL(page_path, ''), r'^/(ja|ru)?/?$') THEN 1 ELSE 0 END) AS has_homepage,
            MAX(CASE WHEN event_name = 'page_view' AND REGEXP_CONTAINS(IFNULL(page_path, ''), r'/collections/') AND NOT REGEXP_CONTAINS(IFNULL(page_path, ''), r'/products/') THEN 1 ELSE 0 END) AS has_catalog,
            MAX(CASE WHEN event_name = 'view_item' THEN 1 ELSE 0 END) AS has_product,
            COUNTIF(event_name = 'view_item') AS product_views,
            MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) AS has_atc,
            MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS has_checkout,
            MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS has_purchase,
            MAX(purchase_revenue) AS revenue,
            MIN(IFNULL(ga_session_number, 1)) AS session_number
        FROM events
        GROUP BY period, channel, source, country, device, user_pseudo_id, session_id
    )
    SELECT
        period, channel, source, country, device,
        COUNT(*) AS sessions,
        COUNT(DISTINCT user_pseudo_id) AS users,
        COUNTIF(session_engaged = '1') AS engaged_sessions,
        ROUND(APPROX_QUANTILES(eng_ms, 100)[OFFSET(50)] / 1000.0, 1) AS median_eng_sec,
        ROUND(AVG(pages), 1) AS avg_pages,
        COUNTIF(pages = 1) AS sessions_1page,
        COUNTIF(pages >= 2 AND pages <= 5) AS sessions_2_5pages,
        COUNTIF(pages > 5) AS sessions_over5pages,
        ROUND(AVG(IF(product_views > 0, product_views, NULL)), 1) AS avg_product_views,
        ROUND(APPROX_QUANTILES(IF(product_views > 0, product_views, NULL), 100)[OFFSET(50)], 1) AS median_product_views,
        SUM(has_homepage) AS funnel_homepage,
        SUM(has_catalog) AS funnel_catalog,
        SUM(has_product) AS funnel_product,
        SUM(has_atc) AS funnel_atc,
        SUM(has_checkout) AS funnel_checkout,
        SUM(has_purchase) AS funnel_purchase,
        ROUND(SUM(revenue), 2) AS revenue,
        COUNTIF(session_number = 1) AS new_users,
        COUNTIF(session_number > 1) AS returning_users
    FROM sessions
    WHERE channel != 'Spam'
    GROUP BY period, channel, source, country, device
    ORDER BY period, channel
    """

    print(f"  Fetching data ({grain})...")
    rows = list(client.query(sql).result())
    print(f"  Got {len(rows)} rows")
    return rows


def fetch_analytics_data(client, grain):
    """Fetch data for the Card-product tab: scroll, catalog depth, cohort retention, time on cards."""
    start, end = get_date_range(grain)
    period = period_sql(grain)
    analytics = {}

    # 2. Scroll depth by channel × device × period
    print("  Fetching scroll data...")
    sql_scroll = f"""
    WITH events AS (
        SELECT
            PARSE_DATE('%Y%m%d', event_date) AS date,
            user_pseudo_id,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
            event_name,
            REGEXP_EXTRACT((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'), r'https?://[^/]+(/.*)?') AS page_path,
            device.category AS device,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) AS medium,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), IFNULL(traffic_source.source, '(direct)')) AS source
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
    ),
    sessions AS (
        SELECT
            {period} AS period,
            {CHANNEL_SQL} AS channel,
            device,
            user_pseudo_id, session_id,
            MAX(CASE WHEN event_name = 'scroll' THEN 1 ELSE 0 END) AS has_scroll,
            MAX(CASE WHEN event_name = 'scroll' AND REGEXP_CONTAINS(IFNULL(page_path,''), r'/products/') THEN 1 ELSE 0 END) AS scroll_product,
            MAX(CASE WHEN event_name = 'scroll' AND REGEXP_CONTAINS(IFNULL(page_path,''), r'/collections/') THEN 1 ELSE 0 END) AS scroll_catalog,
            MAX(CASE WHEN event_name = 'view_item' THEN 1 ELSE 0 END) AS has_product
        FROM events
        GROUP BY period, channel, device, source, medium, user_pseudo_id, session_id
    )
    SELECT
        period, channel, device,
        COUNT(*) AS sessions,
        SUM(has_scroll) AS sessions_with_scroll,
        SUM(scroll_product) AS scroll_on_product,
        SUM(scroll_catalog) AS scroll_on_catalog,
        SUM(has_product) AS sessions_with_product
    FROM sessions
    WHERE channel != 'Spam'
    GROUP BY period, channel, device
    ORDER BY period, channel, device
    """
    scroll_rows = list(client.query(sql_scroll).result())
    analytics["scroll"] = [dict(r) for r in scroll_rows]

    # 3. Catalog browsing depth by period
    print("  Fetching catalog depth...")
    period_raw = period.replace("date", "PARSE_DATE('%Y%m%d', event_date)")
    sql_catalog = f"""
    WITH catalog_views AS (
        SELECT
            {period_raw} AS period,
            user_pseudo_id,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
            IFNULL(SAFE_CAST(REGEXP_EXTRACT(
                (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'),
                r'[?&]page=(\d+)'
            ) AS INT64), 1) AS page_num
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
            AND event_name = 'page_view'
            AND REGEXP_CONTAINS(
                IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'), ''),
                r'/collections/'
            )
            AND NOT REGEXP_CONTAINS(
                IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'), ''),
                r'/products/'
            )
    ),
    session_max AS (
        SELECT period, user_pseudo_id, session_id, MAX(page_num) AS max_page
        FROM catalog_views
        GROUP BY period, user_pseudo_id, session_id
    )
    SELECT
        period,
        COUNT(*) AS sessions,
        COUNTIF(max_page = 1) AS page1,
        COUNTIF(max_page = 2) AS page2,
        COUNTIF(max_page = 3) AS page3,
        COUNTIF(max_page >= 4) AS page4plus
    FROM session_max
    GROUP BY period
    ORDER BY period
    """
    catalog_rows = list(client.query(sql_catalog).result())
    analytics["catalog_depth"] = [dict(r) for r in catalog_rows]

    # 4. Cohort retention (by week of first visit)
    print("  Fetching cohort retention...")
    sql_cohort = f"""
    WITH first_visits AS (
        SELECT user_pseudo_id, MIN(PARSE_DATE('%Y%m%d', event_date)) AS first_date
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '20260205' AND '{end}'
            AND event_name = 'first_visit'
        GROUP BY user_pseudo_id
    ),
    returns AS (
        SELECT DISTINCT
            fv.user_pseudo_id,
            FORMAT_DATE('%G-W%V', fv.first_date) AS cohort_week,
            DATE_DIFF(PARSE_DATE('%Y%m%d', e.event_date), fv.first_date, WEEK) AS weeks_since
        FROM first_visits fv
        JOIN `{BQ_PROJECT}.{BQ_DATASET}.events_*` e
            ON fv.user_pseudo_id = e.user_pseudo_id
        WHERE e._TABLE_SUFFIX BETWEEN '20260205' AND '{end}'
            AND e.event_name = 'session_start'
    )
    SELECT cohort_week, weeks_since, COUNT(DISTINCT user_pseudo_id) AS users
    FROM returns
    WHERE weeks_since BETWEEN 0 AND 8
    GROUP BY cohort_week, weeks_since
    ORDER BY cohort_week, weeks_since
    """
    cohort_rows = list(client.query(sql_cohort).result())
    analytics["cohort"] = [dict(r) for r in cohort_rows]

    # 5. Time on product page (median engagement per session with view_item, by channel/period)
    print("  Fetching time on product...")
    sql_product_time = f"""
    WITH events AS (
        SELECT
            PARSE_DATE('%Y%m%d', event_date) AS date,
            user_pseudo_id,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec') AS engagement_time_msec,
            event_name,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), IFNULL(traffic_source.source, '(direct)')) AS source,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) AS medium
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
    ),
    sessions AS (
        SELECT
            {period} AS period,
            {CHANNEL_SQL} AS channel,
            user_pseudo_id, session_id,
            SUM(engagement_time_msec) AS eng_ms,
            MAX(CASE WHEN event_name = 'view_item' THEN 1 ELSE 0 END) AS has_product
        FROM events
        GROUP BY period, channel, source, medium, user_pseudo_id, session_id
    )
    SELECT
        period, channel,
        COUNT(*) AS sessions_with_product,
        ROUND(APPROX_QUANTILES(eng_ms / 1000.0, 100)[OFFSET(50)], 1) AS median_sec,
        ROUND(AVG(eng_ms / 1000.0), 1) AS avg_sec
    FROM sessions
    WHERE has_product = 1 AND channel != 'Spam'
    GROUP BY period, channel
    ORDER BY period, channel
    """
    product_time_rows = list(client.query(sql_product_time).result())
    analytics["product_time"] = [dict(r) for r in product_time_rows]

    # 6. Per-card view time (time spent on a single product card, capped at 300s)
    print("  Fetching per-card time...")
    sql_per_card = f"""
    WITH events AS (
        SELECT
            PARSE_DATE('%Y%m%d', event_date) AS date,
            user_pseudo_id,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
            event_name,
            event_timestamp,
            geo.country,
            device.category AS device,
            CASE
                WHEN IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) IN ('paid', 'cpm')
                    OR REGEXP_CONTAINS(IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')), r'(?i)instagram_|facebook_') THEN 'meta (paid)'
                ELSE IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), IFNULL(traffic_source.source, '(direct)'))
            END AS source,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) AS medium
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
    ),
    ordered AS (
        SELECT
            date, user_pseudo_id, session_id, event_name, event_timestamp,
            country, device, source, medium,
            {CHANNEL_SQL} AS channel,
            LEAD(event_timestamp) OVER (
                PARTITION BY user_pseudo_id, session_id
                ORDER BY event_timestamp
            ) AS next_ts
        FROM events
    ),
    card_views AS (
        SELECT
            {period} AS period,
            channel, source, country,
            LEAST((next_ts - event_timestamp) / 1000000.0, 300.0) AS sec_on_card
        FROM ordered
        WHERE event_name = 'view_item' AND next_ts IS NOT NULL AND channel != 'Spam'
    )
    SELECT
        period, channel, source, country,
        COUNT(*) AS card_views,
        ROUND(APPROX_QUANTILES(sec_on_card, 100)[OFFSET(50)], 1) AS median_sec,
        ROUND(AVG(sec_on_card), 1) AS mean_sec
    FROM card_views
    GROUP BY period, channel, source, country
    """
    per_card_rows = list(client.query(sql_per_card).result())
    analytics["per_card_time"] = [dict(r) for r in per_card_rows]

    # 7. Top product cards (by views and time-on-card) for the last full period
    print("  Fetching top products...")
    sql_top_products = f"""
    WITH events AS (
        SELECT
            PARSE_DATE('%Y%m%d', event_date) AS date,
            user_pseudo_id,
            (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
            event_name,
            event_timestamp,
            geo.country,
            items
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
    ),
    ordered AS (
        SELECT
            date, user_pseudo_id, session_id, event_name, event_timestamp, country, items,
            LEAD(event_timestamp) OVER (
                PARTITION BY user_pseudo_id, session_id
                ORDER BY event_timestamp
            ) AS next_ts
        FROM events
    ),
    view_items AS (
        SELECT
            {period} AS period,
            items[SAFE_OFFSET(0)].item_id AS item_id,
            items[SAFE_OFFSET(0)].item_name AS item_name,
            user_pseudo_id, session_id,
            LEAST((next_ts - event_timestamp) / 1000000.0, 300.0) AS sec_on_card
        FROM ordered
        WHERE event_name = 'view_item' AND ARRAY_LENGTH(items) > 0
    ),
    atc_items AS (
        SELECT
            {period} AS period,
            items[SAFE_OFFSET(0)].item_id AS item_id,
            user_pseudo_id, session_id
        FROM events
        WHERE event_name = 'add_to_cart' AND ARRAY_LENGTH(items) > 0
    ),
    purchase_items AS (
        SELECT
            {period} AS period,
            items[SAFE_OFFSET(0)].item_id AS item_id,
            user_pseudo_id, session_id
        FROM events
        WHERE event_name = 'purchase' AND ARRAY_LENGTH(items) > 0
    ),
    views_agg AS (
        SELECT
            period, item_id, ANY_VALUE(item_name) AS item_name,
            COUNT(*) AS views,
            COUNT(DISTINCT CONCAT(CAST(user_pseudo_id AS STRING), '|', CAST(session_id AS STRING))) AS view_sessions,
            ROUND(APPROX_QUANTILES(sec_on_card, 100)[OFFSET(50)], 1) AS median_sec,
            ROUND(AVG(sec_on_card), 1) AS mean_sec
        FROM view_items
        WHERE sec_on_card IS NOT NULL
        GROUP BY period, item_id
    ),
    atc_agg AS (
        SELECT period, item_id,
            COUNT(DISTINCT CONCAT(CAST(user_pseudo_id AS STRING), '|', CAST(session_id AS STRING))) AS atc
        FROM atc_items GROUP BY period, item_id
    ),
    purchase_agg AS (
        SELECT period, item_id,
            COUNT(DISTINCT CONCAT(CAST(user_pseudo_id AS STRING), '|', CAST(session_id AS STRING))) AS purchases
        FROM purchase_items GROUP BY period, item_id
    )
    SELECT
        v.period, v.item_id, v.item_name,
        v.views, v.view_sessions, v.median_sec, v.mean_sec,
        IFNULL(a.atc, 0) AS atc,
        IFNULL(p.purchases, 0) AS purchases
    FROM views_agg v
    LEFT JOIN atc_agg a ON v.period = a.period AND v.item_id = a.item_id
    LEFT JOIN purchase_agg p ON v.period = p.period AND v.item_id = p.item_id
    WHERE v.item_id IS NOT NULL
    ORDER BY v.period, v.views DESC
    """
    top_products_rows = list(client.query(sql_top_products).result())
    analytics["top_products"] = [dict(r) for r in top_products_rows]

    # Shorten period labels to match main data (2026-W07 → W07, etc.)
    def shorten(p):
        if '-W' in p:
            return p.replace('2026-', '')
        if len(p) == 10:
            return p[5:]
        return p.replace('2026-', '26-')

    for r in analytics.get("scroll", []):
        r["period"] = shorten(r["period"])
    for r in analytics.get("product_time", []):
        r["period"] = shorten(r["period"])
    for r in analytics.get("per_card_time", []):
        r["period"] = shorten(r["period"])
    for r in analytics.get("top_products", []):
        r["period"] = shorten(r["period"])
    for r in analytics.get("catalog_depth", []):
        r["period"] = shorten(r["period"])
    for r in analytics.get("cohort", []):
        r["cohort_week"] = shorten(r["cohort_week"])

    print(f"  Analytics data fetched")
    return analytics


# ============================================================
# DATA AGGREGATION HELPERS
# ============================================================

def aggregate(rows, group_keys, filter_fn=None):
    """Aggregate rows by group_keys, optionally filtering."""
    result = defaultdict(lambda: {
        "sessions": 0, "users": 0, "engaged_sessions": 0,
        "sessions_1page": 0, "sessions_2_5pages": 0, "sessions_over5pages": 0,
        "funnel_homepage": 0, "funnel_catalog": 0, "funnel_product": 0,
        "funnel_atc": 0, "funnel_checkout": 0, "funnel_purchase": 0,
        "revenue": 0, "new_users": 0, "returning_users": 0,
        "_eng_ms_values": [], "_avg_pv_values": [], "_med_pv_values": [],
    })

    for r in rows:
        if filter_fn and not filter_fn(r):
            continue
        key = tuple(getattr(r, k) for k in group_keys)
        d = result[key]
        d["sessions"] += r.sessions
        d["users"] += r.users
        d["engaged_sessions"] += r.engaged_sessions
        d["sessions_1page"] += r.sessions_1page
        d["sessions_2_5pages"] += r.sessions_2_5pages
        d["sessions_over5pages"] += r.sessions_over5pages
        d["funnel_homepage"] += r.funnel_homepage
        d["funnel_catalog"] += r.funnel_catalog
        d["funnel_product"] += r.funnel_product
        d["funnel_atc"] += r.funnel_atc
        d["funnel_checkout"] += r.funnel_checkout
        d["funnel_purchase"] += r.funnel_purchase
        d["revenue"] += float(r.revenue or 0)
        d["new_users"] += r.new_users
        d["returning_users"] += r.returning_users
        if r.median_eng_sec is not None:
            d["_eng_ms_values"].extend([r.median_eng_sec] * r.sessions)
        if r.avg_product_views is not None:
            d["_avg_pv_values"].extend([r.avg_product_views] * r.sessions)
        if getattr(r, "median_product_views", None) is not None:
            d["_med_pv_values"].extend([r.median_product_views] * r.sessions)

    # Post-process
    for key, d in result.items():
        d["er"] = round(d["engaged_sessions"] / d["sessions"] * 100, 1) if d["sessions"] > 0 else 0
        vals = d["_eng_ms_values"]
        d["median_eng_sec"] = round(sorted(vals)[len(vals) // 2], 1) if vals else 0
        d["deep_pct"] = round((d["sessions_2_5pages"] + d["sessions_over5pages"]) / d["sessions"] * 100, 1) if d["sessions"] > 0 else 0
        pv_vals = d["_avg_pv_values"]
        d["avg_product_views"] = round(sum(pv_vals) / len(pv_vals), 1) if pv_vals else 0
        del d["_avg_pv_values"]
        med_pv = d["_med_pv_values"]
        d["median_product_views"] = round(sorted(med_pv)[len(med_pv) // 2], 1) if med_pv else 0
        del d["_med_pv_values"]
        d["bounce_rate"] = round(d["sessions_1page"] / d["sessions"] * 100, 1) if d["sessions"] > 0 else 0
        d["cr"] = round(d["funnel_purchase"] / d["sessions"] * 100, 2) if d["sessions"] > 0 else 0
        d["atc_rate"] = round(d["funnel_atc"] / d["sessions"] * 100, 2) if d["sessions"] > 0 else 0
        d["cart_to_purchase"] = min(100.0, round(d["funnel_purchase"] / d["funnel_atc"] * 100, 1)) if d["funnel_atc"] > 0 else 0
        d["revenue_per_session"] = round(d["revenue"] / d["sessions"], 2) if d["sessions"] > 0 else 0
        d["cat_to_prod"] = min(100.0, round(d["funnel_product"] / d["funnel_catalog"] * 100, 1)) if d["funnel_catalog"] > 0 else 0
        d["prod_to_atc"] = min(100.0, round(d["funnel_atc"] / d["funnel_product"] * 100, 1)) if d["funnel_product"] > 0 else 0
        d["atc_to_checkout"] = min(100.0, round(d["funnel_checkout"] / d["funnel_atc"] * 100, 1)) if d["funnel_atc"] > 0 else 0
        d["checkout_to_purchase"] = min(100.0, round(d["funnel_purchase"] / d["funnel_checkout"] * 100, 1)) if d["funnel_checkout"] > 0 else 0
        del d["_eng_ms_values"]

    return dict(result)


def compute_deltas(current, previous):
    """Compute deltas between current and previous period metrics."""
    deltas = {}
    for key in ["sessions", "er", "median_eng_sec", "deep_pct"]:
        cur = current.get(key, 0)
        prev = previous.get(key, 0)
        if prev > 0:
            deltas[key] = round((cur - prev) / prev * 100, 1)
        else:
            deltas[key] = None
    deltas["share"] = round(current.get("sessions", 0) / current.get("_total_sessions", 1) * 100, 1)
    return deltas


def safe_div(a, b, pct=True):
    if b == 0:
        return 0
    val = a / b
    return round(val * 100, 1) if pct else round(val, 1)


def get_comparison_periods(grain):
    """How many previous periods to average against, based on grain."""
    return {"month": 3, "week": 4, "day": 7}.get(grain, 4)


def compute_delta_vs_prev(values_per_period, n_prev):
    """Returns % delta of current period vs average of N previous periods."""
    if not values_per_period or len(values_per_period) < 2:
        return None
    cur = values_per_period[-1]
    prev_vals = values_per_period[-(n_prev + 1):-1]
    if not prev_vals:
        return None
    avg = sum(prev_vals) / len(prev_vals)
    if avg == 0:
        return None
    return round((cur - avg) / avg * 100, 1)


def compute_delta_pp(values_per_period, n_prev):
    """Returns absolute delta in percentage points (for rate metrics)."""
    if not values_per_period or len(values_per_period) < 2:
        return None
    cur = values_per_period[-1]
    prev_vals = values_per_period[-(n_prev + 1):-1]
    if not prev_vals:
        return None
    avg = sum(prev_vals) / len(prev_vals)
    return round(cur - avg, 2)


# ============================================================
# HTML GENERATION
# ============================================================

CHANNEL_COLORS = {
    "Social":   TOKENS["channel"]["social"],
    "Direct":   TOKENS["channel"]["direct"],
    "Paid":     TOKENS["channel"]["paid"],
    "Organic":  TOKENS["channel"]["organic"],
    "Referral": TOKENS["channel"]["referral"],
    "Email":    TOKENS["channel"]["email"],
    "Other":    TOKENS["channel"]["other"],
}


def generate_html(rows, grain, excluded_countries, analytics_data=None):
    """Generate the full HTML dashboard."""

    # All countries actually present in the raw data (used by UI country filter dropdown)
    all_countries_in_data = sorted({r.country for r in rows if r.country})

    # Filter excluded countries
    filtered = [r for r in rows if r.country not in excluded_countries]
    periods_raw = sorted(set(r.period for r in filtered))

    # Drop incomplete current period (week/month)
    if grain in ("week", "month") and periods_raw:
        from datetime import date
        today = date.today()
        last_period = periods_raw[-1]
        if grain == "week":
            # Current ISO week — drop if it matches last period
            current_week = today.strftime("%G-W%V")
            if last_period == current_week:
                periods_raw = periods_raw[:-1]
        elif grain == "month":
            current_month = today.strftime("%Y-%m")
            if last_period == current_month:
                periods_raw = periods_raw[:-1]

    # Shorten period labels: 2026-W07 → W07, 2026-03-15 → 03-15, 2026-02 → 26-02
    def shorten_period(p):
        if '-W' in p:
            return p.replace('2026-', '')
        if len(p) == 10:  # day: 2026-03-15
            return p[5:]  # 03-15
        return p.replace('2026-', '26-')  # month
    periods = [shorten_period(p) for p in periods_raw]
    period_map = dict(zip(periods_raw, periods))

    # Remap period in rows for matching, filter to valid periods only
    class RowProxy:
        def __init__(self, row, new_period):
            self._row = row
            self.period = new_period
        def __getattr__(self, name):
            return getattr(self._row, name)

    valid_raw_periods = set(periods_raw)
    filtered = [RowProxy(r, period_map[r.period]) for r in filtered if r.period in valid_raw_periods]

    # ---- BLOCK 1: Funnel stages by period (mobile + desktop) ----
    FUNNEL_STAGES = [
        ("home",     "funnel_homepage", TOKENS["funnel"]["home"]),
        ("catalog",  "funnel_catalog",  TOKENS["funnel"]["catalog"]),
        ("product",  "funnel_product",  TOKENS["funnel"]["product"]),
        ("ATC",      "funnel_atc",      TOKENS["funnel"]["atc"]),
        ("checkout", "funnel_checkout", TOKENS["funnel"]["checkout"]),
        ("purchase", "funnel_purchase", TOKENS["funnel"]["purchase"]),
    ]

    def build_funnel_data(device_filter):
        agg = aggregate(filtered, ["period"], lambda r: r.device == device_filter)
        return {
            "labels": periods,
            "datasets": [
                {
                    "label": name,
                    "data": [agg.get((p,), {}).get(field, 0) for p in periods],
                    "backgroundColor": color,
                }
                for name, field, color in FUNNEL_STAGES
            ]
        }

    mobile_funnel = build_funnel_data("mobile")
    desktop_funnel = build_funnel_data("desktop")

    # ---- BLOCK 1b: Funnel step-to-step conversion % by period (mobile + desktop) ----
    FUNNEL_TRANSITIONS = [
        ("catalog→product",   "cat_to_prod",          TOKENS["funnel"]["product"]),
        ("product→ATC",       "prod_to_atc",          TOKENS["funnel"]["atc"]),
        ("ATC→checkout",      "atc_to_checkout",      TOKENS["funnel"]["checkout"]),
        ("checkout→purchase", "checkout_to_purchase", TOKENS["funnel"]["purchase"]),
    ]

    def build_funnel_pct_data(device_filter):
        agg = aggregate(filtered, ["period"], lambda r: r.device == device_filter)
        return {
            "labels": periods,
            "datasets": [
                {
                    "label": name,
                    "data": [agg.get((p,), {}).get(field, 0) for p in periods],
                    "borderColor": color,
                    "backgroundColor": color,
                    "tension": 0.3,
                    "pointRadius": 3,
                }
                for name, field, color in FUNNEL_TRANSITIONS
            ]
        }

    mobile_funnel_pct = build_funnel_pct_data("mobile")
    desktop_funnel_pct = build_funnel_pct_data("desktop")

    # ---- Helper: avg of last N periods for a metric ----
    def avg_prev_periods(by_period_key, key_val, metric, n=4):
        """Average a metric over the last n periods (excluding current)."""
        if len(periods) < 2:
            return 0
        prev_periods = periods[max(0, len(periods) - 1 - n):len(periods) - 1]
        vals = [by_period_key.get((*key_val, p) if isinstance(key_val, tuple) else (p, key_val), {}).get(metric, 0) for p in prev_periods]
        return round(sum(vals) / len(vals), 1) if vals else 0

    def compute_card_deltas(cur_data, by_period, key_val, metrics_list):
        """Compute deltas: current period vs avg of previous 4 periods."""
        deltas = {}
        for metric, suffix, absolute in metrics_list:
            cur_val = cur_data.get(metric, 0)
            avg_val = avg_prev_periods(by_period, key_val, metric)
            if absolute:
                deltas[f"delta_{metric}"] = round(cur_val - avg_val, 1) if avg_val > 0 or cur_val > 0 else None
            else:
                if avg_val > 0:
                    deltas[f"delta_{metric}"] = round((cur_val - avg_val) / avg_val * 100, 1)
                elif cur_val > 0:
                    deltas[f"delta_{metric}"] = None
                else:
                    deltas[f"delta_{metric}"] = None
        return deltas

    CARD_METRICS = [
        ("sessions", "%", False), ("er", " п.п.", False), ("median_eng_sec", "s", False),
        ("deep_pct", " п.п.", False), ("avg_product_views", "", True),
        ("median_product_views", "", True),
    ]

    # ---- BLOCK 2: Channel cards (mobile) ----
    def build_channel_cards(device):
        by_period_channel = aggregate(filtered, ["period", "channel"], lambda r: device is None or r.device == device)

        # Current period totals for share calculation
        cur_period = periods[-1] if periods else None
        cur_total = sum(d["sessions"] for k, d in by_period_channel.items() if k[0] == cur_period)

        # All channels sorted by current period sessions
        channels = sorted(
            set(k[1] for k in by_period_channel.keys()),
            key=lambda ch: by_period_channel.get((cur_period, ch), {}).get("sessions", 0),
            reverse=True
        )

        cards = []
        for ch in channels:
            if ch in ("Email", "Other", "Spam"):
                continue

            cur = by_period_channel.get((cur_period, ch), {"sessions": 0, "er": 0, "median_eng_sec": 0, "deep_pct": 0, "avg_product_views": 0, "median_product_views": 0})

            # Trend data
            trend = [by_period_channel.get((p, ch), {"sessions": 0})["sessions"] for p in periods]

            # Funnel data per period
            channel_funnel = {
                "labels": periods,
                "datasets": [
                    {
                        "label": name,
                        "data": [by_period_channel.get((p, ch), {}).get(field, 0) for p in periods],
                        "backgroundColor": color,
                    }
                    for name, field, color in FUNNEL_STAGES
                ]
            }

            # Deltas vs avg of prev 4 periods
            deltas = compute_card_deltas(cur, by_period_channel, ch, CARD_METRICS)

            # Top 5 countries (current period only)
            country_agg = aggregate(filtered, ["channel", "country"],
                lambda r: (device is None or r.device == device) and r.period == cur_period)
            top_countries = sorted(
                [(k[1], v["sessions"]) for k, v in country_agg.items() if k[0] == ch],
                key=lambda x: -x[1]
            )[:5]

            cards.append({
                "channel": ch,
                "color": CHANNEL_COLORS.get(ch, "#999"),
                "period": cur_period,
                "sessions": cur["sessions"],
                "share": round(cur["sessions"] / cur_total * 100, 1) if cur_total > 0 else 0,
                "er": cur["er"],
                "median_sec": cur["median_eng_sec"],
                "deep_pct": cur["deep_pct"],
                "avg_products": cur.get("avg_product_views", 0),
                "median_products": cur.get("median_product_views", 0),
                "trend": trend,
                "funnel": channel_funnel,
                "delta_sessions": deltas.get("delta_sessions"),
                "delta_er": deltas.get("delta_er"),
                "delta_median": deltas.get("delta_median_eng_sec"),
                "delta_deep": deltas.get("delta_deep_pct"),
                "delta_products": deltas.get("delta_median_product_views"),
                "top_countries": top_countries,
            })

        return cards

    channel_cards = build_channel_cards(None)

    # ---- BLOCK 3: Source cards (top 5) ----
    def build_source_cards(device):
        by_period_source = aggregate(filtered, ["period", "source"], lambda r: device is None or r.device == device)

        cur_period = periods[-1] if periods else None
        cur_total = sum(d["sessions"] for k, d in by_period_source.items() if k[0] == cur_period)

        # Top 5 sources by current period sessions
        source_cur = sorted(
            [(k[1], d["sessions"]) for k, d in by_period_source.items() if k[0] == cur_period],
            key=lambda x: -x[1]
        )[:5]

        cards = []
        for src, _ in source_cur:
            cur = by_period_source.get((cur_period, src), {"sessions": 0, "er": 0, "median_eng_sec": 0, "deep_pct": 0, "avg_product_views": 0, "median_product_views": 0})

            trend = [by_period_source.get((p, src), {"sessions": 0})["sessions"] for p in periods]

            source_funnel = {
                "labels": periods,
                "datasets": [
                    {
                        "label": name,
                        "data": [by_period_source.get((p, src), {}).get(field, 0) for p in periods],
                        "backgroundColor": color,
                    }
                    for name, field, color in FUNNEL_STAGES
                ]
            }

            deltas = compute_card_deltas(cur, by_period_source, src, CARD_METRICS)

            country_agg = aggregate(filtered, ["source", "country"],
                lambda r, s=src: (device is None or r.device == device) and r.period == cur_period)
            top_countries = sorted(
                [(k[1], v["sessions"]) for k, v in country_agg.items() if k[0] == src],
                key=lambda x: -x[1]
            )[:5]

            cards.append({
                "source": src,
                "period": cur_period,
                "sessions": cur["sessions"],
                "share": round(cur["sessions"] / cur_total * 100, 1) if cur_total > 0 else 0,
                "er": cur["er"],
                "median_sec": cur["median_eng_sec"],
                "deep_pct": cur["deep_pct"],
                "avg_products": cur.get("avg_product_views", 0),
                "median_products": cur.get("median_product_views", 0),
                "trend": trend,
                "funnel": source_funnel,
                "delta_sessions": deltas.get("delta_sessions"),
                "delta_er": deltas.get("delta_er"),
                "delta_median": deltas.get("delta_median_eng_sec"),
                "delta_deep": deltas.get("delta_deep_pct"),
                "delta_products": deltas.get("delta_median_product_views"),
                "top_countries": top_countries,
            })

        return cards

    source_cards = build_source_cards(None)

    # ---- BLOCK 4: Bubble charts by source / channel / country ----
    cur_period = periods[-1] if periods else None

    def build_bubble_data(group_key, device, min_sessions=5):
        agg = aggregate(filtered, [group_key],
            lambda r: (device is None or r.device == device) and r.period == cur_period)
        items = []
        for key_tuple, data in agg.items():
            name = key_tuple[0]
            if data["sessions"] < min_sessions:
                continue
            items.append({
                "name": name,
                "sessions": data["sessions"],
                "funnel_catalog": data["funnel_catalog"],
                "funnel_product": data["funnel_product"],
                "funnel_atc": data["funnel_atc"],
                "funnel_checkout": data["funnel_checkout"],
                "funnel_purchase": data["funnel_purchase"],
                "cat_to_prod": data["cat_to_prod"],
                "prod_to_atc": data["prod_to_atc"],
                "atc_to_checkout": data["atc_to_checkout"],
                "checkout_to_purchase": data["checkout_to_purchase"],
                "er": data["er"],
                "median_sec": data["median_eng_sec"],
            })
        return items

    bubble_channel_all = build_bubble_data("channel", None, min_sessions=0)
    bubble_channel = [
        item for item in sorted(bubble_channel_all, key=lambda x: -x["sessions"])
        if item["name"] not in ("Spam", "Other")
    ]

    # Attach Δ vs avg of 4 prev periods to bubble_channel items
    by_period_channel_full = aggregate(filtered, ["period", "channel"])
    for item in bubble_channel:
        ch = item["name"]
        cur = by_period_channel_full.get((cur_period, ch), {})
        for metric in ("cat_to_prod", "prod_to_atc", "atc_to_checkout", "checkout_to_purchase"):
            cur_val = cur.get(metric, 0)
            avg_val = avg_prev_periods(by_period_channel_full, ch, metric, n=4)
            if avg_val > 0 or cur_val > 0:
                item[f"delta_{metric}"] = round(cur_val - avg_val, 1)
            else:
                item[f"delta_{metric}"] = None

    # ---- BLOCK 4b: Channel conversion trend (line, % per stage by period) ----
    TREND_CHANNELS = ["Social", "Paid", "Direct", "Organic", "Referral", "Email"]
    present_channels = [
        ch for ch in TREND_CHANNELS
        if any(by_period_channel_full.get((p, ch), {}).get("sessions", 0) > 0 for p in periods)
    ]

    def build_channel_trend(metric_field):
        return {
            "labels": periods,
            "datasets": [
                {
                    "label": ch,
                    "data": [by_period_channel_full.get((p, ch), {}).get(metric_field) for p in periods],
                    "borderColor": CHANNEL_COLORS.get(ch, "#999"),
                    "backgroundColor": CHANNEL_COLORS.get(ch, "#999"),
                    "tension": 0.3,
                    "pointRadius": 3,
                    "spanGaps": True,
                }
                for ch in present_channels
            ]
        }

    channel_trend = {
        "channels": present_channels,
        "channel_colors": {ch: CHANNEL_COLORS.get(ch, "#999") for ch in present_channels},
        "cat_to_prod": build_channel_trend("cat_to_prod"),
        "prod_to_atc": build_channel_trend("prod_to_atc"),
        "atc_to_checkout": build_channel_trend("atc_to_checkout"),
        "checkout_to_purchase": build_channel_trend("checkout_to_purchase"),
    }

    # ---- BLOCK 4c: Per-stage tables (country × channel) for current period ----
    by_period_country_channel = aggregate(filtered, ["period", "country", "channel"])
    prev_periods_for_avg = periods[max(0, len(periods) - 1 - 4):len(periods) - 1] if len(periods) >= 2 else []

    def stage_table_rows(input_field, conv_field, min_input=5, top_n=30):
        rows = []
        for (p, country, ch), data in by_period_country_channel.items():
            if p != cur_period:
                continue
            if ch in ("Spam", "Other"):
                continue
            cur_input = data.get(input_field, 0)
            if cur_input < min_input:
                continue
            cur_conv = data.get(conv_field, 0)
            if prev_periods_for_avg:
                vals = [by_period_country_channel.get((pp, country, ch), {}).get(conv_field, 0) for pp in prev_periods_for_avg]
                avg_val = round(sum(vals) / len(vals), 1) if vals else 0
            else:
                avg_val = 0
            if avg_val > 0 or cur_conv > 0:
                delta = round(cur_conv - avg_val, 1)
            else:
                delta = None
            rows.append({
                "country": country,
                "channel": ch,
                "channel_color": CHANNEL_COLORS.get(ch, "#999"),
                "input": cur_input,
                "conv": cur_conv,
                "delta": delta,
            })
        rows.sort(key=lambda r: -r["input"])
        return rows[:top_n]

    stage_tables = {
        "prod":     stage_table_rows("funnel_catalog",  "cat_to_prod"),
        "atc":      stage_table_rows("funnel_product",  "prod_to_atc"),
        "checkout": stage_table_rows("funnel_atc",      "atc_to_checkout"),
        "purchase": stage_table_rows("funnel_checkout", "checkout_to_purchase"),
    }

    # ---- BLOCK 6: Bottom funnel detail table (ATC / Checkout / Purchase) ----
    cur_period_label = periods[-1] if periods else ""

    def build_bottom_funnel(device):
        agg = aggregate(filtered, ["source", "country"], lambda r: (device is None or r.device == device) and r.period == cur_period_label)
        table = []
        for (src, country), data in agg.items():
            if data["funnel_atc"] == 0 and data["funnel_checkout"] == 0 and data["funnel_purchase"] == 0:
                continue
            table.append({
                "source": src,
                "country": country,
                "sessions": data["sessions"],
                "catalog": data["funnel_catalog"],
                "product": data["funnel_product"],
                "atc": data["funnel_atc"],
                "checkout": data["funnel_checkout"],
                "purchase": data["funnel_purchase"],
            })
        return sorted(table, key=lambda x: (-x["atc"], -x["checkout"], -x["purchase"]))

    bottom_funnel = build_bottom_funnel(None)

    # ---- OVERVIEW: KPI + breakdowns ----

    # Total KPIs (all devices)
    overview_total = aggregate(filtered, ["period"])
    overview_kpis_trend = []
    for p in periods:
        d = overview_total.get((p,), {})
        overview_kpis_trend.append({
            "period": p,
            "sessions": d.get("sessions", 0),
            "cr": d.get("cr", 0),
            "atc_rate": d.get("atc_rate", 0),
            "cart_to_purchase": d.get("cart_to_purchase", 0),
            "revenue_per_session": d.get("revenue_per_session", 0),
            "bounce_rate": d.get("bounce_rate", 0),
            "revenue": round(d.get("revenue", 0), 2),
            "new_users": d.get("new_users", 0),
            "returning_users": d.get("returning_users", 0),
        })

    # Current period KPIs + deltas vs avg of previous 4 periods
    cur_kpis = overview_kpis_trend[-1] if overview_kpis_trend else {}
    n_prev = min(4, len(overview_kpis_trend) - 1)
    if n_prev > 0:
        prev_kpis = overview_kpis_trend[-(n_prev + 1):-1]
        for metric in ["sessions", "cr", "atc_rate", "cart_to_purchase", "revenue_per_session", "bounce_rate", "revenue"]:
            avg_val = sum(p.get(metric, 0) for p in prev_kpis) / len(prev_kpis)
            cur_val = cur_kpis.get(metric, 0)
            if avg_val > 0:
                cur_kpis[f"delta_{metric}"] = round((cur_val - avg_val) / avg_val * 100, 1)
            elif cur_val > 0:
                cur_kpis[f"delta_{metric}"] = None
            else:
                cur_kpis[f"delta_{metric}"] = None
        # New/returning — absolute delta in percentage points
        prev_new_total = sum(p.get("new_users", 0) + p.get("returning_users", 0) for p in prev_kpis)
        prev_new_pct = round(sum(p.get("new_users", 0) for p in prev_kpis) / prev_new_total * 100, 1) if prev_new_total > 0 else 0
        cur_total_users = cur_kpis.get("new_users", 0) + cur_kpis.get("returning_users", 0)
        cur_new_pct = round(cur_kpis.get("new_users", 0) / cur_total_users * 100, 1) if cur_total_users > 0 else 0
        cur_kpis["delta_new_pct"] = round(cur_new_pct - prev_new_pct, 1)

    # KPIs by channel (current period, all devices)
    overview_by_channel = aggregate(filtered, ["channel"], lambda r: r.period == cur_period_label)
    channel_table = []
    for ch in ["Social", "Paid", "Direct", "Organic", "Referral", "Email"]:
        d = overview_by_channel.get((ch,), None)
        if not d or d["sessions"] == 0:
            continue
        channel_table.append({
            "channel": ch,
            "color": CHANNEL_COLORS.get(ch, "#999"),
            "sessions": d["sessions"],
            "users": d["users"],
            "cr": d["cr"],
            "atc_rate": d["atc_rate"],
            "bounce_rate": d["bounce_rate"],
            "er": d["er"],
            "median_sec": d["median_eng_sec"],
            "revenue": round(d["revenue"], 2),
            "new_users": d["new_users"],
            "returning_users": d["returning_users"],
        })

    # KPIs by country (current period, all devices, top 10)
    overview_by_country = aggregate(filtered, ["country"], lambda r: r.period == cur_period_label)
    country_table = sorted(
        [
            {
                "country": k[0],
                "flag": flag(k[0]),
                "sessions": d["sessions"],
                "users": d["users"],
                "cr": d["cr"],
                "atc_rate": d["atc_rate"],
                "bounce_rate": d["bounce_rate"],
                "er": d["er"],
                "median_sec": d["median_eng_sec"],
                "revenue": round(d["revenue"], 2),
                "new_users": d["new_users"],
                "returning_users": d["returning_users"],
            }
            for k, d in overview_by_country.items() if d["sessions"] >= 5
        ],
        key=lambda x: -x["sessions"]
    )[:15]

    # New vs Returning by channel (current period)
    new_ret_by_channel = []
    for ch_row in channel_table:
        total = ch_row["new_users"] + ch_row["returning_users"]
        new_ret_by_channel.append({
            "channel": ch_row["channel"],
            "color": ch_row["color"],
            "new_pct": round(ch_row["new_users"] / total * 100, 1) if total > 0 else 0,
            "ret_pct": round(ch_row["returning_users"] / total * 100, 1) if total > 0 else 0,
            "new": ch_row["new_users"],
            "returning": ch_row["returning_users"],
        })

    # ---- Stacked bar data for interactive conversion chart ----
    def build_stacked_conversion(group_key, top_n=None, filter_fn=None):
        by_pg = aggregate(filtered, ["period", group_key], filter_fn)
        # Total ATC across all periods per segment
        totals = defaultdict(int)
        for (p, seg), d in by_pg.items():
            totals[seg] += d["funnel_atc"]
        if top_n:
            top_segs = [s for s, _ in sorted(totals.items(), key=lambda x: -x[1])[:top_n]]
        else:
            top_segs = [s for s, _ in sorted(totals.items(), key=lambda x: -x[1]) if s not in ("Email", "Other", "Spam")]
        has_other = False
        data = {}
        for p in periods:
            data[p] = {}
            other_atc, other_purchase = 0, 0
            for (pp, seg), d in by_pg.items():
                if pp != p:
                    continue
                if seg in top_segs:
                    data[p][seg] = {"atc": d["funnel_atc"], "purchase": d["funnel_purchase"]}
                else:
                    other_atc += d["funnel_atc"]
                    other_purchase += d["funnel_purchase"]
            if other_atc > 0 or other_purchase > 0:
                data[p]["Other"] = {"atc": other_atc, "purchase": other_purchase}
                has_other = True
        segments = top_segs + (["Other"] if has_other else [])
        return {"segments": segments, "data": data}

    stacked_channel = build_stacked_conversion("channel")
    stacked_country = build_stacked_conversion("country", top_n=5)
    stacked_source = build_stacked_conversion("source", top_n=5)

    # New vs Returning — use new_users/returning_users from overview_total as proxy
    # Note: we can't split funnel_atc by new/ret from aggregated data, so show session counts
    # To get accurate funnel by new/ret, we need a different approach in the query.
    # For now, show new_users vs returning_users counts (sessions, not funnel events).
    # Actually, let's approximate: the ratio of new/ret in funnel_atc is likely similar to sessions.
    newret_data = {}
    for p in periods:
        d = overview_total.get((p,), {})
        total_s = d.get("sessions", 0) or 1
        new_ratio = d.get("new_users", 0) / total_s
        ret_ratio = d.get("returning_users", 0) / total_s
        atc = d.get("funnel_atc", 0)
        purchase = d.get("funnel_purchase", 0)
        newret_data[p] = {
            "New": {"atc": round(atc * new_ratio), "purchase": round(purchase * new_ratio)},
            "Returning": {"atc": round(atc * ret_ratio), "purchase": round(purchase * ret_ratio)},
        }
    stacked_newret = {"segments": ["New", "Returning"], "data": newret_data}

    # ---- DEVICE-SPECIFIC overview data (mobile + desktop) ----
    device_overview = {}
    for dev in ["mobile", "desktop"]:
        dev_total = aggregate(filtered, ["period"], lambda r, d=dev: r.device == d)
        dev_trend = []
        for p in periods:
            d = dev_total.get((p,), {})
            dev_trend.append({
                "period": p,
                "sessions": d.get("sessions", 0),
                "cr": d.get("cr", 0),
                "atc_rate": d.get("atc_rate", 0),
                "cart_to_purchase": d.get("cart_to_purchase", 0),
                "revenue_per_session": d.get("revenue_per_session", 0),
                "bounce_rate": d.get("bounce_rate", 0),
                "revenue": round(d.get("revenue", 0), 2),
                "funnel_atc": d.get("funnel_atc", 0),
                "funnel_purchase": d.get("funnel_purchase", 0),
            })

        # Current period KPIs + deltas
        dev_cur = dev_trend[-1].copy() if dev_trend else {}
        n_p = min(4, len(dev_trend) - 1)
        if n_p > 0:
            prev = dev_trend[-(n_p + 1):-1]
            for m in ["sessions", "cr", "atc_rate", "bounce_rate", "revenue"]:
                avg_v = sum(x.get(m, 0) for x in prev) / len(prev)
                cur_v = dev_cur.get(m, 0)
                dev_cur[f"delta_{m}"] = round((cur_v - avg_v) / avg_v * 100, 1) if avg_v > 0 else None

        # Stacked conv per device
        dev_stacked = {
            "channel": build_stacked_conversion("channel", filter_fn=lambda r, d=dev: r.device == d),
            "country": build_stacked_conversion("country", top_n=5, filter_fn=lambda r, d=dev: r.device == d),
            "source": build_stacked_conversion("source", top_n=5, filter_fn=lambda r, d=dev: r.device == d),
        }

        # Bounce by channel per device (with session counts)
        dev_bounce_data = aggregate(filtered, ["period", "channel"], lambda r, d=dev: r.device == d)
        dev_bounce = {}
        for ch in ["Social", "Paid", "Direct", "Organic", "Referral"]:
            dev_bounce[ch] = {
                "bounce": [dev_bounce_data.get((p, ch), {}).get("bounce_rate", 0) for p in periods],
                "sessions": [dev_bounce_data.get((p, ch), {}).get("sessions", 0) for p in periods],
            }

        device_overview[dev] = {
            "trend": dev_trend,
            "cur_kpis": dev_cur,
            "stacked_conv": dev_stacked,
            "bounce_trend": dev_bounce,
        }

    # Bounce rate by channel over time (with session counts for line thickness)
    bounce_by_channel_period = aggregate(filtered, ["period", "channel"])
    bounce_trend = {}
    for ch in ["Social", "Paid", "Direct", "Organic", "Referral"]:
        bounce_trend[ch] = {
            "bounce": [bounce_by_channel_period.get((p, ch), {}).get("bounce_rate", 0) for p in periods],
            "sessions": [bounce_by_channel_period.get((p, ch), {}).get("sessions", 0) for p in periods],
        }

    # =========================================================
    # ==========   SUMMARY TAB DATA   =========================
    # =========================================================
    n_prev = get_comparison_periods(grain)

    # Per-period totals
    period_totals = aggregate(filtered, ["period"])

    def trend_of(metric):
        return [period_totals.get((p,), {}).get(metric, 0) for p in periods]

    def last_value(metric):
        return period_totals.get((periods[-1],), {}).get(metric, 0) if periods else 0

    # KPI block
    sum_kpi = {
        "revenue_per_session": {
            "value": last_value("revenue_per_session"),
            "delta": compute_delta_vs_prev(trend_of("revenue_per_session"), n_prev),
            "trend": trend_of("revenue_per_session"),
            "agg": "mean",
        },
        "revenue": {
            "value": round(last_value("revenue"), 2),
            "delta": compute_delta_vs_prev(trend_of("revenue"), n_prev),
            "trend": [round(v, 2) for v in trend_of("revenue")],
            "agg": "sum",
        },
        "atc_rate": {
            "value": last_value("atc_rate"),
            "delta": compute_delta_pp(trend_of("atc_rate"), n_prev),
            "trend": trend_of("atc_rate"),
            "agg": "rate",
        },
        "purchase_rate": {
            "value": last_value("cr"),
            "delta": compute_delta_pp(trend_of("cr"), n_prev),
            "trend": trend_of("cr"),
            "agg": "rate",
        },
        "cart_to_purchase": {
            "value": last_value("cart_to_purchase"),
            "delta": compute_delta_pp(trend_of("cart_to_purchase"), n_prev),
            "trend": trend_of("cart_to_purchase"),
            "agg": "rate",
        },
    }

    # Visitors & sessions per period
    # NOTE: aggregate sums `users` across breakdowns which double-counts.
    # For accurate unique visitors we need a separate query per period. Approximating for now.
    sum_visitors_sessions = {
        "labels": periods,
        "visitors": [period_totals.get((p,), {}).get("users", 0) for p in periods],
        "sessions": [period_totals.get((p,), {}).get("sessions", 0) for p in periods],
    }

    # Sessions by device type (mobile/desktop/tablet) per period
    dev_by_period = aggregate(filtered, ["period", "device"])
    all_devices = sorted(set(k[1] for k in dev_by_period.keys()))
    sum_device_sessions = {"labels": periods}
    for dev in ["mobile", "desktop", "tablet"]:
        sum_device_sessions[dev] = [dev_by_period.get((p, dev), {}).get("sessions", 0) for p in periods]

    # New vs Returning per period
    sum_new_returning = {
        "labels": periods,
        "new": [period_totals.get((p,), {}).get("new_users", 0) for p in periods],
        "returning": [period_totals.get((p,), {}).get("returning_users", 0) for p in periods],
    }

    # Time on site per device (median) per period
    sum_time_on_site = {"labels": periods}
    for dev in ["mobile", "desktop", "tablet"]:
        sum_time_on_site[dev] = [dev_by_period.get((p, dev), {}).get("median_eng_sec", 0) for p in periods]

    # Bounce rate per device per period
    sum_bounce_device = {"labels": periods}
    for dev in ["mobile", "desktop", "tablet"]:
        sum_bounce_device[dev] = [dev_by_period.get((p, dev), {}).get("bounce_rate", 0) for p in periods]

    # Traffic source trend (sessions + share)
    ch_by_period = aggregate(filtered, ["period", "channel"])
    sum_source_trend = {"labels": periods, "sources": []}
    tracked_channels = ["Social", "Paid", "Direct", "Organic", "Referral"]
    for ch in tracked_channels:
        sessions_per_p = [ch_by_period.get((p, ch), {}).get("sessions", 0) for p in periods]
        totals_per_p = [period_totals.get((p,), {}).get("sessions", 0) for p in periods]
        share_per_p = [round(s / t * 100, 1) if t > 0 else 0 for s, t in zip(sessions_per_p, totals_per_p)]
        sum_source_trend["sources"].append({
            "name": ch,
            "sessions": sessions_per_p,
            "share_pct": share_per_p,
        })

    # Helper: build a table row with delta for each metric
    def build_row_with_deltas(by_period_key, key_label, metrics_spec):
        """metrics_spec: list of (metric_name, delta_type) where delta_type in 'rel','pp','none'"""
        results = []
        # Collect all unique keys
        all_keys = set(k[1] for k in by_period_key.keys())
        for key in all_keys:
            trends = {}
            for metric, _ in metrics_spec:
                trends[metric] = [by_period_key.get((p, key), {}).get(metric, 0) for p in periods]
            if sum(trends[metrics_spec[0][0]]) == 0:  # skip empty rows
                continue
            row = {"name": key}
            for metric, delta_type in metrics_spec:
                cur = trends[metric][-1] if trends[metric] else 0
                if delta_type == "pp":
                    delta = compute_delta_pp(trends[metric], n_prev)
                elif delta_type == "rel":
                    delta = compute_delta_vs_prev(trends[metric], n_prev)
                else:
                    delta = None
                row[metric] = {"value": cur, "delta": delta, "delta_type": delta_type}
            results.append(row)
        return results

    # Source table
    source_metrics = [
        ("sessions", "rel"), ("users", "rel"),
        ("new_users", "rel"), ("returning_users", "rel"),
        ("er", "pp"), ("bounce_rate", "pp"),
        ("median_eng_sec", "rel"), ("avg_pages", "rel"),
        ("atc_rate", "pp"), ("cr", "pp"),
    ]
    sum_source_table = build_row_with_deltas(ch_by_period, "channel", source_metrics)
    sum_source_table = sorted(sum_source_table, key=lambda r: -r["sessions"]["value"])

    # Country table
    country_by_period = aggregate(filtered, ["period", "country"])
    sum_country_table = build_row_with_deltas(country_by_period, "country", source_metrics)
    sum_country_table = [r for r in sum_country_table if r["sessions"]["value"] >= 5]
    sum_country_table = sorted(sum_country_table, key=lambda r: -r["sessions"]["value"])[:20]

    # ATC + PR dual-axis trend (all devices)
    sum_atc_pr_trend = {
        "labels": periods,
        "atc_rate": trend_of("atc_rate"),
        "purchase_rate": trend_of("cr"),
    }

    # Rankings: Source × Country × New/Returning combinations
    # We need per-period data for the combination, take last period's values
    def build_ranking(sort_metric, top_n=10, min_sessions=10):
        # Aggregate by combination for the last period only
        cur_p = periods[-1] if periods else None
        combo_agg = aggregate(filtered, ["source", "country"], lambda r: r.period == cur_p)
        rankings = []
        for (src, country), d in combo_agg.items():
            if d["sessions"] < min_sessions:
                continue
            # Approximate new/ret ratio for this combo
            new_share = d["new_users"] / d["sessions"] if d["sessions"] > 0 else 0
            user_type = "New" if new_share > 0.6 else ("Returning" if new_share < 0.4 else "Mixed")
            rankings.append({
                "source": src,
                "country": country,
                "user_type": user_type,
                "sessions": d["sessions"],
                "atc_rate": d["atc_rate"],
                "purchase_rate": d["cr"],
                "metric_value": d[sort_metric],
            })
        return sorted(rankings, key=lambda x: -x["metric_value"])[:top_n]

    sum_ranking_atc = build_ranking("atc_rate")
    sum_ranking_pr = build_ranking("cr")

    # ---- Cards-per-session breakdown by country / source (mobile, last period) ----
    cur_period_label = periods[-1] if periods else ""
    n_prev_breakdown = get_comparison_periods(grain)
    prev_periods_set = periods[max(0, len(periods) - 1 - n_prev_breakdown):len(periods) - 1]

    def build_cards_breakdown(group_key, min_sessions=10):
        """For mobile, last period: aggregate cards/session by country or source. Compute delta vs avg(prev N periods)."""
        cur_agg = aggregate(filtered, [group_key],
                            lambda r: r.device == "mobile" and r.period == cur_period_label)
        prev_agg = aggregate(filtered, [group_key, "period"],
                             lambda r: r.device == "mobile" and r.period in prev_periods_set)
        rows = []
        for (key,), data in cur_agg.items():
            if data["sessions"] < min_sessions:
                continue
            prev_med_vals = [prev_agg.get((key, p), {}).get("median_product_views", 0) for p in prev_periods_set]
            prev_med_vals = [v for v in prev_med_vals if v > 0]
            avg_prev_med = sum(prev_med_vals) / len(prev_med_vals) if prev_med_vals else 0
            cur_med = data.get("median_product_views", 0)
            delta_med = round(cur_med - avg_prev_med, 1) if avg_prev_med > 0 else None

            prev_mean_vals = [prev_agg.get((key, p), {}).get("avg_product_views", 0) for p in prev_periods_set]
            prev_mean_vals = [v for v in prev_mean_vals if v > 0]
            avg_prev_mean = sum(prev_mean_vals) / len(prev_mean_vals) if prev_mean_vals else 0
            cur_mean = data.get("avg_product_views", 0)
            delta_mean = round(cur_mean - avg_prev_mean, 1) if avg_prev_mean > 0 else None

            rows.append({
                "name": key,
                "sessions": data["sessions"],
                "median_products": cur_med,
                "mean_products": cur_mean,
                "delta_median": delta_med,
                "delta_mean": delta_mean,
            })
        return sorted(rows, key=lambda x: -x["sessions"])[:15]

    cards_by_country = build_cards_breakdown("country")
    cards_by_source = build_cards_breakdown("source")

    # ---- Per-card time breakdown by country / source (last period) ----
    pct_data = (analytics_data or {}).get("per_card_time", [])
    pct_filtered = [r for r in pct_data if r.get("country") not in excluded_countries]

    def build_per_card_breakdown(group_key, min_views=10):
        """Aggregate per-card time by country or source for the last period; delta vs avg of prev periods."""
        from collections import defaultdict
        cur_buckets = defaultdict(lambda: {"card_views": 0, "_med_vals": [], "_mean_sum_w": 0.0})
        for r in pct_filtered:
            if r.get("period") != cur_period_label:
                continue
            key = r.get(group_key)
            if not key:
                continue
            b = cur_buckets[key]
            b["card_views"] += r.get("card_views", 0)
            if r.get("median_sec") is not None and r.get("card_views"):
                b["_med_vals"].extend([r["median_sec"]] * r["card_views"])
            if r.get("mean_sec") is not None:
                b["_mean_sum_w"] += r["mean_sec"] * r.get("card_views", 0)

        prev_buckets = defaultdict(lambda: {"_med_vals": [], "_mean_sum_w": 0.0, "card_views": 0})
        for r in pct_filtered:
            if r.get("period") not in prev_periods_set:
                continue
            key = r.get(group_key)
            if not key:
                continue
            v = r.get("card_views", 0)
            prev_buckets[key]["card_views"] += v
            if r.get("median_sec") is not None and v:
                prev_buckets[key]["_med_vals"].extend([r["median_sec"]] * v)
            if r.get("mean_sec") is not None and v:
                prev_buckets[key]["_mean_sum_w"] += r["mean_sec"] * v

        rows = []
        for key, b in cur_buckets.items():
            if b["card_views"] < min_views:
                continue
            cur_med = round(sorted(b["_med_vals"])[len(b["_med_vals"]) // 2], 1) if b["_med_vals"] else 0
            cur_mean = round(b["_mean_sum_w"] / b["card_views"], 1) if b["card_views"] else 0
            prev = prev_buckets.get(key, {"_med_vals": [], "_mean_sum_w": 0.0, "card_views": 0})
            prev_med = round(sorted(prev["_med_vals"])[len(prev["_med_vals"]) // 2], 1) if prev["_med_vals"] else 0
            prev_mean = round(prev["_mean_sum_w"] / prev["card_views"], 1) if prev["card_views"] else 0
            delta_med = round(cur_med - prev_med, 1) if prev_med > 0 else None
            delta_mean = round(cur_mean - prev_mean, 1) if prev_mean > 0 else None
            rows.append({
                "name": key,
                "card_views": b["card_views"],
                "median_sec": cur_med,
                "mean_sec": cur_mean,
                "delta_median": delta_med,
                "delta_mean": delta_mean,
            })
        return sorted(rows, key=lambda x: -x["card_views"])[:15]

    per_card_by_country = build_per_card_breakdown("country")
    per_card_by_source = build_per_card_breakdown("source")

    # ---- Per-card time chart series (aggregated across channels, by period only) ----
    from collections import defaultdict as _dd
    pct_by_period = _dd(lambda: {"card_views": 0, "_med": [], "_mean_w": 0.0})
    for r in pct_filtered:
        p = r.get("period")
        if not p:
            continue
        bucket = pct_by_period[p]
        bucket["card_views"] += r.get("card_views", 0)
        if r.get("median_sec") is not None and r.get("card_views"):
            bucket["_med"].extend([r["median_sec"]] * r["card_views"])
        if r.get("mean_sec") is not None:
            bucket["_mean_w"] += r["mean_sec"] * r.get("card_views", 0)
    per_card_chart = []
    for p, b in pct_by_period.items():
        if b["card_views"] == 0:
            continue
        med = round(sorted(b["_med"])[len(b["_med"]) // 2], 1) if b["_med"] else 0
        mean = round(b["_mean_w"] / b["card_views"], 1) if b["card_views"] else 0
        per_card_chart.append({
            "period": p,
            "card_views": b["card_views"], "median_sec": med, "mean_sec": mean,
        })

    # ---- Top-20 product cards ----
    top_products_rows = (analytics_data or {}).get("top_products", [])
    top_products_cur = [r for r in top_products_rows if r.get("period") == cur_period_label]
    # Aggregated (last 4 periods)
    last_4_set = set(periods[-(n_prev_breakdown + 1):])  # current + 4 previous
    from collections import defaultdict as _dd2
    agg_4w = _dd2(lambda: {"item_name": None, "views": 0, "atc": 0, "purchases": 0,
                            "_med_w": [], "_mean_sum_w": 0.0, "_view_total": 0})
    for r in top_products_rows:
        if r.get("period") not in last_4_set:
            continue
        item_id = r.get("item_id")
        if not item_id:
            continue
        b = agg_4w[item_id]
        b["item_name"] = r.get("item_name") or b["item_name"]
        b["views"] += r.get("views", 0)
        b["atc"] += r.get("atc", 0)
        b["purchases"] += r.get("purchases", 0)
        v = r.get("views", 0)
        if r.get("median_sec") is not None and v > 0:
            b["_med_w"].extend([r["median_sec"]] * v)
        if r.get("mean_sec") is not None and v > 0:
            b["_mean_sum_w"] += r["mean_sec"] * v
            b["_view_total"] += v

    def _row(item_id, b):
        med = round(sorted(b["_med_w"])[len(b["_med_w"]) // 2], 1) if b["_med_w"] else 0
        mean = round(b["_mean_sum_w"] / b["_view_total"], 1) if b["_view_total"] else 0
        atc = b["atc"]; purchases = b["purchases"]; views = b["views"]
        cr_atc = round(atc / views * 100, 1) if views else 0
        return {
            "item_id": item_id,
            "item_name": b["item_name"] or item_id,
            "views": views,
            "median_sec": med,
            "mean_sec": mean,
            "atc": atc,
            "purchases": purchases,
            "cr_atc": cr_atc,
        }

    top_products_4w = sorted(
        [_row(iid, b) for iid, b in agg_4w.items() if b["views"] > 0],
        key=lambda x: -x["views"]
    )[:30]

    top_products_week = sorted(
        [{
            "item_id": r.get("item_id"),
            "item_name": r.get("item_name") or r.get("item_id"),
            "views": r.get("views", 0),
            "median_sec": r.get("median_sec") or 0,
            "mean_sec": r.get("mean_sec") or 0,
            "atc": r.get("atc", 0),
            "purchases": r.get("purchases", 0),
            "cr_atc": round(r.get("atc", 0) / r["views"] * 100, 1) if r.get("views") else 0,
        } for r in top_products_cur if r.get("views", 0) > 0],
        key=lambda x: -x["views"]
    )[:30]

    summary_data = {
        "n_prev": n_prev,
        "kpi": sum_kpi,
        "visitors_sessions": sum_visitors_sessions,
        "device_sessions": sum_device_sessions,
        "new_returning": sum_new_returning,
        "time_on_site": sum_time_on_site,
        "bounce_device": sum_bounce_device,
        "source_trend": sum_source_trend,
        "source_table": sum_source_table,
        "country_table": sum_country_table,
        "atc_pr_trend": sum_atc_pr_trend,
        "ranking_atc": sum_ranking_atc,
        "ranking_pr": sum_ranking_pr,
    }

    # ---- Build JSON payload for HTML ----
    payload = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "grain": grain,
        "periods": periods,
        "excluded_countries": excluded_countries,
        "all_countries": all_countries_in_data,
        "mobile_funnel": mobile_funnel,
        "desktop_funnel": desktop_funnel,
        "mobile_funnel_pct": mobile_funnel_pct,
        "desktop_funnel_pct": desktop_funnel_pct,
        "channel_cards": channel_cards,
        "source_cards": source_cards,
        "bubble_channel": bubble_channel,
        "channel_trend": channel_trend,
        "stage_tables": stage_tables,
        "bottom_funnel": bottom_funnel,
        "overview_kpis_trend": overview_kpis_trend,
        "cur_kpis": cur_kpis,
        "channel_table": channel_table,
        "country_table": country_table,
        "new_ret_by_channel": new_ret_by_channel,
        "bounce_trend": bounce_trend,
        "stacked_conv": {
            "channel": stacked_channel,
            "country": stacked_country,
            "source": stacked_source,
            "newret": stacked_newret,
        },
        "device_overview": device_overview,
        "analytics": analytics_data or {},
        "summary": summary_data,
        "cards_breakdown": {
            "by_country": cards_by_country,
            "by_source": cards_by_source,
            "period": cur_period_label,
        },
        "per_card_breakdown": {
            "by_country": per_card_by_country,
            "by_source": per_card_by_source,
            "period": cur_period_label,
        },
        "per_card_chart": per_card_chart,
        "top_products": {
            "week": top_products_week,
            "agg_4w": top_products_4w,
            "period": cur_period_label,
            "n_prev": n_prev_breakdown,
        },
    }

    html = build_html(payload)
    return html


def delta_html(value, suffix="%", invert=False):
    """Format a delta value with arrow and color."""
    if value is None:
        return '<span class="delta neutral">—</span>'
    if value > 0:
        color = "red" if invert else "green"
        return f'<span class="delta {color}">↑ +{value}{suffix}</span>'
    elif value < 0:
        color = "green" if invert else "red"
        return f'<span class="delta {color}">↓ {value}{suffix}</span>'
    else:
        return f'<span class="delta neutral">→ 0{suffix}</span>'


def render_card_html(card, name_key):
    """Render a single card HTML block for channel or source cards.

    name_key: 'channel' for channel cards, 'source' for source cards.
    Channel cards get a colored border-top; source cards do not.
    Canvas id prefix is 'funnel-channel-' or 'funnel-source-'.
    """
    name = card[name_key]
    if name_key == "channel":
        border_style = f' style="border-top: 4px solid {card["color"]}"'
        canvas_id = f"funnel-channel-{name.lower().replace(' ', '-')}"
    else:
        border_style = ""
        canvas_id = f"funnel-source-{name.replace('.', '_').replace('(', '').replace(')', '').replace(' ', '-')}"

    top_countries_html = "".join(
        f'<div class="country-row"><span>{flag(c)}</span><span>{s}</span></div>'
        for c, s in card["top_countries"]
    )

    low_n_badge = '<span style="font-size:10px; color:#E17055; margin-left:6px; padding:2px 6px; background:#FFEAE0; border-radius:3px;">&#9888; low n</span>' if card.get("sessions", 0) < 50 else ""

    return f"""
        <div class="cell"{border_style}>
            <h3>{name}{low_n_badge}</h3>
            <canvas id="{canvas_id}"></canvas>
            <div class="metrics">
                <div class="metric">
                    <span class="label">Сессии</span>
                    <span class="value">{card['sessions']}</span>
                    {delta_html(card['delta_sessions'])}
                </div>
                <div class="metric">
                    <span class="label">Доля</span>
                    <span class="value">{card['share']}%</span>
                </div>
                <div class="metric">
                    <span class="label">ER</span>
                    <span class="value">{card['er']}%</span>
                    {delta_html(card['delta_er'], suffix=' п.п.')}
                </div>
                <div class="metric">
                    <span class="label">Median sec</span>
                    <span class="value">{card['median_sec']}s</span>
                    {delta_html(card['delta_median'], suffix='s')}
                </div>
                <div class="metric">
                    <span class="label">Глубина 2+</span>
                    <span class="value">{card['deep_pct']}%</span>
                    {delta_html(card['delta_deep'], suffix=' п.п.')}
                </div>
                <div class="metric">
                    <span class="label">Карточек med / mean</span>
                    <span class="value">{card.get('median_products', 0)} / {card['avg_products']}</span>
                    {delta_html(card.get('delta_products'), suffix='')}
                </div>
            </div>
            <div class="top-countries">
                <h4>Топ 5 стран</h4>
                {top_countries_html}
            </div>
        </div>
        """


def build_html(data):
    """Build the full HTML string."""
    cards_html = "".join(render_card_html(card, "channel") for card in data["channel_cards"])
    source_cards_html = "".join(render_card_html(card, "source") for card in data["source_cards"])

    # Header country filter — checkboxes for excluded (unchecked) and remaining (checked)
    _excluded_set = set(data.get("excluded_countries", []))
    _all_countries = data.get("all_countries", [])
    _excluded_in_data = [c for c in _all_countries if c in _excluded_set]
    _included_in_data = [c for c in _all_countries if c not in _excluded_set]
    country_excluded_html = "".join(
        f'<label><input type="checkbox" data-country="{c}"> {flag(c)}</label>'
        for c in _excluded_in_data
    )
    country_included_html = "".join(
        f'<label><input type="checkbox" data-country="{c}" checked> {flag(c)}</label>'
        for c in _included_in_data
    )
    country_total = len(_excluded_in_data) + len(_included_in_data)
    country_checked_initial = len(_included_in_data)

    bottom_funnel_html = "".join(
        f'<tr><td>{r["source"]}</td><td>{flag(r["country"])}</td><td>{r["sessions"]}</td>'
        f'<td>{r["catalog"]}</td><td>{r["product"]}</td>'
        f'<td class="highlight">{r["atc"]}</td><td class="highlight">{r["checkout"]}</td>'
        f'<td class="highlight">{r["purchase"]}</td></tr>'
        for r in data.get("bottom_funnel", [])
    )

    def _stage_delta_cell(v):
        if v is None:
            return '<td><span class="delta neutral">—</span></td>'
        if v > 0:
            return f'<td><span class="delta green">↑ +{v} п.п.</span></td>'
        if v < 0:
            return f'<td><span class="delta red">↓ {v} п.п.</span></td>'
        return '<td><span class="delta neutral">→ 0 п.п.</span></td>'

    def _render_stage_table(rows, input_label):
        if not rows:
            return f'<table class="data-table"><thead><tr><th>Страна</th><th>Канал</th><th>{input_label}</th><th>Конверсия</th><th>Δ vs ср. 4 пред.</th></tr></thead><tbody><tr><td colspan="5" style="text-align:center; color:#888">Нет данных</td></tr></tbody></table>'
        body = "".join(
            f'<tr><td>{flag(r["country"])} {r["country"]}</td>'
            f'<td><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{r["channel_color"]}; margin-right:6px; vertical-align:middle;"></span>{r["channel"]}</td>'
            f'<td>{r["input"]}</td><td>{r["conv"]}%</td>'
            f'{_stage_delta_cell(r["delta"])}</tr>'
            for r in rows
        )
        return (
            f'<table class="data-table">'
            f'<thead><tr><th>Страна</th><th>Канал</th><th>{input_label}</th>'
            f'<th>Конверсия</th><th>Δ vs ср. 4 пред.</th></tr></thead>'
            f'<tbody>{body}</tbody></table>'
        )

    stage_tables_data = data.get("stage_tables", {})
    stage_table_prod_html     = _render_stage_table(stage_tables_data.get("prod", []),     "Сессии в каталоге")
    stage_table_atc_html      = _render_stage_table(stage_tables_data.get("atc", []),      "Сессии на товаре")
    stage_table_checkout_html = _render_stage_table(stage_tables_data.get("checkout", []), "Сессии с корзиной")
    stage_table_purchase_html = _render_stage_table(stage_tables_data.get("purchase", []), "Сессии с чекаутом")

    def _delta_cell(v, suffix=""):
        if v is None:
            return '<td><span class="delta neutral">—</span></td>'
        if v > 0:
            return f'<td><span class="delta green">↑ +{v}{suffix}</span></td>'
        if v < 0:
            return f'<td><span class="delta red">↓ {v}{suffix}</span></td>'
        return f'<td><span class="delta neutral">→ 0{suffix}</span></td>'

    cards_breakdown = data.get("cards_breakdown", {"by_country": [], "by_source": []})
    cards_country_rows = "".join(
        f'<tr><td>{flag(r["name"])} {r["name"]}</td><td>{r["sessions"]}</td>'
        f'<td>{r["median_products"]}</td>{_delta_cell(r.get("delta_median"))}'
        f'<td>{r["mean_products"]}</td>{_delta_cell(r.get("delta_mean"))}</tr>'
        for r in cards_breakdown.get("by_country", [])
    ) or '<tr><td colspan="6" style="text-align:center; color:#888">Нет данных</td></tr>'
    cards_source_rows = "".join(
        f'<tr><td>{r["name"]}</td><td>{r["sessions"]}</td>'
        f'<td>{r["median_products"]}</td>{_delta_cell(r.get("delta_median"))}'
        f'<td>{r["mean_products"]}</td>{_delta_cell(r.get("delta_mean"))}</tr>'
        for r in cards_breakdown.get("by_source", [])
    ) or '<tr><td colspan="6" style="text-align:center; color:#888">Нет данных</td></tr>'

    pct_breakdown = data.get("per_card_breakdown", {"by_country": [], "by_source": []})
    per_card_country_rows = "".join(
        f'<tr><td>{flag(r["name"])} {r["name"]}</td><td>{r["card_views"]}</td>'
        f'<td>{r["median_sec"]}s</td>{_delta_cell(r.get("delta_median"), "s")}'
        f'<td>{r["mean_sec"]}s</td>{_delta_cell(r.get("delta_mean"), "s")}</tr>'
        for r in pct_breakdown.get("by_country", [])
    ) or '<tr><td colspan="6" style="text-align:center; color:#888">Нет данных</td></tr>'
    per_card_source_rows = "".join(
        f'<tr><td>{r["name"]}</td><td>{r["card_views"]}</td>'
        f'<td>{r["median_sec"]}s</td>{_delta_cell(r.get("delta_median"), "s")}'
        f'<td>{r["mean_sec"]}s</td>{_delta_cell(r.get("delta_mean"), "s")}</tr>'
        for r in pct_breakdown.get("by_source", [])
    ) or '<tr><td colspan="6" style="text-align:center; color:#888">Нет данных</td></tr>'

    # Build overview KPI HTML
    benchmarks = {
        "cr": "1.2–1.8%",
        "atc_rate": "7.5%",
        "cart_to_purchase": "25–30%",
        "revenue_per_session": "$1.5–3.0",
    }

    cur = data.get("cur_kpis", {})
    total_users = cur.get("new_users", 0) + cur.get("returning_users", 0)
    new_pct = round(cur.get("new_users", 0) / total_users * 100, 1) if total_users > 0 else 0
    ret_pct = round(cur.get("returning_users", 0) / total_users * 100, 1) if total_users > 0 else 0

    def kpi_cell(label, value, delta, bench="", canvas_id=""):
        spark = f'<div class="kpi-spark"><canvas id="{canvas_id}"></canvas></div>' if canvas_id else ''
        return f"""<div class="cell h2x2 cell-kpi">
            <div class="kpi-label">{label}</div>
            <div class="kpi-meta"><div class="kpi-value">{value}</div> {delta}</div>
            <div class="kpi-bench">{bench}</div>
            {spark}
        </div>"""

    kpi_cards_html = f"""
    <div class="grid">
        {kpi_cell("Purchase Rate", f"{cur.get('cr', 0)}%", delta_html(cur.get('delta_cr')), f"bench: {benchmarks['cr']}", "spark-cr")}
        {kpi_cell("ATC Rate", f"{cur.get('atc_rate', 0)}%", delta_html(cur.get('delta_atc_rate')), f"bench: {benchmarks['atc_rate']}", "spark-atc")}
        {kpi_cell("Cart → Purchase", f"{cur.get('cart_to_purchase', 0)}%", delta_html(cur.get('delta_cart_to_purchase')), f"bench: {benchmarks['cart_to_purchase']}", "spark-cart")}
        {kpi_cell("Revenue / Session", f"${cur.get('revenue_per_session', 0)}", delta_html(cur.get('delta_revenue_per_session')), f"bench: {benchmarks['revenue_per_session']}", "spark-rps")}
        {kpi_cell("Сессии", f"{cur.get('sessions', 0)}", delta_html(cur.get('delta_sessions')), "vs avg 4 пред.", "spark-sessions")}
        {kpi_cell("Выручка", f"${cur.get('revenue', 0)}", delta_html(cur.get('delta_revenue')), "vs avg 4 пред.", "spark-revenue")}
        <div class="cell h2x2 cell-kpi">
            <div class="kpi-label">New vs Returning</div>
            <div style="margin-top:8px;">
                <div class="nr-bar"><div class="nr-new" style="width:{new_pct}%"></div></div>
                <div style="font-size:12px; margin-top:6px;">
                    <span style="color:#0984E3;">New {cur.get('new_users', 0)} ({new_pct}%)</span>
                    <span style="color:#6C5CE7;">Ret {cur.get('returning_users', 0)} ({ret_pct}%)</span>
                    {delta_html(cur.get('delta_new_pct'), suffix=' п.п.')}
                </div>
            </div>
        </div>
        {kpi_cell("Bounce Rate", f"{cur.get('bounce_rate', 0)}%", delta_html(cur.get('delta_bounce_rate'), invert=True), "vs avg 4 пред.", "spark-bounce")}
    </div>
    """

    # Channel table HTML
    channel_table_html = ""
    for ch in data.get("channel_table", []):
        channel_table_html += f"""<tr>
            <td><span class="ch-dot" style="background:{ch['color']}"></span>{ch['channel']}</td>
            <td>{ch['sessions']}</td>
            <td>{ch['cr']}%</td>
            <td>{ch['atc_rate']}%</td>
            <td>{ch['bounce_rate']}%</td>
            <td>{ch['er']}%</td>
            <td>{ch['median_sec']}s</td>
            <td>${ch['revenue']}</td>
            <td>{ch['new_users']}</td>
            <td>{ch['returning_users']}</td>
        </tr>"""

    # Country table HTML
    country_table_html = ""
    for ct in data.get("country_table", []):
        country_table_html += f"""<tr>
            <td>{ct['flag']}</td>
            <td>{ct['sessions']}</td>
            <td>{ct['cr']}%</td>
            <td>{ct['atc_rate']}%</td>
            <td>{ct['bounce_rate']}%</td>
            <td>{ct['er']}%</td>
            <td>{ct['median_sec']}s</td>
            <td>${ct['revenue']}</td>
        </tr>"""

    # New vs Returning by channel HTML
    nr_channel_html = ""
    for nr in data.get("new_ret_by_channel", []):
        nr_channel_html += f"""<tr>
            <td><span class="ch-dot" style="background:{nr['color']}"></span>{nr['channel']}</td>
            <td>{nr['new']}</td>
            <td>{nr['returning']}</td>
            <td>{nr['new_pct']}%</td>
            <td>{nr['ret_pct']}%</td>
        </tr>"""

    css_vars = render_css_vars(TOKENS)
    chart_js_defaults = chart_defaults_js(TOKENS)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pinkspink Analytics</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu+Mono:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    <style>
        {css_vars}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: var(--ff-mono); background: var(--bg-page); color: var(--tx-primary); padding: 0; margin: 0; }}
        .main-container {{ max-width: 1400px; margin: 0 auto; padding: 0 var(--sp-5) var(--sp-5); }}
        h1 {{ font-size: var(--fs-h1); font-weight: var(--fw-bold); margin-bottom: var(--sp-2); }}
        h2 {{ font-size: var(--fs-h2); font-weight: var(--fw-semibold); margin: var(--sp-5) 0 var(--sp-3); padding-bottom: 6px; }}
        h3 {{ font-size: var(--fs-h3); font-weight: var(--fw-semibold); margin-bottom: var(--sp-2); }}
        h4 {{ font-size: var(--fs-h4); font-weight: var(--fw-semibold); margin: var(--sp-3) 0 6px; color: var(--tx-secondary); }}
        .meta {{ color: var(--tx-secondary); font-size: var(--fs-meta); margin-bottom: var(--sp-3); }}
        .agg-tag {{ display: inline-block; font-size: var(--fs-tag); color: var(--tx-muted); font-weight: var(--fw-regular); text-transform: lowercase; letter-spacing: var(--ls-label); margin-left: var(--sp-1); }}

        /* Sticky header */
        .sticky-header {{
            position: sticky; top: 0; z-index: 100;
            background: var(--sh-sticky); backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--bg-border);
            padding: 10px var(--sp-5);
            display: flex; justify-content: space-between; align-items: center;
            max-width: 1400px; margin: 0 auto; gap: var(--sp-4); flex-wrap: wrap;
            margin-bottom: var(--sp-4);
        }}
        .header-left {{ display: flex; align-items: center; gap: var(--sp-4); }}
        .brand {{ font-size: var(--fs-brand); font-weight: var(--fw-bold); color: var(--tx-primary); }}
        .header-meta {{ font-size: var(--fs-th); color: var(--tx-secondary); line-height: 1.3; }}
        .header-right {{ display: flex; align-items: center; gap: var(--sp-3); }}
        .grain-nav {{ display: flex; gap: 2px; }}
        .grain-sq {{
            width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
            font-size: var(--fs-meta); font-weight: var(--fw-bold); background: var(--bg-muted); color: var(--tx-secondary);
            text-decoration: none; border-radius: var(--r-md);
        }}
        .grain-sq:hover {{ background: var(--bg-border); }}
        .tab-nav {{ display: flex; gap: var(--sp-1); }}

        .filters {{ display: flex; gap: var(--sp-4); padding: var(--sp-3); background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); align-items: center; flex-wrap: wrap; margin-bottom: var(--sp-4); }}
        .filters label {{ font-size: var(--fs-body); color: var(--tx-secondary); }}
        .grain-btn {{ padding: var(--sp-1) var(--sp-3); border-radius: var(--r-md); text-decoration: none; font-size: var(--fs-body); color: var(--tx-secondary); background: var(--bg-muted); border: none; cursor: pointer; }}
        .grain-btn:hover {{ background: var(--bg-border); }}
        .grain-active {{ background: var(--bg-inverse) !important; color: var(--tx-ondark) !important; }}
        .tab-btn {{ padding: 6px 14px; border-radius: var(--r-md); font-size: var(--fs-meta); font-weight: var(--fw-semibold); border: 1px solid var(--bg-border); cursor: pointer; background: var(--bg-card); color: var(--tx-secondary); }}
        .tab-btn:hover {{ background: var(--bg-muted); }}
        .tab-active {{ background: var(--bg-inverse) !important; color: var(--tx-ondark) !important; border-color: var(--bg-inverse) !important; }}

        /* Global header filters (UI-only): device + country */
        .device-nav {{ display: flex; gap: 2px; }}
        .device-nav .grain-btn {{ cursor: pointer; }}
        .country-filter {{ position: relative; }}
        .country-panel {{
            position: absolute; right: 0; top: calc(100% + 4px);
            background: var(--bg-card); border: 1px solid var(--bg-border);
            border-radius: var(--r-md); padding: 8px; min-width: 240px;
            max-height: 360px; overflow-y: auto; z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            font-size: 12px;
        }}
        .country-panel[hidden] {{ display: none; }}
        .country-section {{ display: flex; flex-direction: column; gap: 2px; }}
        .country-section label {{ display: flex; align-items: center; gap: 6px; cursor: pointer; padding: 2px 0; }}
        .country-section-title {{ font-weight: 700; font-size: 11px; color: #636E72; margin: 4px 0 2px; text-transform: uppercase; }}
        .country-sep {{ border: none; border-top: 1px solid var(--bg-border); margin: 6px 0; }}
        .filters-note {{ font-size: 10px; color: #999; align-self: center; max-width: 140px; line-height: 1.2; }}
        /* === 12-column × fixed-row Grid System ===
           Row height = 80px. Elements specify cols (span X) + rows (span Y).
           Naming convention: hNxM = N rows tall × M cols wide.
           Blocks with a title row use the size that includes the title (e.g. 5×8 = 4 data rows + 1 title row).
        */
        .grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            grid-auto-rows: 80px;
            gap: var(--sp-4);
            margin-bottom: var(--sp-5);
        }}
        .cell {{
            background: var(--bg-card); border-radius: var(--r-xl); padding: 14px;
            box-shadow: var(--sh-card); overflow: hidden;
            display: flex; flex-direction: column;
            height: 100%;
        }}

        /* Block containers: grid-column + grid-row spans.
           "h4x12" = 4 data rows + 1 title row = 5 grid rows */
        .h4x12, .h4x8, .h4x6, .h4x4 {{
            grid-row: span 5;
            display: grid;
            grid-template-rows: 80px 1fr;
            gap: var(--sp-2);
        }}
        .h4x12 {{ grid-column: span 12; }}
        .h4x8  {{ grid-column: span 8; }}
        .h4x6  {{ grid-column: span 6; }}
        .h4x4  {{ grid-column: span 4; }}

        /* KPI card sizes */
        .h2x2 {{ grid-column: span 2; grid-row: span 2; }}
        .h1x4 {{ grid-column: span 4; grid-row: span 1; }}
        .h1x2 {{ grid-column: span 2; grid-row: span 1; }}

        /* Title area inside block — 1 row tall, bottom-aligned */
        .title-area {{
            display: flex; flex-direction: column; justify-content: flex-end;
            padding-bottom: var(--sp-1);
            grid-row: 1;
        }}
        .title-area h3 {{ font-size: var(--fs-h4); font-weight: var(--fw-bold); margin: 0 0 2px 0; }}
        .title-area .meta {{ margin: 0; font-size: var(--fs-th); color: var(--tx-secondary); line-height: 1.3; }}

        .h4x12 > .cell, .h4x8 > .cell, .h4x6 > .cell, .h4x4 > .cell {{
            grid-row: 2;
        }}

        /* Chart-wrap: fixed-size container that breaks Chart.js feedback loop */
        .chart-wrap {{ position: relative; width: 100%; height: 100%; flex: 1; }}
        .chart-wrap > canvas {{ position: absolute; top: 0; left: 0; width: 100% !important; height: 100% !important; }}

        /* When a cell.h4x* contains ONLY a chart-wrap (no <h3> title), make the chart span all rows */
        .h4x12 > .chart-wrap:only-child,
        .h4x8 > .chart-wrap:only-child,
        .h4x6 > .chart-wrap:only-child,
        .h4x4 > .chart-wrap:only-child {{ grid-row: 1 / -1; }}

        /* Tall content blocks (taller than h4) for big tables */
        .h8x12 {{
            grid-row: span 9;
            display: grid;
            grid-template-rows: 80px 1fr;
            gap: var(--sp-2);
            grid-column: span 12;
        }}
        .h8x12 > .cell {{ grid-row: 2; overflow:auto; }}

        /* Slider cards keep fixed dimensions */
        .slider > .cell .chart-wrap {{ height: 180px; flex: none; }}

        /* KPI block (Summary page) — 4 cols wide × 5 rows tall (1 title + 4 data) */
        .kpi-block {{
            grid-column: span 4;
            grid-row: span 5;
            display: grid;
            grid-template-rows: 80px 1fr;
            gap: var(--sp-2);
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: repeat(4, 1fr);
            gap: var(--sp-2);
        }}
        .kpi-grid .kpi-rps {{ grid-column: 1; grid-row: 1; }}
        .kpi-grid .kpi-rev {{ grid-column: 2; grid-row: 1; }}
        .kpi-grid .kpi-atc {{ grid-column: 1; grid-row: 2 / span 2; }}
        .kpi-grid .kpi-pr  {{ grid-column: 2; grid-row: 2 / span 2; }}
        .kpi-grid .kpi-c2p {{ grid-column: 1 / span 2; grid-row: 4; }}
        .kpi-grid .cell-kpi {{ padding: 10px var(--sp-3); display: flex; flex-direction: column; justify-content: space-between; }}
        .kpi-grid .cell-kpi .kpi-label {{ font-size: var(--fs-tag); }}
        .kpi-grid .cell-kpi .kpi-value {{ font-size: var(--fs-kpi-lg); font-weight: var(--fw-bold); line-height: 1.1; }}
        .kpi-grid .cell-kpi .kpi-spark {{ flex: 1; min-height: 30px; margin-top: var(--sp-1); background: var(--bg-muted); border-radius: var(--r-md); padding: 2px; position: relative; }}
        .kpi-grid .cell-kpi .kpi-spark .chart-wrap {{ height: 100%; }}

        /* KPI card (2x2) */
        .cell-kpi {{ display: flex; flex-direction: column; }}
        .kpi-label {{ font-size: var(--fs-label); text-transform: uppercase; color: var(--tx-secondary); letter-spacing: var(--ls-label); }}
        .kpi-value {{ font-size: var(--fs-kpi-xl); font-weight: var(--fw-bold); margin: var(--sp-1) 0; }}
        .kpi-bench {{ font-size: var(--fs-label); color: var(--tx-muted); }}
        .kpi-meta {{ display: flex; gap: var(--sp-2); align-items: baseline; }}
        .kpi-spark {{ background: var(--bg-muted); border-radius: var(--r-lg); margin-top: var(--sp-2); padding: var(--sp-1); flex: 1; min-height: 40px; }}

        /* Slider (channel cards, bubble charts) */
        .slider {{ display: flex; gap: var(--sp-4); overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: var(--sp-2); margin-bottom: var(--sp-5); }}
        .slider::-webkit-scrollbar {{ height: 6px; }}
        .slider::-webkit-scrollbar-thumb {{ background: var(--tx-muted); border-radius: var(--r-sm); }}
        .slider > .cell {{ min-width: 380px; max-width: 380px; flex-shrink: 0; scroll-snap-align: start; }}

        /* Shared */
        .nr-bar {{ height: 10px; background: var(--c-channel-social); border-radius: 5px; overflow: hidden; }}
        .nr-new {{ height: 100%; background: var(--c-channel-organic); }}
        .ch-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
        .delta {{ font-size: var(--fs-meta); }}
        .delta.green {{ color: var(--c-growth); }}
        .delta.red {{ color: var(--c-decline); }}
        .delta.neutral {{ color: var(--c-neutral); }}
        .metrics {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--sp-2); margin-top: var(--sp-3); }}
        .metric {{ display: flex; flex-direction: column; }}
        .metric .label {{ font-size: var(--fs-label); color: var(--tx-secondary); text-transform: uppercase; }}
        .metric .value {{ font-size: var(--fs-metric); font-weight: var(--fw-semibold); }}
        .top-countries {{ margin-top: var(--sp-3); }}
        .country-row {{ display: flex; justify-content: space-between; font-size: var(--fs-body); padding: 2px 0; border-bottom: 1px solid var(--bg-divider); }}

        /* Filters */
        .bubble-filters {{ display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-bottom: var(--sp-3); padding: var(--sp-2) var(--sp-3); background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); }}
        .bubble-filters label {{ font-size: var(--fs-label); cursor: pointer; display: flex; align-items: center; gap: var(--sp-1); }}
        .bubble-filters input {{ cursor: pointer; }}

        /* Data tables */
        .data-table {{ width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: var(--r-xl); overflow: hidden; box-shadow: var(--sh-card); }}
        .data-table th {{ background: var(--bg-inverse); color: var(--tx-ondark); padding: var(--sp-2) var(--sp-3); font-size: var(--fs-th); text-align: left; font-weight: var(--fw-semibold); cursor: pointer; user-select: none; }}
        .data-table th:hover {{ background: var(--bg-inverse2); }}
        .data-table td {{ padding: 6px var(--sp-3); font-size: var(--fs-table); border-bottom: 1px solid var(--bg-divider); }}
        .data-table tr:hover {{ background: var(--bg-hover); }}
        .data-table .highlight {{ font-weight: var(--fw-bold); color: var(--c-highlight); }}
        /* Compact tables: don't stretch rows when cell is taller than content */
        .data-table.tbl-compact {{ align-self: flex-start; }}
        .data-table.tbl-compact td, .data-table.tbl-compact th {{ height: auto; line-height: 1.3; }}

        /* Tab containment */
        #tab-funnels, #tab-analytics {{ contain: layout; }}

        @media (max-width: 900px) {{
            .grid {{ grid-template-columns: repeat(6, 1fr); }}
            .h4x12, .h4x8, .h4x6, .h4x4 {{ grid-column: span 6; }}
            .h2x2 {{ grid-column: span 3; }}
        }}
    </style>
</head>
<body>
    <header class="sticky-header">
        <div class="header-left">
            <div class="brand">Pinkspink</div>
            <div class="header-meta">
                <div>Сгенерировано: {data['generated']}</div>
                <div>Исключены: {', '.join(data['excluded_countries'])}</div>
            </div>
        </div>
        <div class="header-right">
            <nav class="grain-nav">
                <a href="report_day.html" class="grain-sq {'grain-active' if data['grain'] == 'day' else ''}">D</a>
                <a href="report_week.html" class="grain-sq {'grain-active' if data['grain'] == 'week' else ''}">W</a>
                <a href="report_month.html" class="grain-sq {'grain-active' if data['grain'] == 'month' else ''}">M</a>
            </nav>
            <nav class="device-nav" title="Фильтр устройства (UI, без пересчёта)">
                <button class="grain-btn grain-active" data-device="all" onclick="setDeviceFilter('all', this)">Все</button>
                <button class="grain-btn" data-device="mobile" onclick="setDeviceFilter('mobile', this)">Моб</button>
                <button class="grain-btn" data-device="desktop" onclick="setDeviceFilter('desktop', this)">Веб</button>
            </nav>
            <div class="country-filter">
                <button class="grain-btn" id="country-toggle" onclick="toggleCountryPanel(event)" title="Фильтр стран (UI, без пересчёта)">
                    Страны <span id="country-count">{country_checked_initial} из {country_total}</span> ▾
                </button>
                <div class="country-panel" id="country-panel" hidden>
                    <div class="country-section-title">Исключённые</div>
                    <div class="country-section">{country_excluded_html}</div>
                    <hr class="country-sep">
                    <div class="country-section-title">Все страны</div>
                    <div class="country-section country-list">{country_included_html}</div>
                </div>
            </div>
            <div class="filters-note">фильтры визуально, пересчёт — в след. итерации</div>
            <nav class="tab-nav">
                <button class="tab-btn tab-active" onclick="switchTab('summary', this)">Сводка</button>
                <button class="tab-btn" onclick="switchTab('funnels', this)">Воронки</button>
                <button class="tab-btn" onclick="switchTab('analytics', this)">Карточка товара</button>
            </nav>
        </div>
    </header>

    <div class="main-container">

    <!-- ===== SUMMARY TAB ===== -->
    <div id="tab-summary">
        <div class="grid">
            <div class="kpi-block">
                <div class="title-area">
                    <h3>KPI <span class="agg-tag">vs avg {'3 прошлых месяца' if data['grain'] == 'month' else ('4 прошлые недели' if data['grain'] == 'week' else '7 прошлых дней')}</span></h3>
                    <p class="meta">Показатели и сравнение со средними значениями</p>
                </div>
                <div class="kpi-grid">
                    <div class="cell cell-kpi kpi-rps">
                        <div class="kpi-label">Revenue / Session <span class="agg-tag">(mean)</span></div>
                        <div class="kpi-value" id="sum-kpi-rps"></div>
                        <div id="sum-kpi-rps-delta"></div>
                    </div>
                    <div class="cell cell-kpi kpi-rev">
                        <div class="kpi-label">Revenue <span class="agg-tag">(sum)</span></div>
                        <div class="kpi-value" id="sum-kpi-rev"></div>
                        <div id="sum-kpi-rev-delta"></div>
                    </div>
                    <div class="cell cell-kpi kpi-atc">
                        <div class="kpi-label">ATC Rate <span class="agg-tag">(rate)</span></div>
                        <div class="kpi-value" id="sum-kpi-atc"></div>
                        <div id="sum-kpi-atc-delta"></div>
                        <div class="kpi-spark"><canvas id="sum-spark-atc"></canvas></div>
                    </div>
                    <div class="cell cell-kpi kpi-pr">
                        <div class="kpi-label">Purchase Rate <span class="agg-tag">(rate)</span></div>
                        <div class="kpi-value" id="sum-kpi-pr"></div>
                        <div id="sum-kpi-pr-delta"></div>
                        <div class="kpi-spark"><canvas id="sum-spark-pr"></canvas></div>
                    </div>
                    <div class="cell cell-kpi kpi-c2p">
                        <div class="kpi-label">Cart → Purchase <span class="agg-tag">(rate)</span></div>
                        <div class="kpi-value" id="sum-kpi-c2p"></div>
                        <div id="sum-kpi-c2p-delta"></div>
                    </div>
                </div>
            </div>

            <div class="h4x8">
                <div class="title-area">
                    <h3>Посетители и сессии <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">Сколько заходят на сайт</p>
                </div>
                <div class="cell"><canvas id="sum-visitors-sessions"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="h4x6">
                <div class="title-area">
                    <h3>Сессии по типу девайсов <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">С каких девайсов чаще посещают сайт</p>
                </div>
                <div class="cell"><canvas id="sum-device-sessions"></canvas></div>
            </div>
            <div class="h4x6">
                <div class="title-area">
                    <h3>Новые vs Вернувшиеся <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">Какая доля посетила сайт первый раз, а какая вернулась</p>
                </div>
                <div class="cell"><canvas id="sum-new-returning"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="h4x6">
                <div class="title-area">
                    <h3>Время на сайте <span class="agg-tag">(median, sec)</span></h3>
                    <p class="meta">В разрезе устройств — на каких дольше проводят время</p>
                </div>
                <div class="cell"><canvas id="sum-time-on-site"></canvas></div>
            </div>
            <div class="h4x6">
                <div class="title-area">
                    <h3>Bounce Rate <span class="agg-tag">(rate)</span></h3>
                    <p class="meta">С каких устройств чаще уходят (sessions_1page / sessions)</p>
                </div>
                <div class="cell"><canvas id="sum-bounce-device"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="h4x12">
                <div class="title-area">
                    <h3>Источник трафика <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">Какой источник трафика преобладает и его динамика</p>
                </div>
                <div class="cell"><canvas id="sum-source-trend"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="h4x12">
                <div class="title-area">
                    <h3>Таблица по источнику трафика</h3>
                    <p class="meta">Значения за последний период + дельта vs avg прошлых периодов</p>
                </div>
                <div class="cell" style="overflow-x:auto;">
                    <table class="data-table" id="sum-source-table">
                        <thead>
                            <tr>
                                <th>Источник</th>
                                <th>Users <span class="agg-tag">sum</span></th>
                                <th>Сессии <span class="agg-tag">sum</span></th>
                                <th>New <span class="agg-tag">sum</span></th>
                                <th>Return <span class="agg-tag">sum</span></th>
                                <th>ER <span class="agg-tag">rate</span></th>
                                <th>Bounce <span class="agg-tag">rate</span></th>
                                <th>Время <span class="agg-tag">median</span></th>
                                <th>Pages/sess <span class="agg-tag">mean</span></th>
                                <th>ATC Rate <span class="agg-tag">rate</span></th>
                                <th>PR <span class="agg-tag">rate</span></th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="h4x12">
                <div class="title-area">
                    <h3>Посетители по странам</h3>
                    <p class="meta">Значения за последний период + дельта vs avg прошлых периодов</p>
                </div>
                <div class="cell" style="overflow-x:auto;">
                    <table class="data-table" id="sum-country-table">
                        <thead>
                            <tr>
                                <th>Страна</th>
                                <th>Users <span class="agg-tag">sum</span></th>
                                <th>Сессии <span class="agg-tag">sum</span></th>
                                <th>New <span class="agg-tag">sum</span></th>
                                <th>Return <span class="agg-tag">sum</span></th>
                                <th>ER <span class="agg-tag">rate</span></th>
                                <th>Bounce <span class="agg-tag">rate</span></th>
                                <th>Время <span class="agg-tag">median</span></th>
                                <th>Pages/sess <span class="agg-tag">mean</span></th>
                                <th>ATC Rate <span class="agg-tag">rate</span></th>
                                <th>PR <span class="agg-tag">rate</span></th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="h4x12">
                <div class="title-area">
                    <h3>ATC Rate + Purchase Rate <span class="agg-tag">(rate)</span></h3>
                    <p class="meta">ATC Rate = add_to_cart / sessions &nbsp;&middot;&nbsp; PR = purchase / sessions</p>
                </div>
                <div class="cell"><canvas id="sum-atc-pr-trend"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="h4x6">
                <div class="title-area">
                    <h3>Рейтинг ATC <span class="agg-tag">top-10</span></h3>
                    <p class="meta">Комбинации Источник × Страна × Тип юзера (min 10 сессий)</p>
                </div>
                <div class="cell">
                    <table class="data-table">
                        <thead>
                            <tr><th>Источник</th><th>Страна</th><th>Тип</th><th>Sessions</th><th>ATC Rate</th></tr>
                        </thead>
                        <tbody id="sum-ranking-atc"></tbody>
                    </table>
                </div>
            </div>
            <div class="h4x6">
                <div class="title-area">
                    <h3>Рейтинг Purchase Rate <span class="agg-tag">top-10</span></h3>
                    <p class="meta">Комбинации Источник × Страна × Тип юзера (min 10 сессий)</p>
                </div>
                <div class="cell">
                    <table class="data-table">
                        <thead>
                            <tr><th>Источник</th><th>Страна</th><th>Тип</th><th>Sessions</th><th>PR</th></tr>
                        </thead>
                        <tbody id="sum-ranking-pr"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <h2 style="margin-top:32px;">Scroll Rate по сайту</h2>
        <p class="meta">
            <strong>Что это:</strong> GA4 шлёт событие <code>scroll</code>, когда пользователь долистал любую страницу до 90%. Здесь — % сессий, в которых это произошло хотя бы один раз (на любой странице сайта).<br>
            <strong>Зачем:</strong> высокий scroll rate = страницы вовлекают, пользователи дочитывают. Низкий = «посмотрели и ушли».
        </p>
        <div class="grid">
            <div class="h4x6">
                <div class="title-area"><h3>По устройствам</h3><p class="meta">% сессий со scroll до 90% (любая страница)</p></div>
                <div class="cell"><canvas id="sum-scroll-site-device"></canvas></div>
            </div>
            <div class="h4x6">
                <div class="title-area"><h3>По каналам</h3><p class="meta">% сессий со scroll до 90% (любая страница)</p></div>
                <div class="cell"><canvas id="sum-scroll-site-channel"></canvas></div>
            </div>
        </div>

        <h2 style="margin-top:32px;">Cohort Retention</h2>
        <p class="meta">
            <strong>Что это:</strong> разрезаем пользователей по неделе их ПЕРВОГО визита (когорта) и смотрим, сколько % из них возвращались через 1, 2, 3… недель.<br>
            <strong>Как читать:</strong> над каждым столбиком сверху подписан размер когорты (новички за ту неделю). Цветные сегменты внутри — % этой когорты, который пришёл снова через N недель. На графике скрыта «Неделя 0», чтобы маленькие проценты возврата были видны — её можно включить в легенде.<br>
            <strong>Зачем:</strong> понять, удерживает ли Pinkspink пользователей. Растёт retention от когорты к когорте = улучшения работают.
        </p>
        <div class="grid">
            <div class="h4x12">
                <div class="title-area"><h3>Retention по когортам</h3><p class="meta">% вернувшихся (Неделя 0 скрыта по умолчанию — клик в легенде включит)</p></div>
                <div class="cell"><canvas id="sum-cohort"></canvas></div>
            </div>
        </div>
    </div><!-- end tab-summary -->


    <!-- ===== FUNNELS TAB ===== -->
    <div id="tab-funnels" style="display:none;">

    <h2>Динамика воронок по устройствам</h2>
    <p class="meta" style="max-width: 980px;">
        Сверху — объём трафика на каждом этапе воронки в шт. (где сколько сессий побывало).
        Снизу — конверсия от предыдущего шага в %: одна линия — один переход.
        Смотрите вместе: верхние графики говорят «много ли народу» доходит до этапа,
        нижние — «насколько хорошо» этап переводит на следующий. Просадка любой линии
        внизу — слабое место воронки за период.
    </p>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>Мобилка — этапы, сессии</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="stacked-mobile"></canvas></div></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>Веб — этапы, сессии</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="stacked-desktop"></canvas></div></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>Мобилка — конверсии между этапами, %</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="pct-mobile"></canvas></div></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>Веб — конверсии между этапами, %</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="pct-desktop"></canvas></div></div>
        </div>
    </div>

    <h3>Воронка по каналам</h3>
    <div class="slider">{cards_html}</div>

    <h3>Воронка по source (топ-5)</h3>
    <div class="slider">{source_cards_html}</div>

    <h2>Кто добавляет в корзину и покупает</h2>
    <p class="meta">Период: {data['periods'][-1] if data['periods'] else '—'}</p>
    <div class="grid">
        <div class="cell h4x12">
            <table class="data-table">
                <thead><tr><th>Source</th><th>Страна</th><th>Сессии</th><th>Каталог</th><th>Товар</th><th>Корзина</th><th>Чекаут</th><th>Покупка</th></tr></thead>
                <tbody>{bottom_funnel_html}</tbody>
            </table>
        </div>
    </div>

    <h2>Эффективность каналов по этапам</h2>
    <p class="meta" style="max-width: 980px;">
        По каждому переходу воронки — пара графиков: <b>слева</b> текущий период
        ({data['periods'][-1] if data['periods'] else '—'}), точка = канал, X — сессии на этапе,
        Y — конверсия в следующий, размер пузыря — сессии. В подсказке — Δ vs среднее за 4 предыдущих периода (п.п.).
        <b>Справа</b> — динамика конверсии по {('дням' if data['grain'] == 'day' else 'неделям' if data['grain'] == 'week' else 'месяцам')},
        одна линия — один канал. Чек-боксы у заголовка этапа включают/выключают канал на этом этапе — удобно для изоляции одного канала.
    </p>

    <h3>Каталог → Товар</h3>
    <div class="bubble-filters" id="filter-channel-prod"></div>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>текущий период</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="bubble-channel-prod"></canvas></div></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>динамика, %</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="trend-channel-prod"></canvas></div></div>
        </div>
        <div class="cell h4x12" style="overflow:auto;">{stage_table_prod_html}</div>
    </div>

    <h3>Товар → Корзина</h3>
    <div class="bubble-filters" id="filter-channel-atc"></div>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>текущий период</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="bubble-channel-atc"></canvas></div></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>динамика, %</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="trend-channel-atc"></canvas></div></div>
        </div>
        <div class="cell h4x12" style="overflow:auto;">{stage_table_atc_html}</div>
    </div>

    <h3>Корзина → Чекаут</h3>
    <div class="bubble-filters" id="filter-channel-checkout"></div>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>текущий период</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="bubble-channel-checkout"></canvas></div></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>динамика, %</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="trend-channel-checkout"></canvas></div></div>
        </div>
        <div class="cell h4x12" style="overflow:auto;">{stage_table_checkout_html}</div>
    </div>

    <h3>Чекаут → Покупка</h3>
    <div class="bubble-filters" id="filter-channel-purchase"></div>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>текущий период</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="bubble-channel-purchase"></canvas></div></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>динамика, %</h3></div>
            <div class="cell"><div class="chart-wrap"><canvas id="trend-channel-purchase"></canvas></div></div>
        </div>
        <div class="cell h4x12" style="overflow:auto;">{stage_table_purchase_html}</div>
    </div>
    </div><!-- end tab-funnels -->

    <!-- ===== КАРТОЧКА ТОВАРА TAB ===== -->
    <div id="tab-analytics" style="display:none;">

    <h2>Время на одной карточке товара</h2>
    <p class="meta">
        <strong>Что это:</strong> сколько секунд пользователь смотрит ОДНУ карточку товара, прежде чем перейти к следующему действию (другая карточка / каталог / закрытие).
        Считается как разница между событием view_item и следующим событием в сессии. Кап 5 мин (защита от «оставил вкладку и ушёл»).<br>
        <strong>Median</strong> = «типичный» пользователь. <strong>Mean</strong> = среднее, чувствительно к тем, кто долго залипает.<br>
        <strong>Зачем:</strong> чем больше времени на карточке, тем интереснее контент (фото, описание, кнопка See it on others). Метрика для UX-аудита изменений в карточке.
    </p>
    <div class="grid">
        <div class="cell h4x12"><canvas id="analytics-per-card-time"></canvas></div>
    </div>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>По странам — последняя полная неделя</h3><p class="meta">Δ vs avg прошлых 4 недель</p></div>
            <div class="cell" style="overflow:auto;">
                <table class="data-table tbl-compact" id="tbl-per-card-country">
                    <thead><tr><th>Страна</th><th>Card views</th><th>Median sec</th><th>Δ Median</th><th>Mean sec</th><th>Δ Mean</th></tr></thead>
                    <tbody>{per_card_country_rows}</tbody>
                </table>
            </div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>По source — последняя полная неделя</h3><p class="meta">Δ vs avg прошлых 4 недель</p></div>
            <div class="cell" style="overflow:auto;">
                <table class="data-table tbl-compact" id="tbl-per-card-source">
                    <thead><tr><th>Source</th><th>Card views</th><th>Median sec</th><th>Δ Median</th><th>Mean sec</th><th>Δ Mean</th></tr></thead>
                    <tbody>{per_card_source_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <h2>Карточек за сессию — разрез по странам и source</h2>
    <p class="meta">Mobile, последняя полная неделя. Сколько карточек товара открывает один пользователь за сессию.</p>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>По странам</h3><p class="meta">Δ vs avg прошлых 4 недель</p></div>
            <div class="cell" style="overflow:auto;">
                <table class="data-table tbl-compact" id="tbl-cards-country">
                    <thead><tr><th>Страна</th><th>Сессии</th><th>Median карт.</th><th>Δ Median</th><th>Mean карт.</th><th>Δ Mean</th></tr></thead>
                    <tbody>{cards_country_rows}</tbody>
                </table>
            </div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>По source</h3><p class="meta">Δ vs avg прошлых 4 недель</p></div>
            <div class="cell" style="overflow:auto;">
                <table class="data-table tbl-compact" id="tbl-cards-source">
                    <thead><tr><th>Source</th><th>Сессии</th><th>Median карт.</th><th>Δ Median</th><th>Mean карт.</th><th>Δ Mean</th></tr></thead>
                    <tbody>{cards_source_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <h2>Топ-30 карточек товара</h2>
    <p class="meta">Mobile + desktop, без excluded стран. Сортировка — клик по любому заголовку колонки.</p>
    <div class="grid">
        <div class="h8x12">
            <div class="title-area">
                <div style="display:flex; gap:8px;">
                    <button class="grain-btn grain-active" id="tp-period-week" onclick="setTopProductsPeriod('week', this)">Последняя неделя</button>
                    <button class="grain-btn" id="tp-period-4w" onclick="setTopProductsPeriod('agg_4w', this)">4 недели (агрегат)</button>
                </div>
            </div>
            <div class="cell" style="overflow:auto;">
                <table class="data-table tbl-compact" id="tbl-top-products">
                    <thead><tr>
                        <th>#</th><th>Товар</th><th>Views</th><th>Med sec</th><th>Mean sec</th>
                        <th>ATC</th><th>Purchase</th><th>CR view→ATC</th>
                    </tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>

    <h2>Время на товарных страницах (сессия целиком)</h2>
    <p class="meta">
        <strong>Что это:</strong> медианное время вовлечения <em>за всю сессию</em>, в которой пользователь хотя бы раз открыл карточку товара (event view_item). Это НЕ время на одной карточке — это «общее время на сайте» среди тех, кто доходит до товара.<br>
        <strong>Чем отличается от блока выше:</strong> per-card time = сколько на ОДНОЙ карточке. Этот график = сколько на сайте у тех, кто кликнул хотя бы на товар.<br>
        <strong>Зачем:</strong> сравнить «глубину» вовлечения по каналам. Direct/Organic обычно дольше; Paid — короче.
    </p>
    <div class="grid"><div class="cell h4x12"><canvas id="analytics-product-time"></canvas></div></div>

    <h2>Scroll на странице товара</h2>
    <p class="meta">
        <strong>Что это:</strong> GA4 шлёт событие <code>scroll</code>, когда пользователь долистал страницу до 90% высоты. Здесь — % сессий, в которых это произошло именно на странице товара (URL содержит <code>/products/</code>).<br>
        <strong>Зачем:</strong> низкий scroll = пользователи не дочитывают до фото внизу / кнопки IG / описания. Высокий = карточка прочитана.
    </p>
    <div class="grid">
        <div class="h4x6">
            <div class="title-area"><h3>По устройствам</h3><p class="meta">% сессий с view_item, в которых был scroll до 90%</p></div>
            <div class="cell"><canvas id="analytics-scroll-product-device"></canvas></div>
        </div>
        <div class="h4x6">
            <div class="title-area"><h3>По каналам</h3><p class="meta">% сессий с view_item, в которых был scroll до 90%</p></div>
            <div class="cell"><canvas id="analytics-scroll-product-channel"></canvas></div>
        </div>
    </div>

    <h2>Глубина каталога</h2>
    <p class="meta">
        <strong>Что это:</strong> сколько страниц каталога перелистал пользователь, считая по параметру <code>?page=N</code> в URL <code>/collections/...?page=N</code>. На графике — распределение сессий по максимальному номеру страницы каталога, который они открыли.<br>
        <strong>⚠ Важные ограничения:</strong>
        — Считаем ТОЛЬКО пагинацию через <code>?page=2,3,4...</code> (кнопка «следующая страница»).
        — Если пользователь использует <strong>фильтры</strong> (цвет/размер/категория), фильтры обычно НЕ меняют <code>?page=</code>, и эти сессии попадают в «Стр. 1».
        — Если пользователь зашёл на <strong>под-каталог</strong> (например <code>/collections/tops</code>), это всё ещё <code>/collections/</code>, и пагинация считается ВНУТРИ этого под-каталога. Прыжки между разными коллекциями метрика НЕ ловит.<br>
        <strong>Что эта метрика реально показывает:</strong> «дочитывают ли пользователи длинные ленты товаров, или быстро переходят на товар». «Стр. 4+» = очень упорные искатели.<br>
        <strong>Альтернатива (можно добавить):</strong> «количество разных URL <code>/collections/*</code> за сессию» — это лучше отразит «обход разных категорий».
    </p>
    <div class="grid"><div class="cell h4x12"><canvas id="analytics-catalog-depth"></canvas></div></div>

    </div><!-- end tab-analytics -->

    <script>
    const DATA = {json.dumps(data, ensure_ascii=False)};

    {chart_js_defaults}

    // Tab switching with lazy chart init
    const tabInited = {{ summary: false, overview: false, funnels: false, analytics: false }};
    // Global header filters — UI only, no data re-aggregation yet.
    function setDeviceFilter(device, btn) {{
        btn.parentElement.querySelectorAll('.grain-btn').forEach(b => b.classList.remove('grain-active'));
        btn.classList.add('grain-active');
        // TODO: trigger global re-render — to be wired in a follow-up task
    }}

    function toggleCountryPanel(e) {{
        if (e) e.stopPropagation();
        const panel = document.getElementById('country-panel');
        panel.hidden = !panel.hidden;
    }}

    function updateCountryCount() {{
        const all = document.querySelectorAll('.country-section input[type="checkbox"]');
        const checked = Array.from(all).filter(cb => cb.checked).length;
        const counter = document.getElementById('country-count');
        if (counter) counter.textContent = checked + ' из ' + all.length;
        // TODO: trigger global re-render — to be wired in a follow-up task
    }}

    document.addEventListener('DOMContentLoaded', () => {{
        document.querySelectorAll('.country-section input[type="checkbox"]').forEach(cb => {{
            cb.addEventListener('change', updateCountryCount);
        }});
        document.addEventListener('click', (ev) => {{
            const filter = document.querySelector('.country-filter');
            const panel = document.getElementById('country-panel');
            if (panel && filter && !filter.contains(ev.target)) {{
                panel.hidden = true;
            }}
        }});
    }});

    function switchTab(tab, btn) {{
        ['summary', 'overview', 'funnels', 'analytics'].forEach(t => {{
            const el = document.getElementById('tab-' + t);
            if (el) el.style.display = t === tab ? 'block' : 'none';
        }});
        btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('tab-active'));
        btn.classList.add('tab-active');
        if (!tabInited[tab]) {{
            tabInited[tab] = true;
            if (tab === 'summary') initSummaryTab();
            if (tab === 'funnels') initFunnelsTab();
            if (tab === 'analytics') initAnalyticsTab();
        }}
    }}

    // Sortable table — colIdx must be index within OWN table, not global across all tables.
    // Also delegate from <table> so dynamically rendered rows (e.g. Top-30) sort correctly.
    document.querySelectorAll('.data-table').forEach(table => {{
        table.addEventListener('click', e => {{
            const th = e.target.closest('th');
            if (!th || !table.contains(th)) return;
            const headers = Array.from(table.querySelectorAll('thead th'));
            const colIdx = headers.indexOf(th);
            if (colIdx < 0) return;
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const asc = th.dataset.sort !== 'asc';
            headers.forEach(h => {{ h.dataset.sort = ''; h.textContent = h.textContent.replace(/ [↑↓]$/, ''); }});
            th.dataset.sort = asc ? 'asc' : 'desc';
            th.textContent = th.textContent + (asc ? ' ↑' : ' ↓');
            rows.sort((a, b) => {{
                const va = (a.cells[colIdx] ? a.cells[colIdx].textContent : '').trim();
                const vb = (b.cells[colIdx] ? b.cells[colIdx].textContent : '').trim();
                const na = parseFloat(va), nb = parseFloat(vb);
                if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
                return asc ? va.localeCompare(vb) : vb.localeCompare(va);
            }});
            rows.forEach(r => tbody.appendChild(r));
        }});
    }});

    // Auto-wrap every canvas in a fixed-size container BEFORE any Chart.js init.
    // This breaks the Chart.js responsive feedback loop that causes infinite growth.
    document.querySelectorAll('canvas').forEach(c => {{
        if (c.parentElement && c.parentElement.classList.contains('chart-wrap')) return;
        const wrap = document.createElement('div');
        wrap.className = 'chart-wrap';
        c.parentNode.insertBefore(wrap, c);
        wrap.appendChild(c);
    }});

    Chart.register(ChartDataLabels);
    Chart.defaults.animation = false;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.responsive = true;
    Chart.defaults.font.family = "'Ubuntu Mono', monospace";
    Chart.defaults.font.size = 11;
    Chart.defaults.plugins.legend.labels.boxWidth = 10;
    Chart.defaults.plugins.legend.labels.boxHeight = 10;
    Chart.defaults.plugins.legend.labels.font = {{ size: 10 }};
    Chart.defaults.plugins.legend.labels.padding = 12;
    Chart.defaults.plugins.legend.labels.boxHeight = 10;

    // Shared scroll-rate aggregators (used by both Сводка and Карточка товара tabs)
    function _scrollAgg(period, filterFn, kind) {{
        const A = DATA.analytics;
        if (!A || !A.scroll) return 0;
        let num = 0, den = 0;
        A.scroll.forEach(r => {{
            if (r.period !== period || !filterFn(r)) return;
            if (kind === 'site') {{ num += r.sessions_with_scroll; den += r.sessions; }}
            else {{ num += r.scroll_on_product; den += r.sessions_with_product; }}
        }});
        return den > 0 ? Math.round(num / den * 100) : 0;
    }}
    function scrollByDev(period, device, kind) {{ return _scrollAgg(period, r => r.device === device, kind); }}
    function scrollByCh(period, channel, kind)  {{ return _scrollAgg(period, r => r.channel === channel, kind); }}

    // Plugin: adds spacing between legend and chart area
    const legendSpacingPlugin = {{
        id: 'legendSpacing',
        beforeInit(chart) {{
            const originalFit = chart.legend && chart.legend.fit;
            if (chart.legend && originalFit) {{
                chart.legend.fit = function fit() {{
                    originalFit.bind(chart.legend)();
                    this.height += 12;
                }};
            }}
        }}
    }};
    Chart.register(legendSpacingPlugin);
    Chart.defaults.plugins.legend.align = 'start';

    // Sparkline for KPI cards
    function sparkline(id, data, color) {{
        const el = document.getElementById(id);
        if (!el || !data || data.length === 0) return;
        new Chart(el, {{
            type: 'line',
            data: {{
                labels: data.map((_, i) => i),
                datasets: [{{ data, borderColor: color || '#2D3436', borderWidth: 2, pointRadius: 0, fill: false, tension: 0.4 }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }}, datalabels: {{ display: false }} }},
                scales: {{ x: {{ display: false }}, y: {{ display: false }} }},
            }}
        }});
    }}

    // Funnel bar chart (grouped, not stacked)
    function funnelBar(id, chartData) {{
        new Chart(document.getElementById(id), {{
            type: 'bar',
            data: {{
                labels: chartData.labels,
                datasets: chartData.datasets
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        anchor: 'end',
                        align: 'top',
                        font: {{ size: 10 }},
                        formatter: v => v > 0 ? v : ''
                    }}
                }},
                layout: {{ padding: {{ top: 10 }} }},
                scales: {{
                    x: {{ stacked: false }},
                    y: {{ beginAtZero: true, grace: '15%' }}
                }}
            }}
        }});
    }}

    function funnelPctLine(id, chartData) {{
        new Chart(document.getElementById(id), {{
            type: 'line',
            data: {{ labels: chartData.labels, datasets: chartData.datasets }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        align: 'top',
                        font: {{ size: 10 }},
                        formatter: v => v != null ? v.toFixed(1) + '%' : ''
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%'
                        }}
                    }}
                }},
                layout: {{ padding: {{ top: 10 }} }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grace: '15%',
                        ticks: {{ callback: v => v + '%' }}
                    }}
                }}
            }}
        }});
    }}

    function channelTrendLine(id, chartData) {{
        return new Chart(document.getElementById(id), {{
            type: 'line',
            data: {{ labels: chartData.labels, datasets: chartData.datasets }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    datalabels: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => ctx.dataset.label + ': ' + (ctx.parsed.y == null ? '—' : ctx.parsed.y.toFixed(1) + '%')
                        }}
                    }}
                }},
                layout: {{ padding: {{ top: 10 }} }},
                scales: {{
                    y: {{ beginAtZero: true, grace: '15%', ticks: {{ callback: v => v + '%' }} }}
                }}
            }}
        }});
    }}

    function initFunnelsTab() {{
        funnelBar('stacked-mobile', DATA.mobile_funnel);
        funnelBar('stacked-desktop', DATA.desktop_funnel);
        funnelPctLine('pct-mobile', DATA.mobile_funnel_pct);
        funnelPctLine('pct-desktop', DATA.desktop_funnel_pct);
        DATA.channel_cards.forEach(card => {{
            const id = 'funnel-channel-' + card.channel.toLowerCase().replace(/\\s/g, '-');
            if (!document.getElementById(id)) return;
            funnelBar(id, card.funnel);
        }});
        DATA.source_cards.forEach(card => {{
            const id = 'funnel-source-' + card.source.replace(/\\./g, '_').replace(/[()]/g, '').replace(/ /g, '-');
            if (!document.getElementById(id)) return;
            funnelBar(id, card.funnel);
        }});

        // Channel effectiveness — per-stage bubble + trend pair, each with its own checkbox filter
        const CHANNEL_STAGES = [
            {{ stage: 'prod',     sessKey: 'funnel_catalog',  convKey: 'cat_to_prod',          deltaKey: 'delta_cat_to_prod',          xLabel: 'Сессии в каталоге',  trendKey: 'cat_to_prod' }},
            {{ stage: 'atc',      sessKey: 'funnel_product',  convKey: 'prod_to_atc',          deltaKey: 'delta_prod_to_atc',          xLabel: 'Сессии на товаре',   trendKey: 'prod_to_atc' }},
            {{ stage: 'checkout', sessKey: 'funnel_atc',      convKey: 'atc_to_checkout',      deltaKey: 'delta_atc_to_checkout',      xLabel: 'Сессии с корзиной',  trendKey: 'atc_to_checkout' }},
            {{ stage: 'purchase', sessKey: 'funnel_checkout', convKey: 'checkout_to_purchase', deltaKey: 'delta_checkout_to_purchase', xLabel: 'Сессии с чекаутом', trendKey: 'checkout_to_purchase' }},
        ];
        const channelOrder = DATA.channel_trend.channels;
        const channelColors = DATA.channel_trend.channel_colors;
        CHANNEL_STAGES.forEach(s => {{
            const bubbleId = 'bubble-channel-' + s.stage;
            const trendId  = 'trend-channel-'  + s.stage;
            const filterId = 'filter-channel-' + s.stage;
            const prefix   = 'ch-' + s.stage;

            const bubble = bubbleChart(bubbleId, DATA.bubble_channel, s.sessKey, s.convKey, s.xLabel, s.deltaKey, channelColors);
            const trend  = channelTrendLine(trendId, DATA.channel_trend[s.trendKey]);

            bubbleCharts[prefix] = [{{
                id: bubbleId, sessKey: s.sessKey, convKey: s.convKey, xLabel: s.xLabel,
                deltaKey: s.deltaKey, colorMap: channelColors, chart: bubble
            }}];
            buildBubbleFilters(filterId, DATA.bubble_channel, prefix, channelColors, channelOrder);

            // Sync this stage's trend visibility with this stage's checkboxes only
            document.querySelectorAll('input[data-prefix="' + prefix + '"]').forEach(cb => {{
                cb.addEventListener('change', () => {{
                    const idx = channelOrder.indexOf(cb.dataset.name);
                    if (idx === -1) return;
                    const ds = trend.data.datasets[idx];
                    if (ds) ds.hidden = !cb.checked;
                    trend.update();
                }});
            }});
        }});

    }} // end initFunnelsTab

    // Zone background plugin for bubble charts
    const zonePlugin = {{
        id: 'zoneBackground',
        beforeDraw: (chart) => {{
            if (!chart.options.plugins2 || !chart.options.plugins2.zones) return;
            const ctx = chart.ctx;
            const {{ left, right, top, bottom }} = chart.chartArea;
            const h = bottom - top;
            // Bottom third = red (low conversion)
            ctx.fillStyle = 'rgba(225, 112, 85, 0.06)';
            ctx.fillRect(left, top + h * 0.66, right - left, h * 0.34);
            // Middle third = yellow (average)
            ctx.fillStyle = 'rgba(253, 203, 110, 0.06)';
            ctx.fillRect(left, top + h * 0.33, right - left, h * 0.33);
            // Top third = green (high conversion)
            ctx.fillStyle = 'rgba(0, 184, 148, 0.06)';
            ctx.fillRect(left, top, right - left, h * 0.33);
        }}
    }};
    Chart.register(zonePlugin);

    // Bubble filter system
    const bubbleCharts = {{}};

    function buildBubbleFilters(containerId, items, prefix, colorMap, names) {{
        const container = document.getElementById(containerId);
        const list = names && names.length ? names : items.map(i => i.name);
        list.forEach(name => {{
            const label = document.createElement('label');
            label.style.cssText = 'display:inline-flex; align-items:center; gap:4px; margin-right:10px; cursor:pointer; font-size:12px;';
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = true;
            cb.dataset.name = name;
            cb.dataset.prefix = prefix;
            cb.addEventListener('change', () => redrawBubbles(prefix, items));
            label.appendChild(cb);
            if (colorMap && colorMap[name]) {{
                const dot = document.createElement('span');
                dot.style.cssText = 'display:inline-block; width:10px; height:10px; border-radius:50%; background:' + colorMap[name];
                label.appendChild(dot);
            }}
            label.appendChild(document.createTextNode(' ' + name));
            container.appendChild(label);
        }});
    }}

    function getExcluded(prefix) {{
        const cbs = document.querySelectorAll(`input[data-prefix="${{prefix}}"]`);
        const excluded = new Set();
        cbs.forEach(cb => {{ if (!cb.checked) excluded.add(cb.dataset.name); }});
        return excluded;
    }}

    function redrawBubbles(prefix, allItems) {{
        const excluded = getExcluded(prefix);
        const filtered = allItems.filter(i => !excluded.has(i.name));
        const configs = bubbleCharts[prefix];
        if (!configs) return;
        configs.forEach(cfg => {{
            cfg.chart.destroy();
            cfg.chart = bubbleChart(cfg.id, filtered, cfg.sessKey, cfg.convKey, cfg.xLabel, cfg.deltaKey, cfg.colorMap);
        }});
    }}

    // Override bubbleChart to return chart instance
    function bubbleChart(id, items, sessKey, convKey, xLabel, deltaKey, colorMap) {{
        const datasets = items.filter(item => item[sessKey] > 0).map(item => {{
            const color = (colorMap && colorMap[item.name]) || '#6C5CE7';
            return {{
                label: item.name,
                data: [{{ x: item[sessKey], y: item[convKey], r: Math.max(6, Math.sqrt(item[sessKey]) * 2) }}],
                backgroundColor: color + '66',
                borderColor: color,
                borderWidth: 1,
            }};
        }});
        return new Chart(document.getElementById(id), {{
            type: 'bubble',
            data: {{ datasets }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                layout: {{ padding: {{ top: 30, right: 60, bottom: 10, left: 10 }} }},
                plugins: {{
                    legend: {{ display: false }},
                    datalabels: {{
                        display: true,
                        formatter: (val, ctx) => {{
                            const filtered = items.filter(i => i[sessKey] > 0);
                            return filtered[ctx.datasetIndex] ? filtered[ctx.datasetIndex].name : '';
                        }},
                        font: {{ size: 9 }},
                        color: '#2D3436',
                        backgroundColor: 'rgba(255,255,255,0.8)',
                        borderRadius: 3,
                        padding: 3,
                        anchor: 'end',
                        align: function(ctx) {{
                            const idx = ctx.datasetIndex;
                            const angles = ['top', 'right', 'left', 'bottom', 'top', 'right', 'left', 'bottom'];
                            const filtered = items.filter(i => i[sessKey] > 0);
                            const item = filtered[idx];
                            if (!item) return 'top';
                            const xMax = Math.max(...filtered.map(i => i[sessKey]));
                            const yMax = Math.max(...filtered.map(i => i[convKey]));
                            if (item[sessKey] > xMax * 0.7) return 'left';
                            if (item[convKey] > yMax * 0.7) return 'bottom';
                            return angles[idx % angles.length];
                        }},
                        offset: 12,
                        clamp: true,
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => {{
                                const filtered = items.filter(i => i[sessKey] > 0);
                                const item = filtered[ctx.datasetIndex];
                                if (!item) return '';
                                const lines = [
                                    item.name,
                                    xLabel + ': ' + item[sessKey],
                                    'Конверсия: ' + item[convKey] + '%',
                                ];
                                if (deltaKey && item[deltaKey] != null) {{
                                    const d = item[deltaKey];
                                    const sign = d > 0 ? '+' : '';
                                    lines.push('Δ vs ср. 4 пред.: ' + sign + d + ' п.п.');
                                }}
                                lines.push('ER: ' + item.er + '%');
                                lines.push('Median: ' + item.median_sec + 's');
                                return lines;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ title: {{ display: true, text: xLabel }}, ticks: {{ font: {{ size: 9 }} }} }},
                    y: {{ title: {{ display: true, text: 'Конверсия %' }}, beginAtZero: true, ticks: {{ font: {{ size: 9 }}, callback: v => v + '%' }} }}
                }},
                plugins2: {{ zones: true }}
            }}
        }});
    }}


    // ===== ANALYTICS TAB CHARTS (lazy init) =====
    function initAnalyticsTab() {{
    const A = DATA.analytics;

    // 2. Scroll on product page — by device + by channel
    if (A.scroll && A.scroll.length > 0) {{
        const scrollChannels = ['Social', 'Paid', 'Direct', 'Organic', 'Referral'];
        const chColors = {{ Social: '#6C5CE7', Paid: '#00B894', Direct: '#636E72', Organic: '#0984E3', Referral: '#FDCB6E' }};
        const devColors = {{ mobile: '#6C5CE7', desktop: '#00B894' }};
        const devices = ['mobile', 'desktop'];
        const lineOpts = {{
            responsive: true, interaction: {{ mode: 'index', intersect: false }},
            plugins: {{
                legend: {{ position: 'top' }},
                datalabels: {{ display: false }},
                tooltip: {{ mode: 'index', intersect: false, callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + '%' }} }}
            }},
            scales: {{ y: {{ beginAtZero: true, max: 100, ticks: {{ callback: v => v + '%' }} }} }}
        }};

        const cvProductDev = document.getElementById('analytics-scroll-product-device');
        if (cvProductDev) new Chart(cvProductDev, {{
            type: 'line',
            data: {{
                labels: DATA.periods,
                datasets: devices.map(dev => ({{
                    label: dev === 'mobile' ? 'Мобилка' : 'Десктоп',
                    data: DATA.periods.map(p => scrollByDev(p, dev, 'product')),
                    borderColor: devColors[dev], tension: 0.3, borderWidth: 2, pointRadius: 3,
                }}))
            }},
            options: lineOpts
        }});

        const cvProductCh = document.getElementById('analytics-scroll-product-channel');
        if (cvProductCh) new Chart(cvProductCh, {{
            type: 'line',
            data: {{
                labels: DATA.periods,
                datasets: scrollChannels.map(ch => ({{
                    label: ch,
                    data: DATA.periods.map(p => scrollByCh(p, ch, 'product')),
                    borderColor: chColors[ch], tension: 0.3, borderWidth: 2, pointRadius: 3,
                }}))
            }},
            options: lineOpts
        }});
    }}

    // 3. Time on Product Page by channel
    if (A.product_time && A.product_time.length > 0) {{
        const ptByPeriodCh = {{}};
        A.product_time.forEach(r => {{ ptByPeriodCh[r.period + '|' + r.channel] = r; }});
        const ptChannels = ['Social', 'Paid', 'Direct', 'Organic', 'Referral'];
        const ptColors = {{ Social: '#6C5CE7', Paid: '#00B894', Direct: '#636E72', Organic: '#0984E3', Referral: '#FDCB6E' }};

        new Chart(document.getElementById('analytics-product-time'), {{
            type: 'line',
            data: {{
                labels: DATA.periods,
                datasets: ptChannels.map(ch => ({{
                    label: ch,
                    data: DATA.periods.map(p => {{
                        const r = ptByPeriodCh[p + '|' + ch];
                        return r ? r.median_sec : 0;
                    }}),
                    borderColor: ptColors[ch],
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 3,
                }}))
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{ display: false }},
                    tooltip: {{
                        mode: 'index', intersect: false,
                        callbacks: {{
                            label: ctx => {{
                                const r = ptByPeriodCh[DATA.periods[ctx.dataIndex] + '|' + ctx.dataset.label];
                                const sess = r ? r.sessions_with_product : 0;
                                return ctx.dataset.label + ': ' + ctx.parsed.y + 's (' + sess + ' сес.)';
                            }}
                        }}
                    }}
                }},
                scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Median sec' }} }} }}
            }}
        }});
    }}

    // 3b. Per-card view time (aggregate across all channels — one median, one mean line)
    if (DATA.per_card_chart && DATA.per_card_chart.length > 0) {{
        const pcByPeriod = {{}};
        DATA.per_card_chart.forEach(r => {{ pcByPeriod[r.period] = r; }});

        new Chart(document.getElementById('analytics-per-card-time'), {{
            type: 'line',
            data: {{
                labels: DATA.periods,
                datasets: [
                    {{
                        label: 'Median sec / card',
                        data: DATA.periods.map(p => pcByPeriod[p] ? pcByPeriod[p].median_sec : null),
                        borderColor: '#6C5CE7', backgroundColor: '#6C5CE7',
                        tension: 0.3, borderWidth: 3, pointRadius: 5,
                    }},
                    {{
                        label: 'Mean sec / card',
                        data: DATA.periods.map(p => pcByPeriod[p] ? pcByPeriod[p].mean_sec : null),
                        borderColor: '#00B894', backgroundColor: '#00B894',
                        borderDash: [6, 4], tension: 0.3, borderWidth: 2, pointRadius: 4,
                    }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        align: 'top', anchor: 'end', font: {{ size: 10, weight: 'bold' }},
                        formatter: v => v != null ? v + 's' : ''
                    }},
                    tooltip: {{
                        mode: 'index', intersect: false,
                        callbacks: {{
                            label: ctx => {{
                                const r = pcByPeriod[DATA.periods[ctx.dataIndex]];
                                const views = r ? r.card_views : 0;
                                return ctx.dataset.label + ': ' + ctx.parsed.y + 's (' + views + ' card views)';
                            }}
                        }}
                    }}
                }},
                scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'sec per card view' }} }} }}
            }}
        }});
    }}

    // 3c. Top-30 product cards table (period toggle only; column-click sorts in place)
    if (DATA.top_products) {{
        let _tpPeriod = 'week';
        const _tpData = () => DATA.top_products[_tpPeriod] || [];

        window.setTopProductsPeriod = function(period, btn) {{
            _tpPeriod = period;
            document.getElementById('tp-period-week').classList.toggle('grain-active', period === 'week');
            document.getElementById('tp-period-4w').classList.toggle('grain-active', period === 'agg_4w');
            renderTopProducts();
        }};
        function renderTopProducts() {{
            const rows = [..._tpData()].sort((a, b) => (b.views || 0) - (a.views || 0)).slice(0, 30);
            const tbody = document.querySelector('#tbl-top-products tbody');
            if (!tbody) return;
            while (tbody.firstChild) tbody.removeChild(tbody.firstChild);
            rows.forEach((r, i) => {{
                const tr = document.createElement('tr');
                const cells = [
                    String(i + 1),
                    r.item_name || r.item_id || '',
                    String(r.views || 0),
                    (r.median_sec || 0) + 's',
                    (r.mean_sec || 0) + 's',
                    String(r.atc || 0),
                    String(r.purchases || 0),
                    (r.cr_atc || 0) + '%',
                ];
                cells.forEach(v => {{ const td = document.createElement('td'); td.textContent = v; tr.appendChild(td); }});
                tbody.appendChild(tr);
            }});
        }}
        renderTopProducts();
    }}

    // 4. Catalog Depth (stacked bar)
    if (A.catalog_depth && A.catalog_depth.length > 0) {{
        const cdPeriods = A.catalog_depth.map(r => r.period);
        new Chart(document.getElementById('analytics-catalog-depth'), {{
            type: 'bar',
            data: {{
                labels: cdPeriods,
                datasets: [
                    {{ label: 'Стр. 1', data: A.catalog_depth.map(r => r.page1), backgroundColor: '#636E72' }},
                    {{ label: 'Стр. 2', data: A.catalog_depth.map(r => r.page2), backgroundColor: '#6C5CE7' }},
                    {{ label: 'Стр. 3', data: A.catalog_depth.map(r => r.page3), backgroundColor: '#0984E3' }},
                    {{ label: 'Стр. 4+', data: A.catalog_depth.map(r => r.page4plus), backgroundColor: '#00B894' }},
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                        anchor: 'center', align: 'center',
                        font: {{ size: 10 }}, color: '#FFF',
                        formatter: v => v > 0 ? v : ''
                    }}
                }},
                scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true, title: {{ display: true, text: 'Сессии' }} }} }}
            }}
        }});
    }}

    }} // end initAnalyticsTab

    // ===== SUMMARY TAB (lazy init — default active) =====
    function initSummaryTab() {{
        const S = DATA.summary;

        // ---- KPI block ----
        function setKpi(id, value, delta, isPP) {{
            const el = document.getElementById(id);
            if (el) el.textContent = value;
            const dEl = document.getElementById(id + '-delta');
            if (dEl && delta != null) {{
                const up = delta > 0;
                const arrow = up ? '↑' : '↓';
                const sign = up ? '+' : '';
                const suffix = isPP ? ' п.п.' : '%';
                const color = up ? 'green' : 'red';
                dEl.textContent = arrow + ' ' + sign + delta + suffix;
                dEl.className = 'delta ' + color;
            }}
        }}
        setKpi('sum-kpi-rps', '$' + S.kpi.revenue_per_session.value, S.kpi.revenue_per_session.delta);
        setKpi('sum-kpi-rev', '$' + S.kpi.revenue.value, S.kpi.revenue.delta);
        setKpi('sum-kpi-atc', S.kpi.atc_rate.value + '%', S.kpi.atc_rate.delta, true);
        setKpi('sum-kpi-pr',  S.kpi.purchase_rate.value + '%', S.kpi.purchase_rate.delta, true);
        setKpi('sum-kpi-c2p', S.kpi.cart_to_purchase.value + '%', S.kpi.cart_to_purchase.delta, true);

        sparkline('sum-spark-atc', S.kpi.atc_rate.trend, '#6C5CE7');
        sparkline('sum-spark-pr',  S.kpi.purchase_rate.trend, '#00B894');

        // ---- Visitors & Sessions (dual axis: line=visitors, bars=sessions) ----
        new Chart(document.getElementById('sum-visitors-sessions'), {{
            type: 'bar',
            data: {{
                labels: S.visitors_sessions.labels,
                datasets: [
                    {{ type: 'bar', label: 'Сессии', data: S.visitors_sessions.sessions,
                       backgroundColor: 'rgba(108,92,231,0.3)', borderColor: '#6C5CE7', yAxisID: 'y' }},
                    {{ type: 'line', label: 'Посетители', data: S.visitors_sessions.visitors,
                       borderColor: '#00B894', borderWidth: 2, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                        anchor: 'end',
                        align: ctx => ctx.dataset.type === 'line' ? 'top' : 'bottom',
                        offset: ctx => ctx.dataset.type === 'line' ? 6 : 6,
                        font: {{ size: 10 }},
                        color: ctx => ctx.dataset.type === 'line' ? '#00B894' : '#6C5CE7',
                        backgroundColor: ctx => ctx.dataset.type === 'line' ? 'rgba(255,255,255,0.9)' : null,
                        borderRadius: 3,
                        padding: ctx => ctx.dataset.type === 'line' ? {{ top: 1, bottom: 1, left: 3, right: 3 }} : 0,
                        formatter: v => v
                    }},
                    tooltip: {{ mode: 'index', intersect: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, grace: '15%', position: 'left', title: {{ display: true, text: 'Сессии' }} }},
                    y1: {{ beginAtZero: true, grace: '20%', position: 'right', title: {{ display: true, text: 'Посетители' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});

        // ---- Device Sessions (stacked bar) ----
        const devColors = {{ mobile: '#6C5CE7', desktop: '#0984E3', tablet: '#FDCB6E' }};
        new Chart(document.getElementById('sum-device-sessions'), {{
            type: 'bar',
            data: {{
                labels: S.device_sessions.labels,
                datasets: ['mobile', 'desktop', 'tablet'].map(dev => ({{
                    label: dev, data: S.device_sessions[dev], backgroundColor: devColors[dev]
                }}))
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        display: ctx => {{
                            const v = ctx.dataset.data[ctx.dataIndex];
                            if (!v || v <= 0) return false;
                            // Only show label if segment is large enough (>= 5% of stack total)
                            const total = ['mobile','desktop','tablet'].reduce((s, d) => s + (S.device_sessions[d][ctx.dataIndex] || 0), 0);
                            return total > 0 && v / total >= 0.05;
                        }},
                        anchor: 'center', align: 'center',
                        font: {{ size: 11, weight: 'bold' }}, color: '#FFF',
                        formatter: v => v > 0 ? v : ''
                    }},
                    tooltip: {{
                        mode: 'index', intersect: false,
                        callbacks: {{
                            label: ctx => {{
                                const total = ['mobile','desktop','tablet'].reduce((s, d) => s + (S.device_sessions[d][ctx.dataIndex] || 0), 0);
                                const pct = total > 0 ? Math.round(ctx.parsed.y / total * 100) : 0;
                                return ctx.dataset.label + ': ' + ctx.parsed.y + ' сес. (' + pct + '%)';
                            }}
                        }}
                    }}
                }},
                scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }}
            }}
        }});

        // ---- New vs Returning ----
        new Chart(document.getElementById('sum-new-returning'), {{
            type: 'line',
            data: {{
                labels: S.new_returning.labels,
                datasets: [
                    {{ label: 'Новые', data: S.new_returning.new, borderColor: '#0984E3', borderWidth: 2, tension: 0.3, _align: 'top' }},
                    {{ label: 'Вернувшиеся', data: S.new_returning.returning, borderColor: '#6C5CE7', borderWidth: 2, tension: 0.3, _align: 'bottom' }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                        anchor: 'end', align: ctx => ctx.dataset._align, offset: 4,
                        font: {{ size: 10 }},
                        color: ctx => ctx.dataset.borderColor,
                        formatter: v => v > 0 ? v : ''
                    }},
                    tooltip: {{ mode: 'index', intersect: false,
                        callbacks: {{
                            label: ctx => {{
                                const total = (S.new_returning.new[ctx.dataIndex] || 0) + (S.new_returning.returning[ctx.dataIndex] || 0);
                                const pct = total > 0 ? Math.round(ctx.parsed.y / total * 100) : 0;
                                return ctx.dataset.label + ': ' + ctx.parsed.y + ' (' + pct + '%)';
                            }}
                        }}
                    }}
                }},
                scales: {{ y: {{ beginAtZero: true, grace: '15%' }} }}
            }}
        }});

        // ---- Time on Site per device (median) ----
        new Chart(document.getElementById('sum-time-on-site'), {{
            type: 'line',
            data: {{
                labels: S.time_on_site.labels,
                datasets: ['mobile','desktop','tablet'].map((dev, i) => ({{
                    label: dev, data: S.time_on_site[dev], borderColor: devColors[dev], borderWidth: 2, tension: 0.3,
                    _align: i === 0 ? 'top' : (i === 1 ? 'bottom' : 'right')
                }}))
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                        anchor: 'end',
                        align: ctx => ctx.dataset._align || 'top',
                        offset: 4,
                        font: {{ size: 10 }},
                        color: ctx => ctx.dataset.borderColor,
                        formatter: v => v > 0 ? v + 's' : ''
                    }},
                    tooltip: {{ mode: 'index', intersect: false,
                        callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + 's (median)' }} }}
                }},
                scales: {{ y: {{ beginAtZero: true, grace: '15%', title: {{ display: true, text: 'median sec' }} }} }}
            }}
        }});

        // ---- Bounce Rate per device ----
        new Chart(document.getElementById('sum-bounce-device'), {{
            type: 'line',
            data: {{
                labels: S.bounce_device.labels,
                datasets: ['mobile','desktop','tablet'].map((dev, i) => ({{
                    label: dev, data: S.bounce_device[dev], borderColor: devColors[dev], borderWidth: 2, tension: 0.3,
                    _align: i === 0 ? 'top' : (i === 1 ? 'bottom' : 'right')
                }}))
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                        anchor: 'end',
                        align: ctx => ctx.dataset._align || 'top',
                        offset: 4,
                        font: {{ size: 10 }},
                        color: ctx => ctx.dataset.borderColor,
                        formatter: v => v > 0 ? v + '%' : ''
                    }},
                    tooltip: {{ mode: 'index', intersect: false,
                        callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + '%' }} }}
                }},
                scales: {{ y: {{ beginAtZero: true, grace: '15%', ticks: {{ callback: v => v + '%' }} }} }}
            }}
        }});

        // ---- Source trend (multi-line with session counts) ----
        const srcColors = {{ Social: '#6C5CE7', Paid: '#00B894', Direct: '#636E72', Organic: '#0984E3', Referral: '#FDCB6E' }};
        new Chart(document.getElementById('sum-source-trend'), {{
            type: 'line',
            data: {{
                labels: S.source_trend.labels,
                datasets: S.source_trend.sources.map((src, i) => ({{
                    label: src.name, data: src.sessions,
                    borderColor: srcColors[src.name] || '#999', borderWidth: 2, tension: 0.3,
                    _share: src.share_pct,
                    _align: ['top','bottom','right','left','top'][i] || 'top'
                }}))
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{
                        display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                        anchor: 'end',
                        align: ctx => ctx.dataset._align || 'top',
                        offset: 4,
                        font: {{ size: 10 }},
                        color: ctx => ctx.dataset.borderColor,
                        formatter: v => v > 0 ? v : ''
                    }},
                    tooltip: {{ mode: 'index', intersect: false,
                        callbacks: {{
                            label: ctx => {{
                                const share = ctx.dataset._share ? ctx.dataset._share[ctx.dataIndex] : 0;
                                return ctx.dataset.label + ': ' + ctx.parsed.y + ' сес. (' + share + '%)';
                            }}
                        }}
                    }}
                }},
                scales: {{ y: {{ beginAtZero: true, grace: '15%' }} }}
            }}
        }});

        // ---- ATC + PR dual axis ----
        new Chart(document.getElementById('sum-atc-pr-trend'), {{
            type: 'line',
            data: {{
                labels: S.atc_pr_trend.labels,
                datasets: [
                    {{ label: 'ATC Rate', data: S.atc_pr_trend.atc_rate, borderColor: '#6C5CE7', borderWidth: 2, tension: 0.3, yAxisID: 'y' }},
                    {{ label: 'Purchase Rate', data: S.atc_pr_trend.purchase_rate, borderColor: '#00B894', borderWidth: 2, tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, position: 'left', title: {{ display: true, text: 'ATC Rate %', color: '#6C5CE7' }}, ticks: {{ callback: v => v + '%', color: '#6C5CE7' }} }},
                    y1: {{ beginAtZero: true, position: 'right', title: {{ display: true, text: 'Purchase Rate %', color: '#00B894' }}, ticks: {{ callback: v => v + '%', color: '#00B894' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});

        // ---- Tables (source + country) ----
        function deltaBadge(delta, deltaType) {{
            if (delta == null) return '';
            const up = delta > 0;
            const arrow = up ? '↑' : '↓';
            const sign = up ? '+' : '';
            const suffix = deltaType === 'pp' ? ' п.п.' : '%';
            const color = up ? '#00B894' : '#E17055';
            return '<span style="font-size:10px; color:' + color + '; margin-left:4px;">' + arrow + sign + delta + suffix + '</span>';
        }}

        function cellVal(metric, unit) {{
            if (!metric) return '';
            const val = metric.value != null ? metric.value : 0;
            return val + (unit || '') + deltaBadge(metric.delta, metric.delta_type);
        }}

        function renderRow(r) {{
            return '<tr>' +
                '<td><b>' + r.name + '</b></td>' +
                '<td>' + cellVal(r.users) + '</td>' +
                '<td>' + cellVal(r.sessions) + '</td>' +
                '<td>' + cellVal(r.new_users) + '</td>' +
                '<td>' + cellVal(r.returning_users) + '</td>' +
                '<td>' + cellVal(r.er, '%') + '</td>' +
                '<td>' + cellVal(r.bounce_rate, '%') + '</td>' +
                '<td>' + cellVal(r.median_eng_sec, 's') + '</td>' +
                '<td>' + cellVal(r.avg_pages) + '</td>' +
                '<td>' + cellVal(r.atc_rate, '%') + '</td>' +
                '<td>' + cellVal(r.cr, '%') + '</td>' +
            '</tr>';
        }}

        const srcTbody = document.querySelector('#sum-source-table tbody');
        srcTbody.innerHTML = S.source_table.map(renderRow).join('');

        const countryTbody = document.querySelector('#sum-country-table tbody');
        countryTbody.innerHTML = S.country_table.map(r => {{
            const flagName = (COUNTRY_FLAGS[r.name] || '🏳️') + ' ' + r.name;
            return '<tr>' +
                '<td><b>' + flagName + '</b></td>' +
                '<td>' + cellVal(r.users) + '</td>' +
                '<td>' + cellVal(r.sessions) + '</td>' +
                '<td>' + cellVal(r.new_users) + '</td>' +
                '<td>' + cellVal(r.returning_users) + '</td>' +
                '<td>' + cellVal(r.er, '%') + '</td>' +
                '<td>' + cellVal(r.bounce_rate, '%') + '</td>' +
                '<td>' + cellVal(r.median_eng_sec, 's') + '</td>' +
                '<td>' + cellVal(r.avg_pages) + '</td>' +
                '<td>' + cellVal(r.atc_rate, '%') + '</td>' +
                '<td>' + cellVal(r.cr, '%') + '</td>' +
            '</tr>';
        }}).join('');

        // ---- Rankings ----
        document.getElementById('sum-ranking-atc').innerHTML = S.ranking_atc.map(r =>
            '<tr><td>' + r.source + '</td><td>' + r.country + '</td><td>' + r.user_type + '</td><td>' + r.sessions + '</td><td><b>' + r.atc_rate + '%</b></td></tr>'
        ).join('');
        document.getElementById('sum-ranking-pr').innerHTML = S.ranking_pr.map(r =>
            '<tr><td>' + r.source + '</td><td>' + r.country + '</td><td>' + r.user_type + '</td><td>' + r.sessions + '</td><td><b>' + r.purchase_rate + '%</b></td></tr>'
        ).join('');

        // ---- Scroll Rate (site-wide) — by device + by channel ----
        const A = DATA.analytics;
        if (A && A.scroll && A.scroll.length > 0) {{
            const scrollChannels = ['Social', 'Paid', 'Direct', 'Organic', 'Referral'];
            const chColors = {{ Social: '#6C5CE7', Paid: '#00B894', Direct: '#636E72', Organic: '#0984E3', Referral: '#FDCB6E' }};
            const devColors = {{ mobile: '#6C5CE7', desktop: '#00B894' }};
            const lineOpts = {{
                responsive: true, interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    legend: {{ position: 'top' }},
                    datalabels: {{ display: false }},
                    tooltip: {{ mode: 'index', intersect: false, callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + '%' }} }}
                }},
                scales: {{ y: {{ beginAtZero: true, max: 100, ticks: {{ callback: v => v + '%' }} }} }}
            }};
            const cvSiteDev = document.getElementById('sum-scroll-site-device');
            if (cvSiteDev) new Chart(cvSiteDev, {{
                type: 'line',
                data: {{
                    labels: DATA.periods,
                    datasets: ['mobile', 'desktop'].map(dev => ({{
                        label: dev === 'mobile' ? 'Мобилка' : 'Десктоп',
                        data: DATA.periods.map(p => scrollByDev(p, dev, 'site')),
                        borderColor: devColors[dev], tension: 0.3, borderWidth: 2, pointRadius: 3,
                    }}))
                }},
                options: lineOpts
            }});
            const cvSiteCh = document.getElementById('sum-scroll-site-channel');
            if (cvSiteCh) new Chart(cvSiteCh, {{
                type: 'line',
                data: {{
                    labels: DATA.periods,
                    datasets: scrollChannels.map(ch => ({{
                        label: ch,
                        data: DATA.periods.map(p => scrollByCh(p, ch, 'site')),
                        borderColor: chColors[ch], tension: 0.3, borderWidth: 2, pointRadius: 3,
                    }}))
                }},
                options: lineOpts
            }});
        }}

        // ---- Cohort Retention ----
        if (A && A.cohort && A.cohort.length > 0) {{
            const cohorts = {{}};
            A.cohort.forEach(r => {{
                if (!cohorts[r.cohort_week]) cohorts[r.cohort_week] = {{}};
                cohorts[r.cohort_week][r.weeks_since] = r.users;
            }});
            const cohortWeeks = Object.keys(cohorts).sort();
            const cohortLabels = cohortWeeks.map(w => w.replace('2026-', ''));
            const maxWeeksSince = 8;
            const retentionData = [];
            for (let ws = 0; ws <= maxWeeksSince; ws++) {{
                retentionData.push({{
                    label: ws === 0 ? 'Неделя 0 (размер когорты)' : '+' + ws + ' нед.',
                    data: cohortWeeks.map(cw => {{
                        const week0 = cohorts[cw][0] || 1;
                        const weekN = cohorts[cw][ws] || 0;
                        return ws === 0 ? week0 : Math.round(weekN / week0 * 100);
                    }}),
                    backgroundColor: ws === 0 ? '#2D3436' : [
                        '#6C5CE7', '#0984E3', '#00B894', '#FDCB6E',
                        '#E17055', '#636E72', '#B2BEC3', '#DFE6E9'
                    ][ws - 1],
                    hidden: ws === 0,
                }});
            }}

            const cvCohort = document.getElementById('sum-cohort');
            if (cvCohort) new Chart(cvCohort, {{
                type: 'bar',
                data: {{ labels: cohortLabels, datasets: retentionData }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'top' }},
                        datalabels: {{
                            display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                            anchor: 'end', align: 'top', clamp: true,
                            font: {{ size: 10, weight: 'bold' }}, color: '#2D3436',
                            formatter: (v, ctx) => {{
                                if (ctx.datasetIndex === 0) return v;
                                return v > 0 ? v + '%' : '';
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ title: {{ display: true, text: 'Когорта (неделя первого визита)' }} }},
                        y: {{ beginAtZero: true, suggestedMax: 30, ticks: {{ callback: v => v + '%' }}, title: {{ display: true, text: '% возврата' }} }}
                    }}
                }}
            }});
        }}
    }}

    // Country flags map for JS use in summary country table
    const COUNTRY_FLAGS = {json.dumps(COUNTRY_FLAGS, ensure_ascii=False)};

    // Auto-init Summary (default active tab)
    tabInited.summary = true;
    initSummaryTab();

    </script>
    </div><!-- end main-container -->
</body>
</html>"""


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Pinkspink Analytics Report Generator")
    parser.add_argument("--grain", choices=["day", "week", "month", "all"], default="week")
    parser.add_argument("--output", default=OUTPUT_FILE)
    parser.add_argument("--styleguide", action="store_true", help="Generate styleguide.html only (skip data fetch)")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(args.output))

    if args.styleguide:
        out = os.path.join(base_dir, "styleguide.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(generate_styleguide(TOKENS))
        print(f"  ✓ Styleguide saved to {out}")
        print(f"  Open in browser: file://{os.path.abspath(out)}")
        return

    client = get_client()

    if args.grain == "all":
        for g in ["day", "week", "month"]:
            print(f"Pinkspink Analytics — Generating report ({g})")
            rows = fetch_session_data(client, g)
            analytics = fetch_analytics_data(client, g)
            html = generate_html(rows, g, EXCLUDED_COUNTRIES_DEFAULT, analytics)
            out = os.path.join(base_dir, f"report_{g}.html")
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  ✓ {out}")
        print(f"\n  Open: file://{os.path.join(base_dir, 'report_week.html')}")
    else:
        print(f"Pinkspink Analytics — Generating report ({args.grain})")
        rows = fetch_session_data(client, args.grain)
        analytics = fetch_analytics_data(client, args.grain)
        html = generate_html(rows, args.grain, EXCLUDED_COUNTRIES_DEFAULT, analytics)
        out = os.path.join(base_dir, f"report_{args.grain}.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ Report saved to {out}")
        print(f"  Open in browser: file://{os.path.abspath(out)}")


if __name__ == "__main__":
    main()
