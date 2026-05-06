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
from datetime import datetime, timedelta, date

from google.cloud import bigquery
from google.oauth2.service_account import Credentials

# ============================================================
# CONFIG
# ============================================================

BQ_PROJECT = "claude-code-486108"
BQ_DATASET = "analytics_411715710"
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_account.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.html")

# First date present in BigQuery export (used to gate the month grain UI button until enough data accumulates).
DATA_START_DATE = date(2026, 2, 5)
MONTH_GRAIN_MIN_FULL_MONTHS = 4

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
            "kpi":        "28px",
            "h2":         "18px",
            "h3":         "14px",
            "body":       "13px",
            "caption":    "11px",
            "chart-meta": "10px",
        },
        "weight": {
            "regular":  "400",
            "semibold": "600",
            "bold":     "700",
        },
        "letter": {
            "label": "0.5px",
        },
        # v1.1 — heading spacing (margin-top заголовка = floor_even(percent × font-size))
        "heading_spacing": {
            "mt-h2":       "44px",   # 250% × 18 = 45 → 44
            "mt-h3":       "24px",   # 175% × 14 = 24.5 → 24
            "mt-h4":       "16px",   # 125% × 13 = 16.25 → 16
            "tight-pair":  "4px",    # h2/h3/h4 + .meta
            "content-gap": "8px",    # .meta → table/grid/chart
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
    # Controls v1.0 — единая высота и радиус для filter-кнопок, square-toggle и checkbox
    "control": {
        "h": "28px",
        "r": "2px",
    },
    # Tables v1.0 — auto-fit до 20 строк, sticky-header при превышении
    "table": {
        "row-h-table":     "28px",
        "max-rows-table":  "20",
        "max-h-table":     "calc(var(--row-h-table) * (var(--max-rows-table) + 1))",
    },
    "chart": {
        "axis_color":               "#636E72",
        "axis_label_size":          10,
        "grid_color":               "rgba(0,0,0,0.06)",
        "datalabel_size":           11,
        "datalabel_color_on_light": "#2D3436",
        "datalabel_color_on_dark":  "#FFFFFF",
        "legend_size":              10,
    },
    "chart_height": {
        "xs": "60px",
        "sm": "180px",
        "md": "280px",
        "lg": "360px",
    },
}


def chart_defaults_js(tokens=TOKENS):
    """Generate Chart.defaults + helpers (v1.0). Emit ONCE per page, before any new Chart(...) call."""
    c = tokens["chart"]
    return f"""
    // === Chart.js global setup (Charts v1.0) ===
    Chart.register(ChartDataLabels);
    Chart.defaults.animation = false;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.responsive = true;

    Chart.defaults.font.family = {tokens['type']['family']!r};
    Chart.defaults.font.size   = {c['axis_label_size']};
    Chart.defaults.color       = {c['axis_color']!r};
    Chart.defaults.borderColor = {c['grid_color']!r};
    Chart.defaults.scale.grid.color  = {c['grid_color']!r};
    Chart.defaults.scale.ticks.color = {c['axis_color']!r};

    Chart.defaults.plugins.legend.labels.font      = {{ size: {c['legend_size']} }};
    Chart.defaults.plugins.legend.labels.boxWidth  = 10;
    Chart.defaults.plugins.legend.labels.boxHeight = 10;
    Chart.defaults.plugins.legend.labels.padding   = 12;

    Chart.defaults.plugins.datalabels       = Chart.defaults.plugins.datalabels || {{}};
    Chart.defaults.plugins.datalabels.font  = {{ size: {c['datalabel_size']} }};
    Chart.defaults.plugins.datalabels.color = {c['datalabel_color_on_light']!r};

    // Hover: показать значения ВСЕХ датасетов в этой x-позиции (override per-chart для bubble)
    Chart.defaults.interaction = {{ mode: 'index', intersect: false }};

    // === Helpers (Charts v1.0) ===
    const cssvar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

    const fmt = {{
        num: v => (v == null || v === 0) ? '' : v.toLocaleString('ru-RU'),
        pct: (v, dec=1) => (v == null || v === 0) ? '' : v.toFixed(dec) + '%',
        sec: v => (v == null || v === 0) ? '' : v + 's',
        cur: (v, c='$') => (v == null || v === 0) ? '' : c + v.toLocaleString('ru-RU')
    }};

    const dlPad = {{
        backgroundColor: 'rgba(255,255,255,0.85)',
        borderRadius: 3,
        padding: {{ top: 1, bottom: 1, left: 4, right: 4 }}
    }};

    function legendLabels(chart) {{
        return chart.data.datasets.map((ds, i) => {{
            const isLine = (ds.type === 'line') || (chart.config.type === 'line' && !ds.type);
            const color = ds.borderColor || ds.backgroundColor;
            return {{
                text: ds.label, fillStyle: color, strokeStyle: color,
                lineWidth: isLine ? 2 : 0,
                pointStyle: isLine ? 'line' : (chart.config.type === 'bubble' ? 'circle' : 'rect'),
                hidden: !chart.isDatasetVisible(i),
                datasetIndex: i
            }};
        }});
    }}

    const legendPresets = {{
        bar:    {{ display: true, position: 'top', align: 'start', labels: {{ usePointStyle: true, pointStyle: 'rect',   boxWidth: 10, boxHeight: 10, padding: 12 }} }},
        line:   {{ display: true, position: 'top', align: 'start', labels: {{ boxWidth: 32, boxHeight: 2, padding: 12, generateLabels: legendLabels }} }},
        bubble: {{ display: true, position: 'top', align: 'start', labels: {{ usePointStyle: true, pointStyle: 'circle', boxWidth: 10, boxHeight: 10, padding: 12 }} }},
        mixed:  {{ display: true, position: 'top', align: 'start', labels: {{ boxWidth: 14, boxHeight: 8, padding: 12, generateLabels: legendLabels }} }},
        none:   {{ display: false }}
    }};

    const dlPresets = {{
        barTop:    {{ anchor: 'end',    align: 'top',    color: cssvar('--tx-primary') }},
        barCenter: {{ anchor: 'center', align: 'center', color: cssvar('--tx-ondark')  }},
        line:      {{ align: 'top',                       color: cssvar('--tx-primary'), ...dlPad }},
        off:       {{ display: false }}
    }};
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
    for k, v in tokens["type"].get("heading_spacing", {}).items():
        lines.append(f"    --{k}: {v};")
    for k, v in tokens["space"].items():
        lines.append(f"    --sp-{k}: {v};")
    for k, v in tokens["radius"].items():
        lines.append(f"    --r-{k}: {v};")
    for k, v in tokens["shadow"].items():
        lines.append(f"    --sh-{k}: {v};")
    for k, v in tokens.get("control", {}).items():
        lines.append(f"    --{k}-control: {v};")
    for k, v in tokens.get("table", {}).items():
        lines.append(f"    --{k}: {v};")
    for k, v in tokens.get("chart_height", {}).items():
        lines.append(f"    --ch-{k}: {v};")
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
            "where":    "Default-фон <code>.btn</code>, <code>.btn-sq</code>, <code>.kpi-spark</code>, фон спарклайнов",
            "text":     "secondary",
            "contains": "Кнопки в неактивном состоянии, мини-графики",
            "demo":     '<button class="btn" style="background:var(--bg-muted)">.btn</button>',
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
            "where":    "Бордер <code>.sticky-header</code>, hover у <code>.btn-sq</code>",
            "text":     "secondary",
            "contains": "Тонкие линии-разделители крупных областей",
            "demo":     '<div style="background:var(--bg-card);border:1px solid var(--bg-border);border-radius:var(--r-md);padding:6px var(--sp-2);font-size:var(--fs-caption)">card · 1px solid border</div>',
        },
        "divider": {
            "where":    "<code>border-bottom</code> в строках таблицы и <code>.country-row</code>",
            "text":     "secondary",
            "contains": "Очень тонкие разделители <em>внутри</em> блоков",
            "demo":     '<div style="font-size:var(--fs-caption)">Row 1</div><div style="border-top:1px solid var(--bg-divider);font-size:var(--fs-caption);padding-top:4px">Row 2</div>',
        },
        "inverse": {
            "where":    "Тёмные <code>&lt;th&gt;</code>, <code>.btn.is-active</code>, <code>.btn-sq.is-active</code>",
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
        "secondary": ".meta, h4, .btn, .header-meta",
        "muted":     ".agg-tag, .kpi-bench, .empty-row, scrollbar",
        "ondark":    "Текст на тёмных кнопках, на <code>&lt;th&gt;</code>",
    }
    NATIVE_WEIGHT = {
        "kpi":        ("bold", 700),
        "h2":         ("semibold", 600),
        "h3":         ("semibold", 600),
        "body":       ("regular", 400),
        "caption":    ("regular", 400),
        "chart-meta": ("regular", 400),
    }
    TYPE_USAGE = {
        "kpi":        "KPI value в .kpi-value (2×2) и .kpi-grid",
        "h2":         "Заголовки секций, бренд в шапке, .metric .value",
        "h3":         "Заголовки блоков внутри карточек (.block)",
        "body":       "Body, h4, .meta, .filters label, .btn, .delta, .country-row",
        "caption":    "<th>/<td>, .kpi-label, .kpi-bench, .header-meta, .agg-tag, datalabels",
        "chart-meta": "Подписи делений осей и легенда на графиках, .delta-sm",
    }
    SPACE_USAGE = {
        "1": "Мелкие зазоры: gap у .tab-bar, padding-y в .btn-sq, margin у .agg-tag",
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

        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: inherit; }}
        body {{ font-family: var(--ff-mono); background: var(--bg-page); color: var(--tx-primary); padding: var(--sp-5); }}
        h1 {{ font-size: var(--fs-kpi); font-weight: var(--fw-bold); margin-bottom: var(--sp-2); }}
        h2 {{ font-size: var(--fs-h2); font-weight: var(--fw-semibold); margin: var(--sp-6) 0 var(--sp-3); padding-bottom: 6px; border-bottom: 2px solid var(--bg-inverse); }}
        .sub {{ color: var(--tx-secondary); font-size: var(--fs-body); margin-bottom: var(--sp-5); }}
        code {{ font-family: var(--ff-mono); font-size: var(--fs-caption); background: var(--bg-muted); padding: 1px 4px; border-radius: var(--r-sm); }}
        .meta {{ color: var(--tx-secondary); font-size: var(--fs-caption); }}

        /* Color swatches */
        .sw-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--sp-3); margin-bottom: var(--sp-4); }}
        .sw {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); overflow: hidden; }}
        .sw-color {{ height: 60px; }}
        .sw-name {{ padding: var(--sp-2) var(--sp-3) 0; font-size: var(--fs-caption); font-weight: var(--fw-bold); }}
        .sw-val {{ padding: 0 var(--sp-3) 2px; font-size: var(--fs-caption); color: var(--tx-secondary); }}
        .sw-use {{ padding: 0 var(--sp-3) var(--sp-3); font-size: var(--fs-caption); color: var(--tx-secondary); line-height: 1.4; }}
        .sw-use code {{ font-size: var(--fs-caption); padding: 0 2px; }}

        /* Buttons demo (Controls v1.0: .btn / .tab / .btn-sq + .is-active) */
        .btn-row {{ display: flex; gap: var(--sp-2); flex-wrap: wrap; align-items: center; padding: var(--sp-3); background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); margin-bottom: var(--sp-3); }}
        .btn-row .label {{ font-size: var(--fs-caption); color: var(--tx-secondary); margin-right: var(--sp-3); min-width: 140px; }}
        .btn {{ height: var(--h-control); padding: 0 var(--sp-3); border-radius: var(--r-control); font-size: var(--fs-body); color: var(--tx-secondary); background: var(--bg-muted); border: none; cursor: pointer; line-height: 1; }}
        .btn.is-hover {{ background: var(--bg-border); }}
        .btn.is-active {{ background: var(--bg-inverse); color: var(--tx-ondark); }}
        .tab {{ padding: var(--sp-2) var(--sp-3) var(--sp-1); font-size: var(--fs-body); border: none; border-bottom: 2px solid transparent; background: transparent; cursor: pointer; color: var(--tx-secondary); line-height: 1.4; }}
        .tab.is-hover {{ color: var(--tx-secondary); }}
        .tab.is-active {{ color: var(--tx-primary); border-bottom-color: var(--tx-primary); font-weight: var(--fw-semibold); }}
        .btn-sq {{ width: var(--h-control); height: var(--h-control); display: inline-flex; align-items: center; justify-content: center; font-size: var(--fs-body); font-weight: var(--fw-semibold); background: var(--bg-muted); color: var(--tx-secondary); border-radius: var(--r-control); }}
        .btn-sq.is-hover {{ background: var(--bg-border); }}
        .btn-sq.is-active {{ background: var(--bg-inverse); color: var(--tx-ondark); }}
        .bubble-filters-demo {{ display: flex; flex-wrap: wrap; gap: var(--sp-2); padding: var(--sp-2) var(--sp-3); background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); }}
        .bubble-filters-demo label {{ font-size: var(--fs-caption); display: flex; align-items: center; gap: var(--sp-1); }}

        /* Typography rows */
        .ty-row {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); padding: var(--sp-3) var(--sp-4); margin-bottom: var(--sp-2); display: flex; align-items: center; justify-content: space-between; gap: var(--sp-4); flex-wrap: wrap; }}
        .ty-meta {{ color: var(--tx-secondary); font-size: var(--fs-caption); text-align: right; }}
        .ty-use {{ font-size: var(--fs-caption); margin-top: 2px; opacity: 0.85; }}

        /* Spacing rows */
        .sp-row {{ display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-2); padding: var(--sp-2) var(--sp-3); background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); }}
        .sp-bar {{ height: 16px; border-radius: var(--r-sm); flex-shrink: 0; }}
        .sp-use {{ font-size: var(--fs-caption); color: var(--tx-secondary); margin-left: var(--sp-2); }}

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
        .sem-tag {{ padding: var(--sp-1) var(--sp-3); border-radius: var(--r-pill); font-size: var(--fs-caption); font-weight: var(--fw-semibold); }}
        .sem-tag.growth   {{ background: var(--c-growth);    color: var(--tx-ondark); }}
        .sem-tag.decline  {{ background: var(--c-decline);   color: var(--tx-ondark); }}
        .sem-tag.neutral  {{ background: var(--c-neutral);   color: var(--tx-ondark); }}
        .sem-tag.highlight{{ background: var(--c-highlight); color: var(--tx-ondark); }}

        /* Data tables */
        .data-table {{ width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: var(--r-xl); overflow: hidden; box-shadow: var(--sh-card); }}
        .data-table th {{ background: var(--bg-inverse); color: var(--tx-ondark); padding: var(--sp-2) var(--sp-3); font-size: var(--fs-caption); text-align: left; font-weight: var(--fw-semibold); }}
        .data-table td {{ padding: 6px var(--sp-3); font-size: var(--fs-caption); border-bottom: 1px solid var(--bg-divider); }}
        .data-table tr:hover {{ background: var(--bg-hover); }}
        .data-table .highlight {{ font-weight: var(--fw-bold); color: var(--c-highlight); }}

        /* KPI demo */
        .kpi-demo {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--sp-3); }}
        .cell-kpi {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); padding: var(--sp-3); display: flex; flex-direction: column; }}
        .kpi-label {{ font-size: var(--fs-caption); text-transform: uppercase; color: var(--tx-secondary); letter-spacing: var(--ls-label); }}
        .kpi-value {{ font-size: var(--fs-kpi); font-weight: var(--fw-bold); margin: var(--sp-1) 0; }}
        .kpi-value-sm {{ font-size: var(--fs-h2); font-weight: var(--fw-bold); line-height: 1.1; margin: var(--sp-1) 0; }}
        .kpi-bench {{ font-size: var(--fs-caption); color: var(--tx-muted); }}
        .kpi-spark {{ background: var(--bg-muted); border-radius: var(--r-lg); margin-top: var(--sp-2); padding: var(--sp-1); flex: 1; min-height: 50px; }}

        /* KPI grid block (Сводка) */
        .kpi-grid-demo {{ display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(4, 70px); gap: var(--sp-2); max-width: 460px; }}
        .kpi-grid-demo .kg {{ padding: var(--sp-2) var(--sp-3); }}
        .kpi-grid-demo .kg .kpi-label {{ font-size: var(--fs-caption); }}
        .kg-rps {{ grid-column: 1; grid-row: 1; }}
        .kg-rev {{ grid-column: 2; grid-row: 1; }}
        .kg-atc {{ grid-column: 1; grid-row: 2 / span 2; }}
        .kg-pr  {{ grid-column: 2; grid-row: 2 / span 2; }}
        .kg-c2p {{ grid-column: 1 / span 2; grid-row: 4; }}

        /* Chart preview */
        .chart-wrap {{ position: relative; width: 100%; height: var(--ch-lg); background: var(--bg-card); border-radius: var(--r-xl); padding: var(--sp-3); box-shadow: var(--sh-card); margin-bottom: var(--sp-4); }}

        /* Surfaces — detailed cards */
        .surf-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: var(--sp-3); margin-bottom: var(--sp-4); }}
        .surf-card {{ background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); overflow: hidden; }}
        .surf-demo {{ height: 130px; padding: var(--sp-3); position: relative; display: flex; flex-direction: column; gap: var(--sp-1); justify-content: center; align-items: center; }}
        .surf-demo .demo-text {{ font-size: var(--fs-body); }}
        .surf-demo .demo-meta {{ font-size: var(--fs-caption); }}
        .surf-demo .mini-card {{ background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); padding: var(--sp-2) var(--sp-3); font-size: var(--fs-caption); color: var(--tx-primary); }}
        .surf-demo .mini-row {{ background: var(--bg-hover); border-radius: var(--r-sm); padding: 4px var(--sp-2); font-size: var(--fs-caption); color: var(--tx-primary); }}
        .surf-demo .mini-th {{ background: var(--bg-inverse); color: var(--tx-ondark); border-radius: var(--r-sm); padding: 4px var(--sp-2); font-size: var(--fs-caption); font-weight: var(--fw-semibold); }}
        .surf-name {{ padding: var(--sp-2) var(--sp-3); font-size: var(--fs-caption); font-weight: var(--fw-bold); border-top: 1px solid var(--bg-divider); display: flex; justify-content: space-between; align-items: baseline; }}
        .surf-name .hex {{ color: var(--tx-secondary); font-weight: var(--fw-regular); }}
        .surf-meta {{ padding: var(--sp-2) var(--sp-3) var(--sp-3); font-size: var(--fs-caption); }}
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
    <p class="sub">Три типа кнопок в дашборде: <code>.btn</code> (фильтры), <code>.tab</code> (вкладки навигации), <code>.btn-sq</code> (квадратные day/W/M в шапке). Активное состояние — <code>.is-active</code>.</p>

    <div class="btn-row">
        <span class="label"><code>.btn</code></span>
        <button class="btn">default</button>
        <button class="btn is-hover">hover</button>
        <button class="btn is-active">active</button>
    </div>
    <div class="btn-row">
        <span class="label"><code>.tab</code></span>
        <button class="tab">default</button>
        <button class="tab is-hover">hover</button>
        <button class="tab is-active">active</button>
    </div>
    <div class="btn-row">
        <span class="label"><code>.btn-sq</code></span>
        <span class="btn-sq">D</span>
        <span class="btn-sq is-hover">W</span>
        <span class="btn-sq is-active">M</span>
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
    <div class="data-table-wrap"><table class="data-table">
        <thead><tr><th>Канал</th><th>Сессии</th><th>ATC</th><th>Конверсия</th></tr></thead>
        <tbody>
            <tr><td>Social</td><td>1 234</td><td>56</td><td class="highlight">4.5%</td></tr>
            <tr><td>Paid</td><td>342</td><td>3</td><td>0.9%</td></tr>
            <tr><td>Direct</td><td>523</td><td>21</td><td class="highlight">4.0%</td></tr>
        </tbody>
    </table></div>

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
        <div class="cell-kpi kg kg-atc"><div class="kpi-label">ATC</div><div class="kpi-value-sm">2.1%</div><div class="kpi-bench" style="font-size:var(--fs-caption)">vs 4w: <span style="color:var(--c-growth)">+0.3pp</span></div></div>
        <div class="cell-kpi kg kg-pr"><div class="kpi-label">Покупки</div><div class="kpi-value-sm">0.3%</div><div class="kpi-bench" style="font-size:var(--fs-caption)">vs 4w: <span style="color:var(--c-decline)">−0.1pp</span></div></div>
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
        start = datetime.combine(DATA_START_DATE, datetime.min.time())
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def count_full_months_available(today=None, data_start=DATA_START_DATE):
    """Count complete calendar months strictly between data_start and today.

    A month counts as full only if it lies entirely within the data window:
    the start month is excluded when data_start.day > 1, and the current
    month is always excluded (it is dropped as incomplete elsewhere).
    """
    if today is None:
        today = date.today()
    # First full month: next month if data starts mid-month, else the start month itself
    if data_start.day == 1:
        first_full_year, first_full_month = data_start.year, data_start.month
    elif data_start.month == 12:
        first_full_year, first_full_month = data_start.year + 1, 1
    else:
        first_full_year, first_full_month = data_start.year, data_start.month + 1
    # Last full month: month before today's month (today's own month is incomplete)
    if today.month == 1:
        last_full_year, last_full_month = today.year - 1, 12
    else:
        last_full_year, last_full_month = today.year, today.month - 1
    diff = (last_full_year - first_full_year) * 12 + (last_full_month - first_full_month) + 1
    return max(0, diff)


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
            device.category AS device,
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
        SELECT period, device, user_pseudo_id, session_id, MAX(page_num) AS max_page
        FROM catalog_views
        GROUP BY period, device, user_pseudo_id, session_id
    )
    SELECT
        period, device,
        COUNT(*) AS sessions,
        COUNTIF(max_page = 1) AS page1,
        COUNTIF(max_page = 2) AS page2,
        COUNTIF(max_page = 3) AS page3,
        COUNTIF(max_page >= 4) AS page4plus
    FROM session_max
    GROUP BY period, device
    ORDER BY period, device
    """
    catalog_rows = list(client.query(sql_catalog).result())
    analytics["catalog_depth"] = [dict(r) for r in catalog_rows]

    # 4. Cohort retention (by week of first visit)
    print("  Fetching cohort retention...")
    # Device label captured from the very first session of each user. Cohort retention
    # is then partitioned by that device, so the filter shows "users who started on X".
    sql_cohort = f"""
    WITH first_visits AS (
        SELECT
            user_pseudo_id,
            MIN(PARSE_DATE('%Y%m%d', event_date)) AS first_date,
            ANY_VALUE(device.category) AS device
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '20260205' AND '{end}'
            AND event_name = 'first_visit'
        GROUP BY user_pseudo_id
    ),
    returns AS (
        SELECT DISTINCT
            fv.user_pseudo_id,
            fv.device,
            FORMAT_DATE('%G-W%V', fv.first_date) AS cohort_week,
            DATE_DIFF(PARSE_DATE('%Y%m%d', e.event_date), fv.first_date, WEEK) AS weeks_since
        FROM first_visits fv
        JOIN `{BQ_PROJECT}.{BQ_DATASET}.events_*` e
            ON fv.user_pseudo_id = e.user_pseudo_id
        WHERE e._TABLE_SUFFIX BETWEEN '20260205' AND '{end}'
            AND e.event_name = 'session_start'
    )
    SELECT cohort_week, device, weeks_since, COUNT(DISTINCT user_pseudo_id) AS users
    FROM returns
    WHERE weeks_since BETWEEN 0 AND 8
    GROUP BY cohort_week, device, weeks_since
    ORDER BY cohort_week, device, weeks_since
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
            device.category AS device,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source'), IFNULL(traffic_source.source, '(direct)')) AS source,
            IFNULL((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium'), IFNULL(traffic_source.medium, '(none)')) AS medium
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
    ),
    sessions AS (
        SELECT
            {period} AS period,
            {CHANNEL_SQL} AS channel,
            device,
            user_pseudo_id, session_id,
            SUM(engagement_time_msec) AS eng_ms,
            MAX(CASE WHEN event_name = 'view_item' THEN 1 ELSE 0 END) AS has_product
        FROM events
        GROUP BY period, channel, device, source, medium, user_pseudo_id, session_id
    )
    SELECT
        period, channel, device,
        COUNT(*) AS sessions_with_product,
        ROUND(APPROX_QUANTILES(eng_ms / 1000.0, 100)[OFFSET(50)], 1) AS median_sec,
        ROUND(AVG(eng_ms / 1000.0), 1) AS avg_sec
    FROM sessions
    WHERE has_product = 1 AND channel != 'Spam'
    GROUP BY period, channel, device
    ORDER BY period, channel, device
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
            channel, source, country, device,
            LEAST((next_ts - event_timestamp) / 1000000.0, 300.0) AS sec_on_card
        FROM ordered
        WHERE event_name = 'view_item' AND next_ts IS NOT NULL AND channel != 'Spam'
    )
    SELECT
        period, channel, source, country, device,
        COUNT(*) AS card_views,
        ROUND(APPROX_QUANTILES(sec_on_card, 100)[OFFSET(50)], 1) AS median_sec,
        ROUND(AVG(sec_on_card), 1) AS mean_sec
    FROM card_views
    GROUP BY period, channel, source, country, device
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
            device.category AS device,
            items
        FROM `{BQ_PROJECT}.{BQ_DATASET}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
    ),
    ordered AS (
        SELECT
            date, user_pseudo_id, session_id, event_name, event_timestamp, country, device, items,
            LEAD(event_timestamp) OVER (
                PARTITION BY user_pseudo_id, session_id
                ORDER BY event_timestamp
            ) AS next_ts
        FROM events
    ),
    view_items AS (
        SELECT
            {period} AS period,
            device,
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
            device,
            items[SAFE_OFFSET(0)].item_id AS item_id,
            user_pseudo_id, session_id
        FROM events
        WHERE event_name = 'add_to_cart' AND ARRAY_LENGTH(items) > 0
    ),
    purchase_items AS (
        SELECT
            {period} AS period,
            device,
            items[SAFE_OFFSET(0)].item_id AS item_id,
            user_pseudo_id, session_id
        FROM events
        WHERE event_name = 'purchase' AND ARRAY_LENGTH(items) > 0
    ),
    views_agg AS (
        SELECT
            period, device, item_id, ANY_VALUE(item_name) AS item_name,
            COUNT(*) AS views,
            COUNT(DISTINCT CONCAT(CAST(user_pseudo_id AS STRING), '|', CAST(session_id AS STRING))) AS view_sessions,
            ROUND(APPROX_QUANTILES(sec_on_card, 100)[OFFSET(50)], 1) AS median_sec,
            ROUND(AVG(sec_on_card), 1) AS mean_sec
        FROM view_items
        WHERE sec_on_card IS NOT NULL
        GROUP BY period, device, item_id
    ),
    atc_agg AS (
        SELECT period, device, item_id,
            COUNT(DISTINCT CONCAT(CAST(user_pseudo_id AS STRING), '|', CAST(session_id AS STRING))) AS atc
        FROM atc_items GROUP BY period, device, item_id
    ),
    purchase_agg AS (
        SELECT period, device, item_id,
            COUNT(DISTINCT CONCAT(CAST(user_pseudo_id AS STRING), '|', CAST(session_id AS STRING))) AS purchases
        FROM purchase_items GROUP BY period, device, item_id
    )
    SELECT
        v.period, v.device, v.item_id, v.item_name,
        v.views, v.view_sessions, v.median_sec, v.mean_sec,
        IFNULL(a.atc, 0) AS atc,
        IFNULL(p.purchases, 0) AS purchases
    FROM views_agg v
    LEFT JOIN atc_agg a ON v.period = a.period AND v.device = a.device AND v.item_id = a.item_id
    LEFT JOIN purchase_agg p ON v.period = p.period AND v.device = p.device AND v.item_id = p.item_id
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


def generate_html(rows, grain, excluded_countries, analytics_data=None, _payload_only=False):
    """Generate the full HTML dashboard. Pass _payload_only=True to skip HTML and
    return just the data dict — used by the unified day+week report builder."""

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

    # Per-device subsets shared by every per_device(...) builder below. Defined here
    # (just after `filtered`) so all blocks — Funnels, Analytics, Summary — can use them.
    DEVICE_SLICES = ["all", "mobile", "desktop", "tablet"]
    filtered_by_device = {
        "all": filtered,
        "mobile": [r for r in filtered if r.device == "mobile"],
        "desktop": [r for r in filtered if r.device == "desktop"],
        "tablet": [r for r in filtered if r.device == "tablet"],
    }
    def per_device(builder):
        """Run builder(filt) for each device slice; return {device: result}."""
        return {dev: builder(filtered_by_device[dev]) for dev in DEVICE_SLICES}

    # Parallel slice WITHOUT excluded_countries — used only to populate the
    # per-country payload keys consumed by the reactive country filter on the
    # Funnels tab (Phase 1 of joyful-mapping-sutherland.md). All existing
    # aggregates keep using `filtered` / `filtered_by_device`, so the visual
    # output of current graphs is unchanged when the dropdown stays at default.
    filtered_all = [RowProxy(r, period_map[r.period]) for r in rows if r.period in valid_raw_periods]
    filtered_all_by_device = {
        "all":     filtered_all,
        "mobile":  [r for r in filtered_all if r.device == "mobile"],
        "desktop": [r for r in filtered_all if r.device == "desktop"],
        "tablet":  [r for r in filtered_all if r.device == "tablet"],
    }

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
    # Default n is grain-aware: day=7, week=4, month=3 — see get_comparison_periods.
    _DEFAULT_PREV_N = get_comparison_periods(grain)

    def avg_prev_periods(by_period_key, key_val, metric, n=None):
        """Average a metric over the last n periods (excluding current).
        n defaults to the grain-aware baseline (7d / 4w / 3m)."""
        if len(periods) < 2:
            return 0
        if n is None:
            n = _DEFAULT_PREV_N
        prev_periods = periods[max(0, len(periods) - 1 - n):len(periods) - 1]
        vals = [by_period_key.get((*key_val, p) if isinstance(key_val, tuple) else (p, key_val), {}).get(metric, 0) for p in prev_periods]
        return round(sum(vals) / len(vals), 1) if vals else 0

    def compute_card_deltas(cur_data, by_period, key_val, metrics_list, n=None):
        """Compute deltas: current period vs avg of previous N periods (grain-aware default)."""
        deltas = {}
        for metric, suffix, absolute in metrics_list:
            cur_val = cur_data.get(metric, 0)
            avg_val = avg_prev_periods(by_period, key_val, metric, n=n)
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

    channel_cards = {
        "all": build_channel_cards(None),
        "mobile": build_channel_cards("mobile"),
        "desktop": build_channel_cards("desktop"),
        "tablet": build_channel_cards("tablet"),
    }

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

    source_cards = {
        "all": build_source_cards(None),
        "mobile": build_source_cards("mobile"),
        "desktop": build_source_cards("desktop"),
        "tablet": build_source_cards("tablet"),
    }

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

    # Bubble + trend data — per-device. The bubble chart shows current-period channel
    # conversion at each stage; the trend line shows it over time. Both react to the
    # device filter by swapping in the matching slice via filter handlers (JS side).
    TREND_CHANNELS = ["Social", "Paid", "Direct", "Organic", "Referral", "Email"]

    def _build_bubble_and_trend(device):
        # Bubble: per-channel, current period only
        bubble_all = build_bubble_data("channel", device, min_sessions=0)
        bubble = [
            item for item in sorted(bubble_all, key=lambda x: -x["sessions"])
            if item["name"] not in ("Spam", "Other")
        ]
        bp_ch = aggregate(filtered, ["period", "channel"], lambda r: device is None or r.device == device)
        for item in bubble:
            ch = item["name"]
            cur = bp_ch.get((cur_period, ch), {})
            for metric in ("cat_to_prod", "prod_to_atc", "atc_to_checkout", "checkout_to_purchase"):
                cur_val = cur.get(metric, 0)
                avg_val = avg_prev_periods(bp_ch, ch, metric)  # n defaults to grain-aware baseline
                if avg_val > 0 or cur_val > 0:
                    item[f"delta_{metric}"] = round(cur_val - avg_val, 1)
                else:
                    item[f"delta_{metric}"] = None

        # Trend: per-channel lines per stage, period-by-period
        present = [ch for ch in TREND_CHANNELS
                   if any(bp_ch.get((p, ch), {}).get("sessions", 0) > 0 for p in periods)]
        def _trend_for(metric_field):
            return {
                "labels": periods,
                "datasets": [
                    {
                        "label": ch,
                        "data": [bp_ch.get((p, ch), {}).get(metric_field) for p in periods],
                        "borderColor": CHANNEL_COLORS.get(ch, "#999"),
                        "backgroundColor": CHANNEL_COLORS.get(ch, "#999"),
                        "tension": 0.3,
                        "pointRadius": 3,
                        "spanGaps": True,
                    }
                    for ch in present
                ]
            }
        trend = {
            "channels": present,
            "channel_colors": {ch: CHANNEL_COLORS.get(ch, "#999") for ch in present},
            "cat_to_prod": _trend_for("cat_to_prod"),
            "prod_to_atc": _trend_for("prod_to_atc"),
            "atc_to_checkout": _trend_for("atc_to_checkout"),
            "checkout_to_purchase": _trend_for("checkout_to_purchase"),
        }
        return bubble, trend

    _bubble_trend_per_dev = {dev: _build_bubble_and_trend(None if dev == "all" else dev) for dev in DEVICE_SLICES}
    bubble_channel = {dev: bt[0] for dev, bt in _bubble_trend_per_dev.items()}
    channel_trend = {dev: bt[1] for dev, bt in _bubble_trend_per_dev.items()}
    # Backward-compat helpers used elsewhere in this function:
    by_period_channel_full = aggregate(filtered, ["period", "channel"])
    present_channels = channel_trend["all"]["channels"]

    # ---- BLOCK 4c: Per-stage tables (country × channel) for current period ----
    prev_periods_for_avg = periods[max(0, len(periods) - 1 - _DEFAULT_PREV_N):len(periods) - 1] if len(periods) >= 2 else []

    def _stage_tables_for(filt):
        bp_cc = aggregate(filt, ["period", "country", "channel"])

        def stage_rows(input_field, conv_field, min_input=5, top_n=30):
            rows = []
            for (p, country, ch), data in bp_cc.items():
                if p != cur_period or ch in ("Spam", "Other"):
                    continue
                cur_input = data.get(input_field, 0)
                if cur_input < min_input:
                    continue
                cur_conv = data.get(conv_field, 0)
                if prev_periods_for_avg:
                    vals = [bp_cc.get((pp, country, ch), {}).get(conv_field, 0) for pp in prev_periods_for_avg]
                    avg_val = round(sum(vals) / len(vals), 1) if vals else 0
                else:
                    avg_val = 0
                if avg_val > 0 or cur_conv > 0:
                    delta = round(cur_conv - avg_val, 1)
                else:
                    delta = None
                rows.append({
                    "country": country, "channel": ch,
                    "channel_color": CHANNEL_COLORS.get(ch, "#999"),
                    "input": cur_input, "conv": cur_conv, "delta": delta,
                })
            rows.sort(key=lambda r: -r["input"])
            return rows[:top_n]

        return {
            "prod":     stage_rows("funnel_catalog",  "cat_to_prod"),
            "atc":      stage_rows("funnel_product",  "prod_to_atc"),
            "checkout": stage_rows("funnel_atc",      "atc_to_checkout"),
            "purchase": stage_rows("funnel_checkout", "checkout_to_purchase"),
        }
    stage_tables = per_device(_stage_tables_for)
    # Kept for any backward-compat reads further below in this function:
    by_period_country_channel = aggregate(filtered, ["period", "country", "channel"])

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

    bottom_funnel = {
        "all": build_bottom_funnel(None),
        "mobile": build_bottom_funnel("mobile"),
        "desktop": build_bottom_funnel("desktop"),
        "tablet": build_bottom_funnel("tablet"),
    }

    # ============================================================
    # PER-COUNTRY PAYLOAD KEYS (Phase 1: data only, JS wires up later)
    # ============================================================
    # Built from `filtered_all` (NO country exclusion). The reactive country
    # filter in the dropdown will sum these client-side once Phase 2 lands.
    # Until then nothing reads them, so current graphs are unaffected.
    #
    # Structures kept slim — only the summable fields needed to recover
    # sessions, ER, bounce, deep%, ATC rate, View→ATC, etc. on the JS side.
    # users / revenue / new+returning / medians are intentionally dropped:
    # the Funnels tab cards never display them per-country, and the Summary
    # tab keeps using `filtered` (unaffected by this filter).
    _CC_SUMMABLE_KEYS = (
        "sessions", "engaged_sessions",
        "sessions_1page", "sessions_2_5pages", "sessions_over5pages",
        "funnel_homepage", "funnel_catalog", "funnel_product",
        "funnel_atc", "funnel_checkout", "funnel_purchase",
    )
    def _pick_cc(d):
        return {k: d.get(k, 0) for k in _CC_SUMMABLE_KEYS}

    # Tablet is dropped from per-country structures: the page never filters
    # by tablet (UI buttons are mobile / desktop / all) and tablet traffic
    # is < 1% of sessions. Saves ~25% payload size.
    _CC_DEVICES = ("all", "mobile", "desktop")

    # Cap source dimension to top 10 sources by total sessions across the
    # window. Current source_cards displays top 5 per device, so 10 leaves
    # headroom for JS to re-derive top-5 after country selection changes.
    _src_totals = aggregate(filtered_all, ["source"])
    _top_sources = {
        k[0] for k, _ in sorted(_src_totals.items(), key=lambda kv: -kv[1]["sessions"])[:10]
    }

    # 1. funnel_by_country[device][period][country] — Block 1 funnel bars
    funnel_by_country = {}
    for _dev in _CC_DEVICES:
        _slc = filtered_all_by_device[_dev]
        _by_pc = aggregate(_slc, ["period", "country"])
        _out = {}
        for (_p, _country), _data in _by_pc.items():
            _out.setdefault(_p, {})[_country] = _pick_cc(_data)
        funnel_by_country[_dev] = _out

    # 2. channel_country[device][channel][country][period] — Block 2 cards.
    # Per-period × channel × country, so JS can recompute trend + current-period
    # totals + deltas vs avg of N prev periods + top-5 countries.
    channel_country = {}
    _channels_keep = {"Social", "Paid", "Direct", "Organic", "Referral"}
    for _dev in _CC_DEVICES:
        _slc = filtered_all_by_device[_dev]
        _by_pcc = aggregate(_slc, ["period", "channel", "country"])
        _out = {}
        for (_p, _ch, _country), _data in _by_pcc.items():
            if _ch not in _channels_keep:
                continue
            _out.setdefault(_ch, {}).setdefault(_country, {})[_p] = _pick_cc(_data)
        channel_country[_dev] = _out

    # 3. source_country[device][source][country][period] — Block 3 cards (top 10 sources)
    source_country = {}
    for _dev in _CC_DEVICES:
        _slc = filtered_all_by_device[_dev]
        _by_psc = aggregate(_slc, ["period", "source", "country"])
        _out = {}
        for (_p, _src, _country), _data in _by_psc.items():
            if _src not in _top_sources:
                continue
            _out.setdefault(_src, {}).setdefault(_country, {})[_p] = _pick_cc(_data)
        source_country[_dev] = _out

    # 4. bottom_funnel_full[device] — same shape as bottom_funnel, no exclusion
    def _build_bottom_funnel_full(_slc):
        _agg = aggregate(_slc, ["source", "country"], lambda r: r.period == cur_period_label)
        _table = []
        for (_src, _country), _data in _agg.items():
            if _data["funnel_atc"] == 0 and _data["funnel_checkout"] == 0 and _data["funnel_purchase"] == 0:
                continue
            _table.append({
                "source": _src,
                "country": _country,
                "sessions": _data["sessions"],
                "catalog": _data["funnel_catalog"],
                "product": _data["funnel_product"],
                "atc": _data["funnel_atc"],
                "checkout": _data["funnel_checkout"],
                "purchase": _data["funnel_purchase"],
            })
        return sorted(_table, key=lambda x: (-x["atc"], -x["checkout"], -x["purchase"]))
    bottom_funnel_full = {
        _dev: _build_bottom_funnel_full(filtered_all_by_device[_dev])
        for _dev in _CC_DEVICES
    }

    # 5. stage_tables_full[device][stageKey] — same shape as stage_tables, no exclusion.
    # Reuses the existing _stage_tables_for builder (it accepts any filtered slice).
    stage_tables_full = {
        _dev: _stage_tables_for(filtered_all_by_device[_dev])
        for _dev in _CC_DEVICES
    }

    # 6. bubble_channel_country[device][channel][country] — Block 5 bubble recompute.
    # Current period only, channel × country. JS sums per-channel for selected
    # countries to recover sessions, funnel stages, and stage-to-stage conv %.
    bubble_channel_country = {}
    for _dev in _CC_DEVICES:
        _slc = filtered_all_by_device[_dev]
        _by_cc = aggregate(_slc, ["channel", "country"], lambda r: r.period == cur_period_label)
        _out = {}
        for (_ch, _country), _data in _by_cc.items():
            if _ch in ("Spam", "Other"):
                continue
            _out.setdefault(_ch, {})[_country] = {
                "sessions": _data["sessions"],
                "funnel_catalog": _data["funnel_catalog"],
                "funnel_product": _data["funnel_product"],
                "funnel_atc": _data["funnel_atc"],
                "funnel_checkout": _data["funnel_checkout"],
                "funnel_purchase": _data["funnel_purchase"],
            }
        bubble_channel_country[_dev] = _out

    # ============================================================
    # RAW ROWS — fed to the client-side _aggregateRows() helper so
    # all Summary + Analytics metrics can be recomputed reactively
    # for any country selection. Replaces the per-graph payload-key
    # explosion that Phase 1 used; one slim payload covers everything.
    # ============================================================
    _RAW_ROW_FIELDS = (
        "period", "device", "channel", "source", "country",
        "sessions", "users", "engaged_sessions",
        "sessions_1page", "sessions_2_5pages", "sessions_over5pages",
        "funnel_homepage", "funnel_catalog", "funnel_product",
        "funnel_atc", "funnel_checkout", "funnel_purchase",
        "revenue", "new_users", "returning_users",
        "median_eng_sec", "avg_product_views", "median_product_views",
    )
    raw_rows = []
    for _r in filtered_all:
        _row = {}
        for _f in _RAW_ROW_FIELDS:
            _v = getattr(_r, _f, None)
            if _f == "revenue" and _v is not None:
                _v = float(_v)
            _row[_f] = _v if _v is not None else 0
        raw_rows.append(_row)

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

    # Per-period totals (DEVICE_SLICES / filtered_by_device / per_device defined earlier).
    period_totals = aggregate(filtered, ["period"])

    def trend_of(metric):
        return [period_totals.get((p,), {}).get(metric, 0) for p in periods]

    def last_value(metric):
        return period_totals.get((periods[-1],), {}).get(metric, 0) if periods else 0

    # KPI block — pre-computed per device so the client can switch slices on filter.
    def _build_kpi(filt):
        pt = aggregate(filt, ["period"])
        def _tr(m): return [pt.get((p,), {}).get(m, 0) for p in periods]
        def _last(m): return pt.get((periods[-1],), {}).get(m, 0) if periods else 0
        return {
            "revenue_per_session": {
                "value": _last("revenue_per_session"),
                "delta": compute_delta_vs_prev(_tr("revenue_per_session"), n_prev),
                "trend": _tr("revenue_per_session"),
                "agg": "mean",
            },
            "revenue": {
                "value": round(_last("revenue"), 2),
                "delta": compute_delta_vs_prev(_tr("revenue"), n_prev),
                "trend": [round(v, 2) for v in _tr("revenue")],
                "agg": "sum",
            },
            "atc_rate": {
                "value": _last("atc_rate"),
                "delta": compute_delta_pp(_tr("atc_rate"), n_prev),
                "trend": _tr("atc_rate"),
                "agg": "rate",
            },
            "purchase_rate": {
                "value": _last("cr"),
                "delta": compute_delta_pp(_tr("cr"), n_prev),
                "trend": _tr("cr"),
                "agg": "rate",
            },
            "cart_to_purchase": {
                "value": _last("cart_to_purchase"),
                "delta": compute_delta_pp(_tr("cart_to_purchase"), n_prev),
                "trend": _tr("cart_to_purchase"),
                "agg": "rate",
            },
        }
    sum_kpi = per_device(_build_kpi)

    # Visitors & sessions per period — pre-computed per device for client-side filter switching.
    # NOTE: `users` is summed across breakdowns which double-counts. For accurate unique visitors
    # we'd need a separate query per period; approximating for now.
    def _vis_sess_slice(device_filter):
        bp = period_totals if device_filter is None else aggregate(
            filtered, ["period"], lambda r: r.device == device_filter
        )
        return {
            "visitors": [bp.get((p,), {}).get("users", 0) for p in periods],
            "sessions": [bp.get((p,), {}).get("sessions", 0) for p in periods],
        }
    sum_visitors_sessions = {
        "labels": periods,
        "all": _vis_sess_slice(None),
        "mobile": _vis_sess_slice("mobile"),
        "desktop": _vis_sess_slice("desktop"),
    }

    # Sessions by device type (mobile/desktop/tablet) per period
    dev_by_period = aggregate(filtered, ["period", "device"])
    all_devices = sorted(set(k[1] for k in dev_by_period.keys()))
    sum_device_sessions = {"labels": periods}
    for dev in ["mobile", "desktop", "tablet"]:
        sum_device_sessions[dev] = [dev_by_period.get((p, dev), {}).get("sessions", 0) for p in periods]

    # New vs Returning per period — per-device for client-side filter switching.
    def _build_new_ret(filt):
        pt = aggregate(filt, ["period"])
        return {
            "new": [pt.get((p,), {}).get("new_users", 0) for p in periods],
            "returning": [pt.get((p,), {}).get("returning_users", 0) for p in periods],
        }
    sum_new_returning = {"labels": periods, **per_device(_build_new_ret)}

    # Time on site per device (median) per period
    sum_time_on_site = {"labels": periods}
    for dev in ["mobile", "desktop", "tablet"]:
        sum_time_on_site[dev] = [dev_by_period.get((p, dev), {}).get("median_eng_sec", 0) for p in periods]

    # Bounce rate per device per period
    sum_bounce_device = {"labels": periods}
    for dev in ["mobile", "desktop", "tablet"]:
        sum_bounce_device[dev] = [dev_by_period.get((p, dev), {}).get("bounce_rate", 0) for p in periods]

    # Traffic source trend (sessions + share) — per-device.
    ch_by_period = aggregate(filtered, ["period", "channel"])
    tracked_channels = ["Social", "Paid", "Direct", "Organic", "Referral"]
    def _build_source_trend(filt):
        ch_pp = aggregate(filt, ["period", "channel"])
        pt = aggregate(filt, ["period"])
        sources = []
        for ch in tracked_channels:
            sessions_per_p = [ch_pp.get((p, ch), {}).get("sessions", 0) for p in periods]
            totals_per_p = [pt.get((p,), {}).get("sessions", 0) for p in periods]
            share_per_p = [round(s / t * 100, 1) if t > 0 else 0 for s, t in zip(sessions_per_p, totals_per_p)]
            sources.append({"name": ch, "sessions": sessions_per_p, "share_pct": share_per_p})
        return sources
    sum_source_trend = {"labels": periods, **per_device(_build_source_trend)}

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

    # Source / country tables — per-device.
    source_metrics = [
        ("sessions", "rel"), ("users", "rel"),
        ("new_users", "rel"), ("returning_users", "rel"),
        ("er", "pp"), ("bounce_rate", "pp"),
        ("median_eng_sec", "rel"), ("avg_pages", "rel"),
        ("atc_rate", "pp"), ("cr", "pp"),
    ]
    def _build_source_table(filt):
        chp = aggregate(filt, ["period", "channel"])
        rows = build_row_with_deltas(chp, "channel", source_metrics)
        return sorted(rows, key=lambda r: -r["sessions"]["value"])
    sum_source_table = per_device(_build_source_table)

    def _build_country_table(filt):
        cp = aggregate(filt, ["period", "country"])
        rows = build_row_with_deltas(cp, "country", source_metrics)
        rows = [r for r in rows if r["sessions"]["value"] >= 5]
        return sorted(rows, key=lambda r: -r["sessions"]["value"])[:20]
    sum_country_table = per_device(_build_country_table)
    country_by_period = aggregate(filtered, ["period", "country"])  # kept for downstream uses

    # ATC + PR dual-axis trend — per-device.
    def _build_atc_pr(filt):
        pt = aggregate(filt, ["period"])
        return {
            "atc_rate": [pt.get((p,), {}).get("atc_rate", 0) for p in periods],
            "purchase_rate": [pt.get((p,), {}).get("cr", 0) for p in periods],
        }
    sum_atc_pr_trend = {"labels": periods, **per_device(_build_atc_pr)}

    # Rankings: Source × Country × New/Returning combinations — per-device.
    # We need per-period data for the combination, take last period's values.
    def build_ranking(filt, sort_metric, top_n=10, min_sessions=10):
        cur_p = periods[-1] if periods else None
        combo_agg = aggregate(filt, ["source", "country"], lambda r: r.period == cur_p)
        rankings = []
        for (src, country), d in combo_agg.items():
            if d["sessions"] < min_sessions:
                continue
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

    sum_ranking_atc = per_device(lambda f: build_ranking(f, "atc_rate"))
    sum_ranking_pr  = per_device(lambda f: build_ranking(f, "cr"))

    # ---- Cards-per-session breakdown by country / source (mobile, last period) ----
    cur_period_label = periods[-1] if periods else ""
    n_prev_breakdown = get_comparison_periods(grain)
    prev_periods_set = periods[max(0, len(periods) - 1 - n_prev_breakdown):len(periods) - 1]

    def build_cards_breakdown(group_key, device=None, min_sessions=10):
        """Last period: aggregate cards/session by country or source. Delta vs avg(prev N periods).
        device=None means all devices; pass 'mobile'/'desktop'/'tablet' to scope.
        """
        def _devmatch(r): return device is None or r.device == device
        cur_agg = aggregate(filtered, [group_key],
                            lambda r: _devmatch(r) and r.period == cur_period_label)
        prev_agg = aggregate(filtered, [group_key, "period"],
                             lambda r: _devmatch(r) and r.period in prev_periods_set)
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

    # Per-device versions; default view ("all") matches the previous mobile-only default
    # by being the union across devices. JS swaps slices on filter change.
    cards_by_country = {dev: build_cards_breakdown("country", device=None if dev == "all" else dev) for dev in DEVICE_SLICES}
    cards_by_source  = {dev: build_cards_breakdown("source",  device=None if dev == "all" else dev) for dev in DEVICE_SLICES}

    # ---- Per-card time breakdown by country / source (last period) ----
    pct_data = (analytics_data or {}).get("per_card_time", [])
    pct_filtered = [r for r in pct_data if r.get("country") not in excluded_countries]

    def build_per_card_breakdown(group_key, device=None, min_views=10):
        """Aggregate per-card time by country or source for the last period; delta vs avg of prev periods.
        device=None means all devices; per_card_time rows ship with device after the SQL change.
        """
        from collections import defaultdict
        def _devmatch(r): return device is None or r.get("device") == device
        cur_buckets = defaultdict(lambda: {"card_views": 0, "_med_vals": [], "_mean_sum_w": 0.0})
        for r in pct_filtered:
            if r.get("period") != cur_period_label or not _devmatch(r):
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
            if r.get("period") not in prev_periods_set or not _devmatch(r):
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

    per_card_by_country = {dev: build_per_card_breakdown("country", device=None if dev == "all" else dev) for dev in DEVICE_SLICES}
    per_card_by_source  = {dev: build_per_card_breakdown("source",  device=None if dev == "all" else dev) for dev in DEVICE_SLICES}

    # ---- Per-card time chart series — per-device. ----
    from collections import defaultdict as _dd
    def _build_per_card_chart(device=None):
        pcp = _dd(lambda: {"card_views": 0, "_med": [], "_mean_w": 0.0})
        for r in pct_filtered:
            p = r.get("period")
            if not p:
                continue
            if device is not None and r.get("device") != device:
                continue
            bucket = pcp[p]
            bucket["card_views"] += r.get("card_views", 0)
            if r.get("median_sec") is not None and r.get("card_views"):
                bucket["_med"].extend([r["median_sec"]] * r["card_views"])
            if r.get("mean_sec") is not None:
                bucket["_mean_w"] += r["mean_sec"] * r.get("card_views", 0)
        out = []
        for p, b in pcp.items():
            if b["card_views"] == 0:
                continue
            med = round(sorted(b["_med"])[len(b["_med"]) // 2], 1) if b["_med"] else 0
            mean = round(b["_mean_w"] / b["card_views"], 1) if b["card_views"] else 0
            out.append({"period": p, "card_views": b["card_views"], "median_sec": med, "mean_sec": mean})
        out.sort(key=lambda x: x["period"])
        return out
    per_card_chart = {dev: _build_per_card_chart(None if dev == "all" else dev) for dev in DEVICE_SLICES}

    # ---- Top-20 product cards (per-device) ----
    top_products_rows = (analytics_data or {}).get("top_products", [])
    last_4_set = set(periods[-(n_prev_breakdown + 1):])  # current + 4 previous
    from collections import defaultdict as _dd2

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

    def _build_top_4w(device=None):
        agg = _dd2(lambda: {"item_name": None, "views": 0, "atc": 0, "purchases": 0,
                              "_med_w": [], "_mean_sum_w": 0.0, "_view_total": 0})
        for r in top_products_rows:
            if r.get("period") not in last_4_set:
                continue
            if device is not None and r.get("device") != device:
                continue
            item_id = r.get("item_id")
            if not item_id:
                continue
            b = agg[item_id]
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
        return sorted([_row(iid, b) for iid, b in agg.items() if b["views"] > 0],
                      key=lambda x: -x["views"])[:30]

    def _build_top_cur(device=None):
        cur_dev = _dd2(lambda: {"item_name": None, "views": 0, "atc": 0, "purchases": 0,
                                  "_med_w": [], "_mean_sum_w": 0.0, "_view_total": 0})
        for r in top_products_rows:
            if r.get("period") != cur_period_label:
                continue
            if device is not None and r.get("device") != device:
                continue
            item_id = r.get("item_id")
            if not item_id:
                continue
            b = cur_dev[item_id]
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
        return sorted([_row(iid, b) for iid, b in cur_dev.items() if b["views"] > 0],
                      key=lambda x: -x["views"])[:30]

    top_products_4w   = {dev: _build_top_4w(None if dev == "all" else dev)  for dev in DEVICE_SLICES}
    top_products_week = {dev: _build_top_cur(None if dev == "all" else dev) for dev in DEVICE_SLICES}
    # The original code path below is now bypassed (kept as a no-op via the empty list).
    _top_products_legacy_unused = sorted(
        [{
            "item_id": r.get("item_id"),
            "item_name": r.get("item_name") or r.get("item_id"),
            "views": r.get("views", 0),
            "median_sec": r.get("median_sec") or 0,
            "mean_sec": r.get("mean_sec") or 0,
            "atc": r.get("atc", 0),
            "purchases": r.get("purchases", 0),
            "cr_atc": round(r.get("atc", 0) / r["views"] * 100, 1) if r.get("views") else 0,
        } for r in [] if r.get("views", 0) > 0],
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
        # Per-country breakdowns for the reactive country filter (Phase 1).
        # Built from filtered_all (no country exclusion). JS will consume these
        # in Phase 2 to recompute Funnels-tab blocks on checkbox toggle.
        "funnel_by_country": funnel_by_country,
        "channel_country": channel_country,
        "source_country": source_country,
        "bottom_funnel_full": bottom_funnel_full,
        "stage_tables_full": stage_tables_full,
        "bubble_channel_country": bubble_channel_country,
        # Phase 5: raw rows for client-side aggregation across all tabs
        "raw_rows": raw_rows,
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

    if _payload_only:
        return payload
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


def render_card_html(card, name_key, dev_prefix=""):
    """Render a single card HTML block for channel or source cards.

    name_key: 'channel' for channel cards, 'source' for source cards.
    dev_prefix: e.g. 'mobile-', 'desktop-', '' (for the 'all' slice). Prepended to
    canvas IDs so 4 device variants of the slider can coexist in the DOM without
    collisions; charts then init by looping over each variant.
    """
    name = card[name_key]
    if name_key == "channel":
        border_style = f' style="border-top: 4px solid {card["color"]}"'
        canvas_id = f"{dev_prefix}funnel-channel-{name.lower().replace(' ', '-')}"
    else:
        border_style = ""
        canvas_id = f"{dev_prefix}funnel-source-{name.replace('.', '_').replace('(', '').replace(')', '').replace(' ', '-')}"

    top_countries_html = "".join(
        f'<div class="country-row"><span>{flag(c)}</span><span>{s}</span></div>'
        for c, s in card["top_countries"]
    )

    low_n_badge = '<span class="low-n-badge">&#9888; low n</span>' if card.get("sessions", 0) < 50 else ""

    # data-card-* attrs: stable selectors for the JS country-filter recompute
    # so it can find cards without parsing canvas IDs.
    return f"""
        <div class="block" data-card-type="{name_key}" data-card-name="{name}"{border_style}>
            <h3>{name}{low_n_badge}</h3>
            <canvas id="{canvas_id}"></canvas>
            <div class="metrics">
                <div class="metric" data-metric="sessions">
                    <span class="label">Сессии</span>
                    <span class="value">{card['sessions']}</span>
                    {delta_html(card['delta_sessions'])}
                </div>
                <div class="metric" data-metric="share">
                    <span class="label">Доля</span>
                    <span class="value">{card['share']}%</span>
                </div>
                <div class="metric" data-metric="er">
                    <span class="label">ER</span>
                    <span class="value">{card['er']}%</span>
                    {delta_html(card['delta_er'], suffix=' п.п.')}
                </div>
                <div class="metric" data-metric="median_sec">
                    <span class="label">Median sec</span>
                    <span class="value">{card['median_sec']}s</span>
                    {delta_html(card['delta_median'], suffix='s')}
                </div>
                <div class="metric" data-metric="deep">
                    <span class="label">Глубина 2+</span>
                    <span class="value">{card['deep_pct']}%</span>
                    {delta_html(card['delta_deep'], suffix=' п.п.')}
                </div>
                <div class="metric" data-metric="products">
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
    """Build the full HTML string. If data['_unified'] is set, the page ships
    payloads for both day and week and lets the client swap grain without a
    page reload (default grain provides the SSR initial state)."""
    _unified_mode = bool(data.get("_unified"))
    _payloads_by_grain = data.get("_payloads") or {}
    _default_grain = data.get("_default_grain") or data.get("grain", "week")
    # Render 4 device variants of channel/source sliders. Visibility-toggled by
    # data-device-cell — the active slice mounts visible, others stay display:none
    # but their charts still init (Chart.js doesn't require visibility).
    _DEV_PREFIXES = {"all": "", "mobile": "mobile-", "desktop": "desktop-", "tablet": "tablet-"}
    def _render_slider_set(card_groups, key):
        # data-device-slice has EXACT-match visibility semantics: only the slice
        # whose name equals FILTERS.device (incl. 'all') is shown — sliders are
        # complete views, not additive cells. Non-active slices start hidden.
        chunks = []
        for dev, cards in card_groups.items():
            prefix = _DEV_PREFIXES[dev]
            hidden = '' if dev == 'all' else ' style="display:none"'
            inner = "".join(render_card_html(c, key, prefix) for c in cards)
            chunks.append(f'<div class="slider" data-device-slice="{dev}"{hidden}>{inner}</div>')
        return "".join(chunks)
    cards_html_all = _render_slider_set(data["channel_cards"], "channel")
    source_cards_html_all = _render_slider_set(data["source_cards"], "source")

    # Header country filter — checkboxes for excluded (unchecked) and remaining (checked)
    _excluded_set = set(data.get("excluded_countries", []))
    _all_countries = data.get("all_countries", [])
    _excluded_in_data = [c for c in _all_countries if c in _excluded_set]
    _included_in_data = [c for c in _all_countries if c not in _excluded_set]
    country_excluded_html = "".join(
        f'<label class="check"><input type="checkbox" data-country="{c}"> {flag(c)}</label>'
        for c in _excluded_in_data
    )
    # Phase 4: included labels also get .check for visual consistency with excluded ones.
    country_included_html = "".join(
        f'<label class="check"><input type="checkbox" data-country="{c}" checked> {flag(c)}</label>'
        for c in _included_in_data
    )
    country_total = len(_excluded_in_data) + len(_included_in_data)
    country_checked_initial = len(_included_in_data)

    # Hide month-grain button until at least MONTH_GRAIN_MIN_FULL_MONTHS full months exist.
    # Data starts mid-Feb 2026, so we will only have meaningful month-over-month
    # comparisons once Feb→Jun completes (button reappears in early July 2026).
    if count_full_months_available() >= MONTH_GRAIN_MIN_FULL_MONTHS:
        _month_active = "is-active" if data["grain"] == "month" else ""
        month_btn_html = f'<a href="report_month.html" class="btn-sq {_month_active}">M</a>'
    else:
        month_btn_html = ""

    # In unified mode, D and W are JS buttons that swap data without a reload.
    # Otherwise (single-grain pages or month report) they stay as plain links.
    if _unified_mode:
        _day_active  = "is-active" if _default_grain == "day"  else ""
        _week_active = "is-active" if _default_grain == "week" else ""
        grain_buttons_html = (
            f'<button type="button" class="btn-sq {_day_active}" data-grain="day" onclick="setGrain(\'day\', this)">D</button>'
            f'<button type="button" class="btn-sq {_week_active}" data-grain="week" onclick="setGrain(\'week\', this)">W</button>'
        )
    else:
        grain_buttons_html = (
            f'<a href="report_day.html" class="btn-sq {("is-active" if data["grain"] == "day" else "")}">D</a>'
            f'<a href="report_week.html" class="btn-sq {("is-active" if data["grain"] == "week" else "")}">W</a>'
        )

    # Grain-aware labels for "last complete period" and "vs previous N periods" captions.
    # Mirrors the KPI baseline: day=7, week=4, month=3.
    # `prev_short_label` is the same idea but in a compact form for table column headers.
    if data["grain"] == "day":
        last_full_label = "последний полный день"
        prev_avg_label = "Δ vs avg прошлых 7 дней"
        prev_short_label = "Δ vs ср. 7 дней"
    elif data["grain"] == "month":
        last_full_label = "последний полный месяц"
        prev_avg_label = "Δ vs avg прошлых 3 месяцев"
        prev_short_label = "Δ vs ср. 3 мес."
    else:
        last_full_label = "последняя полная неделя"
        prev_avg_label = "Δ vs avg прошлых 4 недель"
        prev_short_label = "Δ vs ср. 4 пред."

    # SSR initial bottom-funnel rows for "all" device. JS rewrites tbody on filter change.
    _bottom_funnel_initial = data.get("bottom_funnel", {}).get("all", []) if isinstance(data.get("bottom_funnel"), dict) else data.get("bottom_funnel", [])
    bottom_funnel_html = "".join(
        f'<tr><td>{r["source"]}</td><td>{flag(r["country"])}</td><td>{r["sessions"]}</td>'
        f'<td>{r["catalog"]}</td><td>{r["product"]}</td>'
        f'<td class="highlight">{r["atc"]}</td><td class="highlight">{r["checkout"]}</td>'
        f'<td class="highlight">{r["purchase"]}</td></tr>'
        for r in _bottom_funnel_initial
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
            return f'<div class="data-table-wrap"><table class="data-table"><thead><tr><th>Страна</th><th>Канал</th><th>{input_label}</th><th>Конверсия</th><th><span data-grain-label="prev_short">{prev_short_label}</span></th></tr></thead><tbody><tr><td colspan="5" class="empty-row">Нет данных</td></tr></tbody></table></div>'
        body = "".join(
            f'<tr><td>{flag(r["country"])} {r["country"]}</td>'
            f'<td><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{r["channel_color"]}; margin-right:6px; vertical-align:middle;"></span>{r["channel"]}</td>'
            f'<td>{r["input"]}</td><td>{r["conv"]}%</td>'
            f'{_stage_delta_cell(r["delta"])}</tr>'
            for r in rows
        )
        return (
            f'<div class="data-table-wrap"><table class="data-table">'
            f'<thead><tr><th>Страна</th><th>Канал</th><th>{input_label}</th>'
            f'<th>Конверсия</th><th><span data-grain-label="prev_short">{prev_short_label}</span></th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>'
        )

    # SSR initial stage tables for "all" device. JS rewrites contents on filter change.
    stage_tables_data_all = data.get("stage_tables", {}).get("all", {}) if isinstance(data.get("stage_tables"), dict) and "all" in data.get("stage_tables", {}) else data.get("stage_tables", {})
    stage_table_prod_html     = _render_stage_table(stage_tables_data_all.get("prod", []),     "Сессии в каталоге")
    stage_table_atc_html      = _render_stage_table(stage_tables_data_all.get("atc", []),      "Сессии на товаре")
    stage_table_checkout_html = _render_stage_table(stage_tables_data_all.get("checkout", []), "Сессии с корзиной")
    stage_table_purchase_html = _render_stage_table(stage_tables_data_all.get("purchase", []), "Сессии с чекаутом")

    def _delta_cell(v, suffix=""):
        if v is None:
            return '<td><span class="delta neutral">—</span></td>'
        if v > 0:
            return f'<td><span class="delta green">↑ +{v}{suffix}</span></td>'
        if v < 0:
            return f'<td><span class="delta red">↓ {v}{suffix}</span></td>'
        return f'<td><span class="delta neutral">→ 0{suffix}</span></td>'

    # Analytics tab tables now ship per-device dicts. SSR initial = "all" device,
    # JS handler rewrites contents on filter change.
    _cb = data.get("cards_breakdown", {})
    _cb_by_country_all = (_cb.get("by_country", {}) or {}).get("all", []) if isinstance(_cb.get("by_country", {}), dict) else _cb.get("by_country", [])
    _cb_by_source_all = (_cb.get("by_source", {}) or {}).get("all", []) if isinstance(_cb.get("by_source", {}), dict) else _cb.get("by_source", [])
    cards_country_rows = "".join(
        f'<tr><td>{flag(r["name"])} {r["name"]}</td><td>{r["sessions"]}</td>'
        f'<td>{r["median_products"]}</td>{_delta_cell(r.get("delta_median"))}'
        f'<td>{r["mean_products"]}</td>{_delta_cell(r.get("delta_mean"))}</tr>'
        for r in _cb_by_country_all
    ) or '<tr><td colspan="6" class="empty-row">Нет данных</td></tr>'
    cards_source_rows = "".join(
        f'<tr><td>{r["name"]}</td><td>{r["sessions"]}</td>'
        f'<td>{r["median_products"]}</td>{_delta_cell(r.get("delta_median"))}'
        f'<td>{r["mean_products"]}</td>{_delta_cell(r.get("delta_mean"))}</tr>'
        for r in _cb_by_source_all
    ) or '<tr><td colspan="6" class="empty-row">Нет данных</td></tr>'

    _pb = data.get("per_card_breakdown", {})
    _pb_by_country_all = (_pb.get("by_country", {}) or {}).get("all", []) if isinstance(_pb.get("by_country", {}), dict) else _pb.get("by_country", [])
    _pb_by_source_all = (_pb.get("by_source", {}) or {}).get("all", []) if isinstance(_pb.get("by_source", {}), dict) else _pb.get("by_source", [])
    per_card_country_rows = "".join(
        f'<tr><td>{flag(r["name"])} {r["name"]}</td><td>{r["card_views"]}</td>'
        f'<td>{r["median_sec"]}s</td>{_delta_cell(r.get("delta_median"), "s")}'
        f'<td>{r["mean_sec"]}s</td>{_delta_cell(r.get("delta_mean"), "s")}</tr>'
        for r in _pb_by_country_all
    ) or '<tr><td colspan="6" class="empty-row">Нет данных</td></tr>'
    per_card_source_rows = "".join(
        f'<tr><td>{r["name"]}</td><td>{r["card_views"]}</td>'
        f'<td>{r["median_sec"]}s</td>{_delta_cell(r.get("delta_median"), "s")}'
        f'<td>{r["mean_sec"]}s</td>{_delta_cell(r.get("delta_mean"), "s")}</tr>'
        for r in _pb_by_source_all
    ) or '<tr><td colspan="6" class="empty-row">Нет данных</td></tr>'

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
        return f"""<div class="block h2x2 cell-kpi">
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
        <div class="block h2x2 cell-kpi">
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

        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: inherit; }}
        body {{ font-family: var(--ff-mono); background: var(--bg-page); color: var(--tx-primary); padding: 0; margin: 0; line-height: 1.25; }}
        .main-container {{ max-width: 1400px; margin: 0 auto; padding: 0 var(--sp-5) var(--sp-5); }}
        h1 {{ font-size: var(--fs-kpi); font-weight: var(--fw-bold); margin-bottom: var(--sp-2); line-height: 1.25; }}
        h2 {{ font-size: var(--fs-h2); font-weight: var(--fw-semibold); margin: var(--mt-h2) 0 0; line-height: 1.25; }}
        h3 {{ font-size: var(--fs-h3); font-weight: var(--fw-semibold); margin: var(--mt-h3) 0 0; line-height: 1.25; }}
        h4 {{ font-size: var(--fs-body); font-weight: var(--fw-semibold); margin: var(--mt-h4) 0 0; color: var(--tx-secondary); line-height: 1.25; }}
        .meta {{ color: var(--tx-secondary); font-size: var(--fs-caption); line-height: 1.25; margin: 0 0 var(--content-gap); }}
        h2 + .meta, h3 + .meta, h4 + .meta {{ margin-top: var(--tight-pair); }}
        /* Reset top margin for headings inside cards / KPI blocks — those have their own spacing via grid */
        .cell-kpi h2, .cell-kpi h3, .cell-kpi h4,
        .kpi-block h2, .kpi-block h3, .kpi-block h4 {{ margin-top: 0; }}
        .agg-tag {{ display: inline-block; font-size: var(--fs-caption); color: var(--tx-muted); font-weight: var(--fw-regular); text-transform: lowercase; letter-spacing: var(--ls-label); margin-left: var(--sp-1); }}

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
        .brand-stack {{ display: flex; flex-direction: column; gap: 2px; }}
        .brand {{ font-size: var(--fs-h2); font-weight: var(--fw-bold); color: var(--tx-primary); line-height: 1.1; }}
        .header-meta {{ font-size: var(--fs-caption); color: var(--tx-secondary); line-height: 1.2; }}
        .header-right {{ display: flex; align-items: center; gap: var(--sp-3); }}
        .grain-nav {{ display: flex; gap: 2px; }}
        .tab-nav {{ display: flex; gap: var(--sp-3); }}

        /* Controls v1.0: .btn / .btn-sq / .tab / .check */
        .btn {{
            font-family: var(--ff-mono);
            height: var(--h-control); padding: 0 var(--sp-3);
            display: inline-flex; align-items: center; justify-content: center;
            border-radius: var(--r-control);
            font-size: var(--fs-body); font-weight: var(--fw-regular);
            color: var(--tx-secondary); background: var(--bg-muted);
            border: 1px solid transparent; cursor: pointer; line-height: 1;
            text-decoration: none;
            transition: background 120ms, color 120ms, border-color 120ms;
        }}
        .btn:hover     {{ background: var(--bg-border); color: var(--tx-primary); }}
        .btn.is-active {{ background: var(--bg-inverse); color: var(--tx-ondark); }}
        .btn:focus     {{ outline: 2px solid var(--c-channel-social); outline-offset: 2px; }}
        .btn[disabled] {{ opacity: 0.4; cursor: not-allowed; }}

        .btn-sq {{
            font-family: var(--ff-mono);
            width: var(--h-control); height: var(--h-control);
            display: inline-flex; align-items: center; justify-content: center;
            font-size: var(--fs-body); font-weight: var(--fw-semibold);
            color: var(--tx-secondary); background: var(--bg-muted);
            border: 1px solid transparent; border-radius: var(--r-control);
            cursor: pointer; text-decoration: none;
            transition: background 120ms, color 120ms, border-color 120ms;
        }}
        .btn-sq:hover     {{ background: var(--bg-border); color: var(--tx-primary); }}
        .btn-sq.is-active {{ background: var(--bg-inverse); color: var(--tx-ondark); }}
        .btn-sq:focus     {{ outline: 2px solid var(--c-channel-social); outline-offset: 2px; }}

        .tab {{
            font-family: var(--ff-mono);
            background: none; border: none;
            border-bottom: 2px solid transparent;
            padding: var(--sp-2) var(--sp-3) var(--sp-1);
            font-size: var(--fs-body); font-weight: var(--fw-regular);
            color: var(--tx-muted); cursor: pointer; line-height: 1.4;
            transition: color 120ms, border-color 120ms;
        }}
        .tab:hover     {{ color: var(--tx-secondary); }}
        .tab.is-active {{ color: var(--tx-primary); border-bottom-color: var(--tx-primary); font-weight: var(--fw-semibold); }}
        .tab:focus     {{ outline: 2px solid var(--c-channel-social); outline-offset: 2px; border-radius: var(--r-control); }}

        .tab-bar {{ display: flex; gap: var(--sp-3); padding: 0 var(--sp-3); }}

        .check {{ display: inline-flex; align-items: center; gap: var(--sp-1); font-size: var(--fs-caption); color: var(--tx-primary); cursor: pointer; line-height: 1.4; user-select: none; }}
        .check input {{
            appearance: none; -webkit-appearance: none;
            width: 14px; height: 14px;
            border: 1.5px solid var(--bg-border); border-radius: var(--r-control);
            background: var(--bg-card); cursor: pointer; flex-shrink: 0;
            position: relative;
            transition: background 120ms, border-color 120ms;
        }}
        .check input:hover    {{ border-color: var(--tx-secondary); }}
        .check input:checked  {{ background: var(--bg-inverse); border-color: var(--bg-inverse); }}
        .check input:checked::after {{
            content: ''; position: absolute; left: 3px; top: 0;
            width: 5px; height: 9px;
            border: solid var(--tx-ondark); border-width: 0 2px 2px 0;
            transform: rotate(45deg);
        }}
        .check input:focus    {{ outline: 2px solid var(--c-channel-social); outline-offset: 2px; }}

        .filter-bar {{ display: flex; align-items: flex-start; gap: var(--sp-5); padding: var(--sp-3); background: var(--bg-card); border-radius: var(--r-xl); box-shadow: var(--sh-card); flex-wrap: wrap; }}
        .filter-group {{ display: flex; flex-direction: column; gap: var(--sp-1); }}
        .filter-label {{ font-size: var(--fs-caption); font-weight: var(--fw-regular); color: var(--tx-secondary); text-transform: uppercase; letter-spacing: var(--ls-label); padding-bottom: var(--sp-1); border-bottom: 1px solid var(--bg-border); min-width: 110px; }}
        .filter-buttons {{ display: flex; gap: var(--sp-1); }}


        /* Global header filters (UI-only): device + country */
        .device-nav {{ display: flex; gap: 2px; }}
        .country-filter {{ position: relative; }}
        .country-panel {{
            position: absolute; right: 0; top: calc(100% + 4px);
            background: var(--bg-card); border: 1px solid var(--bg-border);
            border-radius: var(--r-md); padding: var(--sp-2); min-width: 240px;
            max-height: 360px; overflow-y: auto; z-index: 1000;
            box-shadow: var(--sh-card);
            font-size: var(--fs-body);
        }}
        .country-panel[hidden] {{ display: none; }}
        .country-section {{ display: flex; flex-direction: column; gap: 2px; }}
        .country-section label {{ display: flex; align-items: center; gap: 6px; cursor: pointer; padding: 2px 0; }}
        .country-section-title {{ font-weight: var(--fw-bold); font-size: var(--fs-caption); color: var(--tx-secondary); margin: var(--tight-pair) 0 2px; text-transform: uppercase; }}
        .country-sep {{ border: none; border-top: 1px solid var(--bg-border); margin: 6px 0; }}
        .country-panel .filter-buttons {{ display: flex; gap: var(--sp-1, 4px); margin-top: var(--sp-2, 8px); }}
        .country-panel .filter-buttons .btn {{ flex: 1; }}
        /* Mass-toggle row for the long "Все страны" section sticks to the bottom of
           the scrollable panel — users always have one-click access without scroll. */
        .country-panel .filter-buttons.sticky-bottom {{
            position: sticky; bottom: 0; background: var(--bg-card);
            padding: var(--sp-1, 4px) 0; margin-top: 0;
            border-top: 1px solid var(--bg-border);
        }}
        .filters-note {{ font-size: var(--fs-chart-meta); color: var(--tx-secondary); align-self: center; max-width: 140px; line-height: 1.2; }}
        /* === 12-column × fixed-row Grid System ===
           Row height = 80px. Elements specify cols (span X) + rows (span Y).
           Naming convention: hNxM = N rows tall × M cols wide.
           Blocks with a title row use the size that includes the title (e.g. 5×8 = 4 data rows + 1 title row).
        */
        /* Blocks v1.0 — 12-кол. сетка, ряды auto по контенту, единый chart-height */
        .grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: var(--sp-4);
            margin-bottom: var(--sp-5);
        }}
        .block {{
            background: var(--bg-card);
            border-radius: var(--r-xl);
            box-shadow: var(--sh-card);
            padding: var(--sp-3);
            display: flex; flex-direction: column;
        }}
        .block > :first-child {{ margin-top: 0; }}

        /* Span (ширина в 12-кол. сетке) */
        .span-12 {{ grid-column: span 12; }}
        .span-8  {{ grid-column: span 8; }}
        .span-6  {{ grid-column: span 6; }}
        .span-4  {{ grid-column: span 4; }}
        .span-3  {{ grid-column: span 3; }}
        .span-2  {{ grid-column: span 2; }}

        /* Chart-wrap: ФИКС-высота — никакого flex-роста (иначе Chart.js feedback loop) */
        .chart-wrap {{ position: relative; width: 100%; height: var(--ch-md); }}
        .chart-wrap > canvas {{ position: absolute; top: 0; left: 0; width: 100% !important; height: 100% !important; }}
        .block.h-xs .chart-wrap {{ height: var(--ch-xs); }}
        .block.h-sm .chart-wrap {{ height: var(--ch-sm); }}
        .block.h-md .chart-wrap {{ height: var(--ch-md); }}
        .block.h-lg .chart-wrap {{ height: var(--ch-lg); }}

        /* Slider cards keep fixed dimensions */
        .slider > .block .chart-wrap {{ height: var(--ch-sm); }}

        /* KPI block (Summary page) — 4 cols wide × 5 rows tall (1 title + 4 data) */
        .kpi-block {{
            grid-column: span 4;
            display: flex;
            flex-direction: column;
            padding: var(--sp-3);    /* совпасть box-моделью с .block-соседом (то же padding, без gap) */
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
            grid-template-rows: repeat(4, minmax(0, 1fr));
            gap: var(--sp-2);
            height: var(--ch-md);
        }}
        .kpi-grid .cell-kpi {{ min-height: 0; min-width: 0; }}    /* убран overflow: hidden — обрезал CART→PURCHASE */
        .kpi-grid .kpi-rps {{ grid-column: 1; grid-row: 1; }}
        .kpi-grid .kpi-rev {{ grid-column: 2; grid-row: 1; }}
        .kpi-grid .kpi-atc {{ grid-column: 1; grid-row: 2 / span 2; }}
        .kpi-grid .kpi-pr  {{ grid-column: 2; grid-row: 2 / span 2; }}
        .kpi-grid .kpi-c2p {{ grid-column: 1 / span 2; grid-row: 4; }}
        .kpi-grid .cell-kpi {{ padding: 10px var(--sp-3); display: flex; flex-direction: column; justify-content: space-between; }}
        .kpi-grid .kpi-c2p {{ padding: 6px var(--sp-3); }}    /* override — c2p row узкий (64px), 10px padding не влезает */
        .kpi-grid .cell-kpi .kpi-label {{ font-size: var(--fs-caption); }}
        .kpi-grid .cell-kpi .kpi-value {{ font-size: var(--fs-h2); font-weight: var(--fw-bold); line-height: 1.1; }}
        .kpi-grid .cell-kpi .kpi-spark {{ height: 60px; flex: none; margin-top: var(--sp-1); background: var(--bg-muted); border-radius: var(--r-md); padding: 2px; position: relative; }}    /* 50→60: больше места для min/max меток */
        .kpi-grid .cell-kpi .kpi-spark .chart-wrap {{ height: 100%; }}

        /* KPI card (2x2) */
        .cell-kpi {{ display: flex; flex-direction: column; }}
        .kpi-label {{ font-size: var(--fs-caption); text-transform: uppercase; color: var(--tx-secondary); letter-spacing: var(--ls-label); }}
        .kpi-value {{ font-size: var(--fs-kpi); font-weight: var(--fw-bold); margin: var(--sp-1) 0; }}
        .kpi-bench {{ font-size: var(--fs-caption); color: var(--tx-muted); }}
        .kpi-meta {{ display: flex; gap: var(--sp-2); align-items: baseline; }}
        .kpi-spark {{ background: var(--bg-muted); border-radius: var(--r-lg); margin-top: var(--sp-2); padding: var(--sp-1); flex: 1; min-height: 40px; }}

        /* Slider (channel cards, bubble charts) */
        .slider {{ display: flex; gap: var(--sp-4); overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: var(--sp-2); margin-bottom: var(--sp-5); }}
        .slider::-webkit-scrollbar {{ height: 6px; }}
        .slider::-webkit-scrollbar-thumb {{ background: var(--tx-muted); border-radius: var(--r-sm); }}
        .slider > .block, .slider > .cell {{ min-width: 380px; max-width: 380px; flex-shrink: 0; scroll-snap-align: start; }}

        /* Shared */
        .nr-bar {{ height: 10px; background: var(--c-channel-social); border-radius: 5px; overflow: hidden; }}
        .nr-new {{ height: 100%; background: var(--c-channel-organic); }}
        .ch-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
        .delta {{ font-size: var(--fs-body); }}
        .delta.green {{ color: var(--c-growth); }}
        .delta.red {{ color: var(--c-decline); }}
        .delta.neutral {{ color: var(--c-neutral); }}
        .delta-sm {{ font-size: var(--fs-chart-meta); margin-left: var(--sp-1); }}
        .low-n-badge {{ font-size: var(--fs-chart-meta); color: var(--c-decline); margin-left: 6px; padding: 2px 6px; background: var(--bg-alert); border-radius: var(--r-control); }}
        .empty-row {{ text-align: center; color: var(--tx-muted); }}
        .metrics {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--sp-2); margin-top: var(--sp-3); }}
        .metric {{ display: flex; flex-direction: column; }}
        .metric .label {{ font-size: var(--fs-caption); color: var(--tx-secondary); text-transform: uppercase; }}
        .metric .value {{ font-size: var(--fs-h2); font-weight: var(--fw-semibold); }}
        .top-countries {{ margin-top: var(--sp-3); }}
        .country-row {{ display: flex; justify-content: space-between; font-size: var(--fs-body); padding: 2px 0; border-bottom: 1px solid var(--bg-divider); }}

        /* Filters */
        .bubble-filters {{ display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-bottom: var(--sp-3); padding: var(--sp-2) var(--sp-3); background: var(--bg-card); border-radius: var(--r-lg); box-shadow: var(--sh-card); }}
        .bubble-filters label {{ font-size: var(--fs-caption); cursor: pointer; display: flex; align-items: center; gap: var(--sp-1); }}
        .bubble-filters input {{ cursor: pointer; }}

        /* Data tables */
        /* Tables v1.1 — naked: max-height + overflow только; карточка приходит от .block */
        .data-table-wrap {{ max-height: var(--max-h-table); overflow-y: auto; }}
        .data-table {{ width: 100%; border-collapse: collapse; }}
        .data-table th {{ position: sticky; top: 0; z-index: 1; background: var(--bg-inverse); color: var(--tx-ondark); height: var(--row-h-table); padding: 0 var(--sp-3); font-size: var(--fs-caption); font-weight: var(--fw-semibold); text-align: left; line-height: 1.25; cursor: pointer; user-select: none; }}
        .data-table th:hover {{ background: var(--bg-inverse2); }}
        .data-table td {{ height: var(--row-h-table); padding: 0 var(--sp-3); font-size: var(--fs-caption); line-height: 1.25; border-bottom: 1px solid var(--bg-divider); vertical-align: middle; }}
        .data-table tr:last-child td {{ border-bottom: none; }}
        .data-table tr:hover {{ background: var(--bg-hover); }}
        .data-table .highlight {{ font-weight: var(--fw-bold); color: var(--c-highlight); }}
        .data-table-wrap::-webkit-scrollbar {{ width: 6px; }}
        .data-table-wrap::-webkit-scrollbar-track {{ background: transparent; }}
        .data-table-wrap::-webkit-scrollbar-thumb {{ background: var(--tx-muted); border-radius: var(--r-control); }}

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
            <div class="brand-stack">
                <div class="brand">Pinkspink</div>
                <div class="header-meta">Сгенерировано: {data['generated']}</div>
            </div>
        </div>
        <div class="header-right">
            <nav class="grain-nav">
                {grain_buttons_html}
                {month_btn_html}
            </nav>
            <nav class="device-nav">
                <button class="btn is-active" data-device="all" onclick="setDeviceFilter('all', this)">Все</button>
                <button class="btn" data-device="mobile" onclick="setDeviceFilter('mobile', this)">Моб</button>
                <button class="btn" data-device="desktop" onclick="setDeviceFilter('desktop', this)">Веб</button>
            </nav>
            <div class="country-filter">
                <button class="btn" id="country-toggle" onclick="toggleCountryPanel(event)">
                    Страны <span id="country-count">{country_checked_initial} из {country_total}</span> ▾
                </button>
                <div class="country-panel" id="country-panel" hidden>
                    <div class="country-section-title">Исключённые</div>
                    <div class="country-section excluded">{country_excluded_html}</div>
                    <div class="filter-buttons">
                        <button type="button" class="btn" onclick="setExcludedSection(true)">Добавить исключения</button>
                        <button type="button" class="btn" onclick="setExcludedSection(false)">Убрать исключения</button>
                    </div>
                    <hr class="country-sep">
                    <div class="country-section-title">Все страны</div>
                    <div class="country-section included country-list">{country_included_html}</div>
                    <div class="filter-buttons sticky-bottom">
                        <button type="button" class="btn" onclick="setAllCountries(true)">Выбрать все</button>
                        <button type="button" class="btn" onclick="setAllCountries(false)">Убрать все</button>
                    </div>
                </div>
            </div>
            <nav class="tab-bar">
                <button class="tab is-active" onclick="switchTab('summary', this)">Сводка</button>
                <button class="tab" onclick="switchTab('funnels', this)">Воронки</button>
                <button class="tab" onclick="switchTab('analytics', this)">Карточка товара</button>
            </nav>
        </div>
    </header>

    <div class="main-container">

    <!-- ===== SUMMARY TAB ===== -->
    <div id="tab-summary">
        <div class="grid">
            <div class="kpi-block">
                
                    <h3>KPI <span class="agg-tag">vs avg {'3 прошлых месяца' if data['grain'] == 'month' else ('4 прошлые недели' if data['grain'] == 'week' else '7 прошлых дней')}</span></h3>
                    <p class="meta">Показатели и сравнение со средними значениями</p>
                
                <div class="kpi-grid">
                    <div class="block cell-kpi kpi-rps">
                        <div class="kpi-label">Revenue / Session <span class="agg-tag">(mean)</span></div>
                        <div class="kpi-value" id="sum-kpi-rps"></div>
                        <div id="sum-kpi-rps-delta"></div>
                    </div>
                    <div class="block cell-kpi kpi-rev">
                        <div class="kpi-label">Revenue <span class="agg-tag">(sum)</span></div>
                        <div class="kpi-value" id="sum-kpi-rev"></div>
                        <div id="sum-kpi-rev-delta"></div>
                    </div>
                    <div class="block cell-kpi kpi-atc">
                        <div class="kpi-label">ATC Rate <span class="agg-tag">(rate)</span></div>
                        <div class="kpi-value" id="sum-kpi-atc"></div>
                        <div id="sum-kpi-atc-delta"></div>
                        <div class="kpi-spark"><canvas id="sum-spark-atc"></canvas></div>
                    </div>
                    <div class="block cell-kpi kpi-pr">
                        <div class="kpi-label">Purchase Rate <span class="agg-tag">(rate)</span></div>
                        <div class="kpi-value" id="sum-kpi-pr"></div>
                        <div id="sum-kpi-pr-delta"></div>
                        <div class="kpi-spark"><canvas id="sum-spark-pr"></canvas></div>
                    </div>
                    <div class="block cell-kpi kpi-c2p">
                        <div class="kpi-label">Cart → Purchase <span class="agg-tag">(rate)</span></div>
                        <div class="kpi-value" id="sum-kpi-c2p"></div>
                        <div id="sum-kpi-c2p-delta"></div>
                    </div>
                </div>
            </div>

            <div class="block span-8 h-md">
                
                    <h3>Посетители и сессии <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">Сколько заходят на сайт</p>
                
                <div class="chart-wrap"><canvas id="sum-visitors-sessions"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="block span-6 h-md">
                
                    <h3>Сессии по типу девайсов <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">С каких девайсов чаще посещают сайт</p>
                
                <div class="chart-wrap"><canvas id="sum-device-sessions"></canvas></div>
            </div>
            <div class="block span-6 h-md">
                
                    <h3>Новые vs Вернувшиеся <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">Какая доля посетила сайт первый раз, а какая вернулась</p>
                
                <div class="chart-wrap"><canvas id="sum-new-returning"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="block span-6 h-md">
                
                    <h3>Время на сайте <span class="agg-tag">(median, sec)</span></h3>
                    <p class="meta">В разрезе устройств — на каких дольше проводят время</p>
                
                <div class="chart-wrap"><canvas id="sum-time-on-site"></canvas></div>
            </div>
            <div class="block span-6 h-md">
                
                    <h3>Bounce Rate <span class="agg-tag">(rate)</span></h3>
                    <p class="meta">С каких устройств чаще уходят (sessions_1page / sessions)</p>
                
                <div class="chart-wrap"><canvas id="sum-bounce-device"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="block span-12 h-md">
                
                    <h3>Источник трафика <span class="agg-tag">(sum)</span></h3>
                    <p class="meta">Какой источник трафика преобладает и его динамика</p>
                
                <div class="chart-wrap"><canvas id="sum-source-trend"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="block span-12 h-md">
                
                    <h3>Таблица по источнику трафика</h3>
                    <p class="meta">Значения за последний период + дельта vs avg прошлых периодов</p>
                
                <div class="data-table-wrap" style="overflow-x:auto;"><table class="data-table" id="sum-source-table">
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
                    </table></div>
            </div>
        </div>

        <div class="grid">
            <div class="block span-12 h-md">
                
                    <h3>Посетители по странам</h3>
                    <p class="meta">Значения за последний период + дельта vs avg прошлых периодов</p>
                
                <div class="data-table-wrap" style="overflow-x:auto;"><table class="data-table" id="sum-country-table">
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
                    </table></div>
            </div>
        </div>

        <div class="grid">
            <div class="block span-12 h-md">
                
                    <h3>ATC Rate + Purchase Rate <span class="agg-tag">(rate)</span></h3>
                    <p class="meta">ATC Rate = add_to_cart / sessions &nbsp;&middot;&nbsp; PR = purchase / sessions</p>
                
                <div class="chart-wrap"><canvas id="sum-atc-pr-trend"></canvas></div>
            </div>
        </div>

        <div class="grid">
            <div class="block span-6 h-md">
                <h3>Рейтинг ATC <span class="agg-tag">top-10</span></h3>
                <p class="meta">Комбинации Источник × Страна × Тип юзера (min 10 сессий)</p>
                <div class="data-table-wrap"><table class="data-table">
                    <thead>
                        <tr><th>Источник</th><th>Страна</th><th>Тип</th><th>Sessions</th><th>ATC Rate</th></tr>
                    </thead>
                    <tbody id="sum-ranking-atc"></tbody>
                </table></div>
            </div>
            <div class="block span-6 h-md">
                <h3>Рейтинг Purchase Rate <span class="agg-tag">top-10</span></h3>
                <p class="meta">Комбинации Источник × Страна × Тип юзера (min 10 сессий)</p>
                <div class="data-table-wrap"><table class="data-table">
                    <thead>
                        <tr><th>Источник</th><th>Страна</th><th>Тип</th><th>Sessions</th><th>PR</th></tr>
                    </thead>
                    <tbody id="sum-ranking-pr"></tbody>
                </table></div>
            </div>
        </div>

        <h2>Scroll Rate по сайту</h2>
        <p class="meta">
            <strong>Что это:</strong> GA4 шлёт событие <code>scroll</code>, когда пользователь долистал любую страницу до 90%. Здесь — % сессий, в которых это произошло хотя бы один раз (на любой странице сайта).<br>
            <strong>Зачем:</strong> высокий scroll rate = страницы вовлекают, пользователи дочитывают. Низкий = «посмотрели и ушли».
        </p>
        <div class="grid">
            <div class="block span-6 h-md">
                <h3>По устройствам</h3><p class="meta">% сессий со scroll до 90% (любая страница)</p>
                <div class="chart-wrap"><canvas id="sum-scroll-site-device"></canvas></div>
            </div>
            <div class="block span-6 h-md">
                <h3>По каналам</h3><p class="meta">% сессий со scroll до 90% (любая страница)</p>
                <div class="chart-wrap"><canvas id="sum-scroll-site-channel"></canvas></div>
            </div>
        </div>

        <h2>Cohort Retention</h2>
        <p class="meta">
            <strong>Что это:</strong> разрезаем пользователей по неделе их ПЕРВОГО визита (когорта) и смотрим, сколько % из них возвращались через 1, 2, 3… недель.<br>
            <strong>Как читать:</strong> над каждым столбиком сверху подписан размер когорты (новички за ту неделю). Цветные сегменты внутри — % этой когорты, который пришёл снова через N недель. На графике скрыта «Неделя 0», чтобы маленькие проценты возврата были видны — её можно включить в легенде.<br>
            <strong>Зачем:</strong> понять, удерживает ли Pinkspink пользователей. Растёт retention от когорты к когорте = улучшения работают.
        </p>
        <div class="grid">
            <div class="block span-12 h-md">
                <h3>Retention по когортам</h3><p class="meta">% вернувшихся (Неделя 0 скрыта по умолчанию — клик в легенде включит)</p>
                <div class="chart-wrap"><canvas id="sum-cohort"></canvas></div>
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
        <div class="block span-6 h-md" data-device-cell="mobile">
            <h3>Мобилка — этапы, сессии</h3>
            <div class="chart-wrap"><canvas id="stacked-mobile"></canvas></div>
        </div>
        <div class="block span-6 h-md" data-device-cell="desktop">
            <h3>Веб — этапы, сессии</h3>
            <div class="chart-wrap"><canvas id="stacked-desktop"></canvas></div>
        </div>
        <div class="block span-6 h-md" data-device-cell="mobile">
            <h3>Мобилка — конверсии между этапами, %</h3>
            <div class="chart-wrap"><canvas id="pct-mobile"></canvas></div>
        </div>
        <div class="block span-6 h-md" data-device-cell="desktop">
            <h3>Веб — конверсии между этапами, %</h3>
            <div class="chart-wrap"><canvas id="pct-desktop"></canvas></div>
        </div>
    </div>

    <h2>Кто добавляет в корзину и покупает</h2>
    <p class="meta">Период: {data['periods'][-1] if data['periods'] else '—'}</p>
    <div class="grid">
        <div class="block span-12 h-md">
            <div class="data-table-wrap"><table class="data-table">
                <thead><tr><th>Source</th><th>Страна</th><th>Сессии</th><th>Каталог</th><th>Товар</th><th>Корзина</th><th>Чекаут</th><th>Покупка</th></tr></thead>
                <tbody id="tbody-bottom-funnel">{bottom_funnel_html}</tbody>
            </table></div>
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
        <div class="block span-6 h-md">
            <h3>текущий период</h3>
            <div class="chart-wrap"><canvas id="bubble-channel-prod"></canvas></div>
        </div>
        <div class="block span-6 h-md">
            <h3>динамика, %</h3>
            <div class="chart-wrap"><canvas id="trend-channel-prod"></canvas></div>
        </div>
        <div class="block span-12 h-md" id="stage-table-prod">{stage_table_prod_html}</div>
    </div>

    <h3>Товар → Корзина</h3>
    <div class="bubble-filters" id="filter-channel-atc"></div>
    <div class="grid">
        <div class="block span-6 h-md">
            <h3>текущий период</h3>
            <div class="chart-wrap"><canvas id="bubble-channel-atc"></canvas></div>
        </div>
        <div class="block span-6 h-md">
            <h3>динамика, %</h3>
            <div class="chart-wrap"><canvas id="trend-channel-atc"></canvas></div>
        </div>
        <div class="block span-12 h-md" id="stage-table-atc">{stage_table_atc_html}</div>
    </div>

    <h3>Корзина → Чекаут</h3>
    <div class="bubble-filters" id="filter-channel-checkout"></div>
    <div class="grid">
        <div class="block span-6 h-md">
            <h3>текущий период</h3>
            <div class="chart-wrap"><canvas id="bubble-channel-checkout"></canvas></div>
        </div>
        <div class="block span-6 h-md">
            <h3>динамика, %</h3>
            <div class="chart-wrap"><canvas id="trend-channel-checkout"></canvas></div>
        </div>
        <div class="block span-12 h-md" id="stage-table-checkout">{stage_table_checkout_html}</div>
    </div>

    <h3>Чекаут → Покупка</h3>
    <div class="bubble-filters" id="filter-channel-purchase"></div>
    <div class="grid">
        <div class="block span-6 h-md">
            <h3>текущий период</h3>
            <div class="chart-wrap"><canvas id="bubble-channel-purchase"></canvas></div>
        </div>
        <div class="block span-6 h-md">
            <h3>динамика, %</h3>
            <div class="chart-wrap"><canvas id="trend-channel-purchase"></canvas></div>
        </div>
        <div class="block span-12 h-md" id="stage-table-purchase">{stage_table_purchase_html}</div>
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
        <div class="block span-12 h-md"><canvas id="analytics-per-card-time"></canvas></div>
    </div>
    <div class="grid">
        <div class="block span-6 h-md">
            <h3>По странам — <span data-grain-label="last_full">{last_full_label}</span></h3><p class="meta"><span data-grain-label="prev_avg">{prev_avg_label}</span></p>
            <div class="data-table-wrap" style="overflow:auto;"><table class="data-table" id="tbl-per-card-country">
                <thead><tr><th>Страна</th><th>Card views</th><th>Median sec</th><th>Δ Median</th><th>Mean sec</th><th>Δ Mean</th></tr></thead>
                <tbody>{per_card_country_rows}</tbody>
            </table></div>
        </div>
        <div class="block span-6 h-md">
            <h3>По source — <span data-grain-label="last_full">{last_full_label}</span></h3><p class="meta"><span data-grain-label="prev_avg">{prev_avg_label}</span></p>
            <div class="data-table-wrap" style="overflow:auto;"><table class="data-table" id="tbl-per-card-source">
                <thead><tr><th>Source</th><th>Card views</th><th>Median sec</th><th>Δ Median</th><th>Mean sec</th><th>Δ Mean</th></tr></thead>
                <tbody>{per_card_source_rows}</tbody>
            </table></div>
        </div>
    </div>

    <h2>Карточек за сессию — разрез по странам и source</h2>
    <p class="meta"><span data-grain-label="last_full">{last_full_label}</span>. Сколько карточек товара открывает один пользователь за сессию.</p>
    <div class="grid">
        <div class="block span-6 h-md">
            <h3>По странам</h3><p class="meta"><span data-grain-label="prev_avg">{prev_avg_label}</span></p>
            <div class="data-table-wrap" style="overflow:auto;"><table class="data-table" id="tbl-cards-country">
                <thead><tr><th>Страна</th><th>Сессии</th><th>Median карт.</th><th>Δ Median</th><th>Mean карт.</th><th>Δ Mean</th></tr></thead>
                <tbody>{cards_country_rows}</tbody>
            </table></div>
        </div>
        <div class="block span-6 h-md">
            <h3>По source</h3><p class="meta"><span data-grain-label="prev_avg">{prev_avg_label}</span></p>
            <div class="data-table-wrap" style="overflow:auto;"><table class="data-table" id="tbl-cards-source">
                <thead><tr><th>Source</th><th>Сессии</th><th>Median карт.</th><th>Δ Median</th><th>Mean карт.</th><th>Δ Mean</th></tr></thead>
                <tbody>{cards_source_rows}</tbody>
            </table></div>
        </div>
    </div>

    <h2>Топ-30 карточек товара</h2>
    <p class="meta">Mobile + desktop, без excluded стран. Сортировка — клик по любому заголовку колонки.</p>
    <div class="grid">
        <div class="block span-12">
            <div style="display:flex; gap:var(--sp-2); margin-bottom:var(--content-gap);">
                <button class="btn is-active" id="tp-period-week" onclick="setTopProductsPeriod('week', this)">Последняя неделя</button>
                <button class="btn" id="tp-period-4w" onclick="setTopProductsPeriod('agg_4w', this)">4 недели (агрегат)</button>
            </div>
            <div class="data-table-wrap">
                <table class="data-table" id="tbl-top-products">
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
    <div class="grid"><div class="block span-12 h-md"><canvas id="analytics-product-time"></canvas></div></div>

    <h2>Scroll на странице товара</h2>
    <p class="meta">
        <strong>Что это:</strong> GA4 шлёт событие <code>scroll</code>, когда пользователь долистал страницу до 90% высоты. Здесь — % сессий, в которых это произошло именно на странице товара (URL содержит <code>/products/</code>).<br>
        <strong>Зачем:</strong> низкий scroll = пользователи не дочитывают до фото внизу / кнопки IG / описания. Высокий = карточка прочитана.
    </p>
    <div class="grid">
        <div class="block span-6 h-md">
            <h3>По устройствам</h3><p class="meta">% сессий с view_item, в которых был scroll до 90%</p>
            <div class="chart-wrap"><canvas id="analytics-scroll-product-device"></canvas></div>
        </div>
        <div class="block span-6 h-md">
            <h3>По каналам</h3><p class="meta">% сессий с view_item, в которых был scroll до 90%</p>
            <div class="chart-wrap"><canvas id="analytics-scroll-product-channel"></canvas></div>
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
    <div class="grid"><div class="block span-12 h-md"><canvas id="analytics-catalog-depth"></canvas></div></div>

    </div><!-- end tab-analytics -->

    <script>
    // Unified mode: ship payloads for both grains and let the user flip with no reload.
    const DATA_BY_GRAIN = {json.dumps(_payloads_by_grain, ensure_ascii=False)};
    const _UNIFIED_MODE = {json.dumps(_unified_mode)};
    let currentGrain = {json.dumps(_default_grain)};
    let DATA = _UNIFIED_MODE && DATA_BY_GRAIN[currentGrain]
        ? DATA_BY_GRAIN[currentGrain]
        : {json.dumps(data, ensure_ascii=False)};

    {chart_js_defaults}

    // Tab switching with lazy chart init
    let tabInited = {{ summary: false, overview: false, funnels: false, analytics: false }};

    // Global filter state. Three ways for a block to react to the device filter:
    //   1. data-device-cell="mobile|desktop" on its grid cell — entire cell hides when not selected.
    //   2. registerDeviceChart(chart) — for charts that hold per-device datasets in one canvas
    //      (dataset.label === 'mobile'|'desktop'|'tablet'); non-matching datasets get hidden.
    //   3. registerFilterHandler(fn) — for charts whose datasets aren't labeled by device but the
    //      payload ships pre-aggregated per-device slices; handler swaps in the right slice.
    const FILTERS = {{ device: 'all' }};
    let deviceCharts = [];
    let filterHandlers = [];

    // Grain-aware text snippets used by SSR'd labels with [data-grain-label] markers.
    // applyGrainLabels rewrites textContent in-place when the user flips D/W.
    const GRAIN_LABELS = {{
        day:   {{ last_full: "последний полный день",   prev_avg: "Δ vs avg прошлых 7 дней",   prev_short: "Δ vs ср. 7 дней"  }},
        week:  {{ last_full: "последняя полная неделя", prev_avg: "Δ vs avg прошлых 4 недель", prev_short: "Δ vs ср. 4 пред." }},
        month: {{ last_full: "последний полный месяц",  prev_avg: "Δ vs avg прошлых 3 месяцев", prev_short: "Δ vs ср. 3 мес." }},
    }};
    function applyGrainLabels() {{
        const labels = GRAIN_LABELS[currentGrain] || GRAIN_LABELS.week;
        document.querySelectorAll('[data-grain-label]').forEach(el => {{
            const key = el.dataset.grainLabel;
            if (labels[key]) el.textContent = labels[key];
        }});
    }}

    // Destroy every Chart.js instance currently in the page. Used on grain switch
    // so the next init runs against fresh canvases. Chart.instances is keyed by
    // chart id; we copy keys first because destroy() mutates the collection.
    function _destroyAllCharts() {{
        const ids = Object.keys(Chart.instances || {{}});
        ids.forEach(id => {{
            const c = Chart.instances[id];
            if (c && typeof c.destroy === 'function') {{
                try {{ c.destroy(); }} catch (e) {{ /* swallow */ }}
            }}
        }});
    }}

    // ---- JS renderers used to rebuild SSR'd chunks when grain switches ----
    // Mirrors render_card_html() / _render_slider_set() on the Python side.
    const _DEV_PREFIXES = {{ all: '', mobile: 'mobile-', desktop: 'desktop-', tablet: 'tablet-' }};

    function _flagOf(country) {{
        return ((typeof COUNTRY_FLAGS !== 'undefined' ? COUNTRY_FLAGS[country] : null) || '🏳️') + ' ' + country;
    }}

    function _deltaHtml(value, suffix, invert) {{
        suffix = suffix || '';
        if (value === null || value === undefined) return '<span class="delta neutral">—</span>';
        if (value > 0) {{
            const color = invert ? 'red' : 'green';
            return '<span class="delta ' + color + '">↑ +' + value + suffix + '</span>';
        }}
        if (value < 0) {{
            const color = invert ? 'green' : 'red';
            return '<span class="delta ' + color + '">↓ ' + value + suffix + '</span>';
        }}
        return '<span class="delta neutral">→ 0' + suffix + '</span>';
    }}

    function _renderCardHtml(card, nameKey, devPrefix) {{
        devPrefix = devPrefix || '';
        const name = card[nameKey];
        let borderStyle = '';
        let canvasId;
        if (nameKey === 'channel') {{
            borderStyle = ' style="border-top: 4px solid ' + card.color + '"';
            canvasId = devPrefix + 'funnel-channel-' + name.toLowerCase().replace(/\\s/g, '-');
        }} else {{
            canvasId = devPrefix + 'funnel-source-' + name.replace(/\\./g, '_').replace(/[()]/g, '').replace(/ /g, '-');
        }}
        const topCountriesHtml = (card.top_countries || []).map(pair =>
            '<div class="country-row"><span>' + _flagOf(pair[0]) + '</span><span>' + pair[1] + '</span></div>'
        ).join('');
        const lowN = (card.sessions || 0) < 50 ? '<span class="low-n-badge">&#9888; low n</span>' : '';
        return ''
            + '<div class="block"' + borderStyle + '>'
            +   '<h3>' + name + lowN + '</h3>'
            +   '<canvas id="' + canvasId + '"></canvas>'
            +   '<div class="metrics">'
            +     '<div class="metric"><span class="label">Сессии</span><span class="value">' + card.sessions + '</span>' + _deltaHtml(card.delta_sessions) + '</div>'
            +     '<div class="metric"><span class="label">Доля</span><span class="value">' + card.share + '%</span></div>'
            +     '<div class="metric"><span class="label">ER</span><span class="value">' + card.er + '%</span>' + _deltaHtml(card.delta_er, ' п.п.') + '</div>'
            +     '<div class="metric"><span class="label">Median sec</span><span class="value">' + card.median_sec + 's</span>' + _deltaHtml(card.delta_median, 's') + '</div>'
            +     '<div class="metric"><span class="label">Глубина 2+</span><span class="value">' + card.deep_pct + '%</span>' + _deltaHtml(card.delta_deep, ' п.п.') + '</div>'
            +     '<div class="metric"><span class="label">Карточек med / mean</span><span class="value">' + (card.median_products || 0) + ' / ' + card.avg_products + '</span>' + _deltaHtml(card.delta_products) + '</div>'
            +   '</div>'
            +   '<div class="top-countries"><h4>Топ 5 стран</h4>' + topCountriesHtml + '</div>'
            + '</div>';
    }}

    function _renderSliderSet(cardGroups, nameKey) {{
        // Outputs 4 sliders, one per device slice. Each slider is a complete view
        // for that slice; only the active slice is shown (exact-match semantics).
        // Non-active slices ship with display:none so the page doesn't flash before
        // applyDeviceVisibility() runs.
        return ['all', 'mobile', 'desktop', 'tablet'].map(dev => {{
            const cards = cardGroups[dev] || [];
            const prefix = _DEV_PREFIXES[dev] || '';
            const inner = cards.map(c => _renderCardHtml(c, nameKey, prefix)).join('');
            const hidden = dev === FILTERS.device ? '' : ' style="display:none"';
            return '<div class="slider" data-device-slice="' + dev + '"' + hidden + '>' + inner + '</div>';
        }}).join('');
    }}

    // ---- setGrain: swap DATA, destroy + re-init the active tab ----
    function setGrain(grain, btn) {{
        if (!_UNIFIED_MODE || !DATA_BY_GRAIN[grain] || grain === currentGrain) return;
        // Toggle active class on the D/W buttons (siblings of btn in grain-nav).
        if (btn && btn.parentElement) {{
            btn.parentElement.querySelectorAll('[data-grain]').forEach(b => b.classList.remove('is-active'));
            btn.classList.add('is-active');
        }}
        currentGrain = grain;
        DATA = DATA_BY_GRAIN[grain];
        // Update grain-aware label text everywhere it's marked with [data-grain-label].
        applyGrainLabels();

        // Tear down all existing chart instances so canvases are clean.
        _destroyAllCharts();
        deviceCharts = [];
        filterHandlers = [];
        bubbleCharts = {{}};
        tabInited = {{ summary: false, overview: false, funnels: false, analytics: false }};

        // Rebuild SSR'd slider HTML for the new grain. The chart-wrap auto-wrap
        // runs once per page-load, so we re-wrap canvases inside the new HTML.
        const channelWrap = document.getElementById('channel-cards-wrap');
        if (channelWrap) channelWrap.innerHTML = _renderSliderSet(DATA.channel_cards || {{}}, 'channel');
        const sourceWrap  = document.getElementById('source-cards-wrap');
        if (sourceWrap)  sourceWrap.innerHTML  = _renderSliderSet(DATA.source_cards  || {{}}, 'source');
        document.querySelectorAll('canvas').forEach(c => {{
            if (c.parentElement && c.parentElement.classList.contains('chart-wrap')) return;
            const wrap = document.createElement('div');
            wrap.className = 'chart-wrap';
            c.parentNode.insertBefore(wrap, c);
            wrap.appendChild(c);
        }});

        // Re-render the active tab from scratch.
        const activeTab = document.querySelector('.tab.is-active');
        const tabKey = activeTab
            ? (activeTab.getAttribute('onclick') || '').match(/'([^']+)'/)
            : null;
        const target = tabKey ? tabKey[1] : 'summary';
        if (target === 'summary') initSummaryTab();
        else if (target === 'funnels') initFunnelsTab();
        else if (target === 'analytics') initAnalyticsTab();
        tabInited[target] = true;
        // Re-apply device visibility (data-device-cell) after the new DOM lands.
        applyDeviceVisibility();
    }}
    function registerDeviceChart(chart) {{ if (chart) deviceCharts.push(chart); }}
    function registerFilterHandler(fn) {{ filterHandlers.push(fn); fn(FILTERS); }}

    function applyDeviceVisibility() {{
        // data-device-cell: additive (Block 1 funnels — show on 'all' OR matching device)
        document.querySelectorAll('[data-device-cell]').forEach(el => {{
            const cell = el.dataset.deviceCell;
            const visible = FILTERS.device === 'all' || FILTERS.device === cell;
            el.style.display = visible ? '' : 'none';
        }});
        // data-device-slice: exact-match (sliders — each slice is a complete view)
        document.querySelectorAll('[data-device-slice]').forEach(el => {{
            el.style.display = el.dataset.deviceSlice === FILTERS.device ? '' : 'none';
        }});
        deviceCharts.forEach(chart => {{
            chart.data.datasets.forEach(ds => {{
                ds.hidden = FILTERS.device !== 'all' && ds.label !== FILTERS.device;
            }});
            chart.update('none');
        }});
        filterHandlers.forEach(fn => fn(FILTERS));
    }}

    function setDeviceFilter(device, btn) {{
        btn.parentElement.querySelectorAll('.btn').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        FILTERS.device = device;
        applyDeviceVisibility();
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
    }}

    // =========================================================================
    // REACTIVE COUNTRY FILTER (Phase 2 of joyful-mapping-sutherland.md)
    // -------------------------------------------------------------------------
    // Recomputes the 6 Funnels-tab blocks on the fly when checkbox selection
    // changes. Reads from per-country payload keys (funnel_by_country,
    // channel_country, source_country, bottom_funnel_full, stage_tables_full,
    // bubble_channel_country) shipped in Phase 1.
    //
    // Stays inert until user toggles a checkbox: FILTERS.countries === null
    // means SSR (Python-rendered, default-excluded) data. First user change
    // populates the Set and triggers full recompute via filterHandlers.
    //
    // Limitation: median_eng_sec / avg_product_views / median_product_views
    // are NOT in the slim per-country payload. Those card cells stay at SSR
    // values. Sessions, share, ER, deep%, top-5 countries, funnel bars, and
    // bubble + trend stages all recompute live.
    // =========================================================================
    FILTERS.countries = null;
    const _N_PREV_BY_GRAIN = {{ day: 7, week: 4, month: 3 }};
    const _CC_FUNNEL_FIELDS = ['funnel_homepage','funnel_catalog','funnel_product','funnel_atc','funnel_checkout','funnel_purchase'];

    function getSelectedCountries() {{
        const set = new Set();
        document.querySelectorAll('.country-section input[type="checkbox"]:checked')
            .forEach(cb => set.add(cb.dataset.country));
        return set;
    }}

    function _safeRate(num, den) {{ return den ? Math.round(num / den * 1000) / 10 : 0; }}
    function _avgArr(arr) {{ return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0; }}

    // =========================================================================
    // _aggregateRows — JS mirror of Python's aggregate() (generate_report.py:1354).
    // Sums summable fields, computes derived rates/medians per group key.
    // Used by Summary + Analytics recompute paths (Phase 5/6) so country filter
    // reaches every chart on the dashboard, not just the Funnels tab.
    // =========================================================================
    const _AGG_SUMMABLE = [
        'sessions', 'users', 'engaged_sessions',
        'sessions_1page', 'sessions_2_5pages', 'sessions_over5pages',
        'funnel_homepage', 'funnel_catalog', 'funnel_product',
        'funnel_atc', 'funnel_checkout', 'funnel_purchase',
        'revenue', 'new_users', 'returning_users',
    ];
    function _aggregateRows(rows, groupKeys, filterFn) {{
        const result = new Map();
        for (const r of rows) {{
            if (filterFn && !filterFn(r)) continue;
            const key = groupKeys.map(k => String(r[k])).join('||');
            let d = result.get(key);
            if (!d) {{
                d = {{ _key: groupKeys.map(k => r[k]) }};
                for (const f of _AGG_SUMMABLE) d[f] = 0;
                d._eng_ms_vals = [];
                d._avg_pv_vals = [];
                d._med_pv_vals = [];
                result.set(key, d);
            }}
            for (const f of _AGG_SUMMABLE) d[f] += (r[f] || 0);
            const sess = r.sessions || 0;
            if (r.median_eng_sec != null && sess > 0) {{
                for (let i = 0; i < sess; i++) d._eng_ms_vals.push(r.median_eng_sec);
            }}
            if (r.avg_product_views != null && sess > 0) {{
                for (let i = 0; i < sess; i++) d._avg_pv_vals.push(r.avg_product_views);
            }}
            if (r.median_product_views != null && sess > 0) {{
                for (let i = 0; i < sess; i++) d._med_pv_vals.push(r.median_product_views);
            }}
        }}
        for (const d of result.values()) {{
            const s = d.sessions;
            d.er = s ? Math.round(d.engaged_sessions / s * 1000) / 10 : 0;
            d.bounce_rate = s ? Math.round(d.sessions_1page / s * 1000) / 10 : 0;
            d.deep_pct = s ? Math.round((d.sessions_2_5pages + d.sessions_over5pages) / s * 1000) / 10 : 0;
            d.cr = s ? Math.round(d.funnel_purchase / s * 10000) / 100 : 0;
            d.atc_rate = s ? Math.round(d.funnel_atc / s * 10000) / 100 : 0;
            d.cart_to_purchase = d.funnel_atc ? Math.min(100, Math.round(d.funnel_purchase / d.funnel_atc * 1000) / 10) : 0;
            d.revenue_per_session = s ? Math.round(d.revenue / s * 100) / 100 : 0;
            d.cat_to_prod = d.funnel_catalog ? Math.min(100, Math.round(d.funnel_product / d.funnel_catalog * 1000) / 10) : 0;
            d.prod_to_atc = d.funnel_product ? Math.min(100, Math.round(d.funnel_atc / d.funnel_product * 1000) / 10) : 0;
            d.atc_to_checkout = d.funnel_atc ? Math.min(100, Math.round(d.funnel_checkout / d.funnel_atc * 1000) / 10) : 0;
            d.checkout_to_purchase = d.funnel_checkout ? Math.min(100, Math.round(d.funnel_purchase / d.funnel_checkout * 1000) / 10) : 0;
            // Medians: sort + middle. Mean is also computed here so that JS callers
            // can swap them in if they prefer summable-friendly approximations.
            const ev = d._eng_ms_vals;
            d.median_eng_sec = ev.length ? Math.round(ev.sort((a, b) => a - b)[Math.floor(ev.length / 2)] * 10) / 10 : 0;
            const av = d._avg_pv_vals;
            d.avg_product_views = av.length ? Math.round(av.reduce((a, b) => a + b, 0) / av.length * 10) / 10 : 0;
            const mv = d._med_pv_vals;
            d.median_product_views = mv.length ? Math.round(mv.sort((a, b) => a - b)[Math.floor(mv.length / 2)] * 10) / 10 : 0;
            // avg_pages is what the existing Summary tables read for the "Стр./сесс." column.
            d.avg_pages = d.avg_product_views;  // proxy; matches Python builders for these breakdowns
            delete d._eng_ms_vals; delete d._avg_pv_vals; delete d._med_pv_vals;
        }}
        return result;
    }}

    // Returns rows filtered by current country selection (or default-excluded set
    // when the user hasn't toggled anything).
    const _DEFAULT_EXCLUDED = new Set((DATA.excluded_countries || []));
    function _activeRows() {{
        const all = DATA.raw_rows || [];
        if (FILTERS.countries) {{
            const picked = FILTERS.countries;
            return all.filter(r => picked.has(r.country));
        }}
        return all.filter(r => !_DEFAULT_EXCLUDED.has(r.country));
    }}

    // Compute % delta of current period vs avg of N previous periods.
    function _computeDeltaVsPrev(values, nPrev) {{
        if (!values || values.length < 2) return null;
        const cur = values[values.length - 1];
        const start = Math.max(0, values.length - 1 - nPrev);
        const prev = values.slice(start, values.length - 1);
        if (!prev.length) return null;
        const avg = prev.reduce((a, b) => a + b, 0) / prev.length;
        if (avg === 0) return null;
        return Math.round((cur - avg) / avg * 1000) / 10;
    }}
    // Absolute delta in p.p. (for rate metrics).
    function _computeDeltaPp(values, nPrev) {{
        if (!values || values.length < 2) return null;
        const cur = values[values.length - 1];
        const start = Math.max(0, values.length - 1 - nPrev);
        const prev = values.slice(start, values.length - 1);
        if (!prev.length) return null;
        const avg = prev.reduce((a, b) => a + b, 0) / prev.length;
        return Math.round((cur - avg) * 100) / 100;
    }}

    // =========================================================================
    // _rebuildSummaryData(activeRows) — JS mirror of Python's summary_data builder
    // (generate_report.py:2280-2700ish). Produces exactly the shape that existing
    // Summary filter-handlers consume, so country-reactive recompute drops in
    // without touching per-chart handlers.
    // =========================================================================
    function _rebuildSummaryData(rows, periods, nPrev) {{
        const devices = ['all', 'mobile', 'desktop', 'tablet'];
        const trackedChannels = ['Social', 'Paid', 'Direct', 'Organic', 'Referral'];
        const devMatch = (dev) => (dev === 'all' ? () => true : (r) => r.device === dev);

        function trVals(agg, groupKey) {{
            return periods.map(p => agg.get([...(Array.isArray(groupKey) ? groupKey : [groupKey]), p].join('||'))?.[0] || null);
        }}

        // Per-period agg per device — used by KPI / trends / etc.
        const ptByDev = {{}};
        for (const dev of devices) {{
            ptByDev[dev] = _aggregateRows(rows, ['period'], devMatch(dev));
        }}
        const lookup = (m, dev) => periods.map(p => {{
            const e = ptByDev[dev].get(p);
            return e ? (e[m] || 0) : 0;
        }});
        const lastVal = (m, dev) => {{
            if (!periods.length) return 0;
            const e = ptByDev[dev].get(periods[periods.length - 1]);
            return e ? (e[m] || 0) : 0;
        }};

        // ---- KPI per device ----
        const kpi = {{}};
        for (const dev of devices) {{
            const tr = (m) => lookup(m, dev);
            kpi[dev] = {{
                revenue_per_session: {{ value: lastVal('revenue_per_session', dev), delta: _computeDeltaVsPrev(tr('revenue_per_session'), nPrev), trend: tr('revenue_per_session'), agg: 'mean' }},
                revenue:             {{ value: Math.round(lastVal('revenue', dev) * 100) / 100, delta: _computeDeltaVsPrev(tr('revenue'), nPrev), trend: tr('revenue').map(v => Math.round(v * 100) / 100), agg: 'sum' }},
                atc_rate:            {{ value: lastVal('atc_rate', dev), delta: _computeDeltaPp(tr('atc_rate'), nPrev), trend: tr('atc_rate'), agg: 'rate' }},
                purchase_rate:       {{ value: lastVal('cr', dev), delta: _computeDeltaPp(tr('cr'), nPrev), trend: tr('cr'), agg: 'rate' }},
                cart_to_purchase:    {{ value: lastVal('cart_to_purchase', dev), delta: _computeDeltaPp(tr('cart_to_purchase'), nPrev), trend: tr('cart_to_purchase'), agg: 'rate' }},
            }};
        }}

        // ---- Visitors & sessions ----
        const visitorsSessions = {{ labels: periods }};
        for (const dev of devices) {{
            visitorsSessions[dev] = {{
                visitors: lookup('users', dev),
                sessions: lookup('sessions', dev),
            }};
        }}

        // ---- Device sessions per period (mobile/desktop/tablet) ----
        const devByPeriod = _aggregateRows(rows, ['period', 'device']);
        const deviceSessions = {{ labels: periods }};
        for (const d of ['mobile', 'desktop', 'tablet']) {{
            deviceSessions[d] = periods.map(p => {{
                const e = devByPeriod.get([p, d].join('||'));
                return e ? (e.sessions || 0) : 0;
            }});
        }}

        // ---- New vs Returning ----
        const newRet = {{ labels: periods }};
        for (const dev of devices) {{
            newRet[dev] = {{
                new: lookup('new_users', dev),
                returning: lookup('returning_users', dev),
            }};
        }}

        // ---- Time on site (median) per device ----
        const timeOnSite = {{ labels: periods }};
        for (const d of ['mobile', 'desktop', 'tablet']) {{
            timeOnSite[d] = periods.map(p => {{
                const e = devByPeriod.get([p, d].join('||'));
                return e ? (e.median_eng_sec || 0) : 0;
            }});
        }}

        // ---- Bounce by device ----
        const bounceDevice = {{ labels: periods }};
        for (const d of ['mobile', 'desktop', 'tablet']) {{
            bounceDevice[d] = periods.map(p => {{
                const e = devByPeriod.get([p, d].join('||'));
                return e ? (e.bounce_rate || 0) : 0;
            }});
        }}

        // ---- Source trend (per device, per channel) ----
        const sourceTrend = {{ labels: periods }};
        for (const dev of devices) {{
            const chPp = _aggregateRows(rows, ['period', 'channel'], devMatch(dev));
            const ptDev = ptByDev[dev];
            const sources = trackedChannels.map(ch => {{
                const sessionsArr = periods.map(p => {{
                    const e = chPp.get([p, ch].join('||'));
                    return e ? (e.sessions || 0) : 0;
                }});
                const totals = periods.map(p => {{
                    const e = ptDev.get(p);
                    return e ? (e.sessions || 0) : 0;
                }});
                const shares = sessionsArr.map((s, i) => totals[i] > 0 ? Math.round(s / totals[i] * 1000) / 10 : 0);
                return {{ name: ch, sessions: sessionsArr, share_pct: shares }};
            }});
            sourceTrend[dev] = sources;
        }}

        // ---- Source / Country tables (per-device, with per-metric deltas) ----
        const sourceMetrics = [
            ['sessions', 'rel'], ['users', 'rel'],
            ['new_users', 'rel'], ['returning_users', 'rel'],
            ['er', 'pp'], ['bounce_rate', 'pp'],
            ['median_eng_sec', 'rel'], ['avg_pages', 'rel'],
            ['atc_rate', 'pp'], ['cr', 'pp'],
        ];
        function buildTable(groupKey, rows_, devFilter, minSessions) {{
            const agg = _aggregateRows(rows_, ['period', groupKey], devFilter);
            const allKeys = new Set();
            for (const k of agg.keys()) allKeys.add(k.split('||')[1]);
            const out = [];
            for (const key of allKeys) {{
                const trends = {{}};
                for (const [m, _] of sourceMetrics) {{
                    trends[m] = periods.map(p => {{
                        const e = agg.get([p, key].join('||'));
                        return e ? (e[m] || 0) : 0;
                    }});
                }}
                if (trends[sourceMetrics[0][0]].reduce((a, b) => a + b, 0) === 0) continue;
                const row = {{ name: key }};
                for (const [m, dt] of sourceMetrics) {{
                    const cur = trends[m][trends[m].length - 1] || 0;
                    let delta;
                    if (dt === 'pp') delta = _computeDeltaPp(trends[m], nPrev);
                    else if (dt === 'rel') delta = _computeDeltaVsPrev(trends[m], nPrev);
                    else delta = null;
                    row[m] = {{ value: cur, delta, delta_type: dt }};
                }}
                out.push(row);
            }}
            const sorted = out.sort((a, b) => (b.sessions.value || 0) - (a.sessions.value || 0));
            return minSessions ? sorted.filter(r => r.sessions.value >= minSessions).slice(0, 20) : sorted;
        }}
        const sourceTable = {{}};
        const countryTable = {{}};
        for (const dev of devices) {{
            sourceTable[dev] = buildTable('channel', rows, devMatch(dev));
            countryTable[dev] = buildTable('country', rows, devMatch(dev), 5);
        }}

        // ---- ATC + PR trend per device ----
        const atcPrTrend = {{ labels: periods }};
        for (const dev of devices) {{
            atcPrTrend[dev] = {{
                atc_rate: lookup('atc_rate', dev),
                purchase_rate: lookup('cr', dev),
            }};
        }}

        // ---- Rankings (top-N source × country combos at current period) ----
        function buildRanking(rows_, sortMetric, devFilter, topN, minSessions) {{
            if (!periods.length) return [];
            const curP = periods[periods.length - 1];
            const agg = _aggregateRows(rows_, ['source', 'country'], r => devFilter(r) && r.period === curP);
            const out = [];
            for (const d of agg.values()) {{
                if (d.sessions < minSessions) continue;
                const newShare = d.sessions > 0 ? d.new_users / d.sessions : 0;
                const userType = newShare > 0.6 ? 'New' : (newShare < 0.4 ? 'Returning' : 'Mixed');
                out.push({{
                    source: d._key[0],
                    country: d._key[1],
                    user_type: userType,
                    sessions: d.sessions,
                    atc_rate: d.atc_rate,
                    purchase_rate: d.cr,
                    metric_value: d[sortMetric],
                }});
            }}
            return out.sort((a, b) => (b.metric_value || 0) - (a.metric_value || 0)).slice(0, topN);
        }}
        const rankingAtc = {{}};
        const rankingPr = {{}};
        for (const dev of devices) {{
            rankingAtc[dev] = buildRanking(rows, 'atc_rate', devMatch(dev), 10, 10);
            rankingPr[dev]  = buildRanking(rows, 'cr',       devMatch(dev), 10, 10);
        }}

        return {{
            n_prev: nPrev,
            kpi,
            visitors_sessions: visitorsSessions,
            device_sessions: deviceSessions,
            new_returning: newRet,
            time_on_site: timeOnSite,
            bounce_device: bounceDevice,
            source_trend: sourceTrend,
            source_table: sourceTable,
            country_table: countryTable,
            atc_pr_trend: atcPrTrend,
            ranking_atc: rankingAtc,
            ranking_pr: rankingPr,
        }};
    }}

    // Build a delta-span via DOM API (textContent only — no HTML parsing).
    function _buildDeltaSpan(value, suffix) {{
        const span = document.createElement('span');
        if (value == null) {{
            span.className = 'delta neutral';
            span.textContent = '—';
            return span;
        }}
        if (value > 0) {{
            span.className = 'delta green';
            span.textContent = '↑ +' + value + suffix;
        }} else if (value < 0) {{
            span.className = 'delta red';
            span.textContent = '↓ ' + value + suffix;
        }} else {{
            span.className = 'delta neutral';
            span.textContent = '→ 0' + suffix;
        }}
        return span;
    }}

    // Sum {{country: {{period: {{fields}}}}}} across `picked` countries at one period.
    function _sumByCountryAtPeriod(byCountry, period, picked) {{
        const agg = {{
            sessions: 0, engaged_sessions: 0,
            sessions_1page: 0, sessions_2_5pages: 0, sessions_over5pages: 0,
            funnel_homepage: 0, funnel_catalog: 0, funnel_product: 0,
            funnel_atc: 0, funnel_checkout: 0, funnel_purchase: 0,
        }};
        for (const country in byCountry) {{
            if (!picked.has(country)) continue;
            const v = byCountry[country][period];
            if (!v) continue;
            for (const k in agg) agg[k] += (v[k] || 0);
        }}
        return agg;
    }}

    // Sum a flat {{country: {{fields}}}} bucket (no period dim) — for bubble_channel_country.
    function _sumByCountryFlat(byCountry, picked) {{
        const agg = {{
            sessions: 0,
            funnel_catalog: 0, funnel_product: 0,
            funnel_atc: 0, funnel_checkout: 0, funnel_purchase: 0,
        }};
        for (const country in byCountry) {{
            if (!picked.has(country)) continue;
            const v = byCountry[country];
            if (!v) continue;
            for (const k in agg) agg[k] += (v[k] || 0);
        }}
        return agg;
    }}

    // Total sessions across all countries (selected) for a device + period.
    // Denominator for share% on channel/source cards.
    function _totalSessionsAt(dev, period, picked) {{
        const fbc = ((DATA.funnel_by_country || {{}})[dev]) || {{}};
        const countries = fbc[period] || {{}};
        let total = 0;
        for (const c in countries) {{
            if (picked.has(c)) total += (countries[c].sessions || 0);
        }}
        return total;
    }}

    // ---------- Block 1: per-period funnel bars (mobile + desktop) ----------
    function recomputeFunnelByCountry(picked) {{
        const fbc = DATA.funnel_by_country || {{}};
        const periods = DATA.periods || [];
        [['stacked-mobile', 'mobile'], ['stacked-desktop', 'desktop']].forEach(([id, dev]) => {{
            const chart = Chart.getChart(id);
            if (!chart) return;
            const byPeriod = fbc[dev] || {{}};
            chart.data.datasets.forEach((ds, i) => {{
                const field = _CC_FUNNEL_FIELDS[i];
                ds.data = periods.map(p => {{
                    const countries = byPeriod[p] || {{}};
                    let sum = 0;
                    for (const c in countries) {{
                        if (picked.has(c)) sum += (countries[c][field] || 0);
                    }}
                    return sum;
                }});
            }});
            chart.update('none');
        }});
    }}

    // ---------- Block 2 + 3: Channel / source cards ----------
    function _recomputeCardSet(payloadKey, type, picked, dev) {{
        const groups = (DATA[payloadKey] || {{}})[dev];
        if (!groups) return;
        const periods = DATA.periods || [];
        if (!periods.length) return;
        const curPeriod = periods[periods.length - 1];
        const nPrev = _N_PREV_BY_GRAIN[currentGrain] || 4;
        const prevStart = Math.max(0, periods.length - 1 - nPrev);
        const totalSessions = _totalSessionsAt(dev, curPeriod, picked);
        const sliceEl = document.querySelector('[data-device-slice="' + dev + '"]');
        if (!sliceEl) return;

        Object.keys(groups).forEach(name => {{
            const byCountry = groups[name];
            // Find card via stable data-card-* attrs (added in Phase 2 to render_card_html)
            const cards = sliceEl.querySelectorAll('[data-card-type="' + type + '"]');
            let card = null;
            for (const c of cards) {{
                if (c.dataset.cardName === name) {{ card = c; break; }}
            }}
            if (!card) return;
            const canvas = card.querySelector('canvas');

            const perPeriod = periods.map(p => _sumByCountryAtPeriod(byCountry, p, picked));
            const cur = perPeriod[perPeriod.length - 1];
            const prev = perPeriod.slice(prevStart, perPeriod.length - 1);

            // Funnel bar chart
            if (canvas) {{
                const chart = Chart.getChart(canvas);
                if (chart) {{
                    chart.data.datasets.forEach((ds, i) => {{
                        ds.data = perPeriod.map(s => s[_CC_FUNNEL_FIELDS[i]]);
                    }});
                    chart.update('none');
                }}
            }}

            // Cur-period scalar metrics
            const sessions = cur.sessions;
            const er = _safeRate(cur.engaged_sessions, cur.sessions);
            const deep = _safeRate(cur.sessions_2_5pages + cur.sessions_over5pages, cur.sessions);
            const share = totalSessions ? Math.round(sessions / totalSessions * 1000) / 10 : 0;

            // Deltas vs avg of prev N periods
            const avgSessions = _avgArr(prev.map(s => s.sessions));
            const avgEr = _avgArr(prev.map(s => _safeRate(s.engaged_sessions, s.sessions)));
            const avgDeep = _avgArr(prev.map(s => _safeRate(s.sessions_2_5pages + s.sessions_over5pages, s.sessions)));
            const dSess = avgSessions > 0 ? Math.round((sessions - avgSessions) / avgSessions * 1000) / 10 : null;
            const dEr   = (avgEr > 0 || er > 0) ? Math.round((er - avgEr) * 10) / 10 : null;
            const dDeep = (avgDeep > 0 || deep > 0) ? Math.round((deep - avgDeep) * 10) / 10 : null;

            _setMetric(card, 'sessions', String(sessions), _buildDeltaSpan(dSess, '%'));
            _setMetric(card, 'share', share + '%', null);
            _setMetric(card, 'er', er + '%', _buildDeltaSpan(dEr, ' п.п.'));
            _setMetric(card, 'deep', deep + '%', _buildDeltaSpan(dDeep, ' п.п.'));
            // 'median_sec' and 'products' stay at SSR — not summable.

            // Top-5 countries (current period)
            const top = [];
            for (const country in byCountry) {{
                if (!picked.has(country)) continue;
                const v = byCountry[country][curPeriod];
                if (!v || !v.sessions) continue;
                top.push([country, v.sessions]);
            }}
            top.sort((a, b) => b[1] - a[1]);
            _renderTopCountries(card, top.slice(0, 5));
        }});
    }}

    // Replace .metric value + delta in-place via DOM API (no HTML parsing).
    function _setMetric(card, metric, value, deltaEl) {{
        const el = card.querySelector('.metric[data-metric="' + metric + '"]');
        if (!el) return;
        const valEl = el.querySelector('.value');
        if (valEl) valEl.textContent = value;
        if (deltaEl) {{
            const oldDelta = el.querySelector('.delta');
            if (oldDelta) oldDelta.replaceWith(deltaEl);
        }}
    }}

    // Rebuild top-5 country list via DOM API.
    function _renderTopCountries(card, top) {{
        const wrap = card.querySelector('.top-countries');
        if (!wrap) return;
        while (wrap.firstChild) wrap.removeChild(wrap.firstChild);
        const h4 = document.createElement('h4');
        h4.textContent = 'Топ 5 стран';
        wrap.appendChild(h4);
        top.forEach(([c, s]) => {{
            const row = document.createElement('div');
            row.className = 'country-row';
            const flagSpan = document.createElement('span');
            flagSpan.textContent = COUNTRY_FLAGS[c] || '🏳️';
            const sessSpan = document.createElement('span');
            sessSpan.textContent = String(s);
            row.appendChild(flagSpan);
            row.appendChild(sessSpan);
            wrap.appendChild(row);
        }});
    }}

    function recomputeChannelCards(picked, dev) {{ _recomputeCardSet('channel_country', 'channel', picked, dev); }}
    function recomputeSourceCards(picked, dev)  {{ _recomputeCardSet('source_country',  'source',  picked, dev); }}

    // ---------- Block 5 helpers — used by the bubble device-filter handler ----------
    // Builds the items array (per-channel summed over picked countries, current period)
    // that bubbleChart consumes. Mirrors Python's build_bubble_data structure.
    function _ccRecomputeBubbleItems(dev, picked) {{
        const bcc = (DATA.bubble_channel_country || {{}})[dev] || {{}};
        const chc = (DATA.channel_country || {{}})[dev] || {{}};
        const periods = DATA.periods || [];
        const items = [];
        Object.keys(bcc).forEach(ch => {{
            const summed = _sumByCountryFlat(bcc[ch], picked);
            items.push({{
                name: ch,
                sessions: summed.sessions,
                funnel_catalog: summed.funnel_catalog,
                funnel_product: summed.funnel_product,
                funnel_atc: summed.funnel_atc,
                funnel_checkout: summed.funnel_checkout,
                funnel_purchase: summed.funnel_purchase,
                cat_to_prod:          summed.funnel_catalog ? Math.round(summed.funnel_product   / summed.funnel_catalog  * 1000) / 10 : 0,
                prod_to_atc:          summed.funnel_product ? Math.round(summed.funnel_atc       / summed.funnel_product  * 1000) / 10 : 0,
                atc_to_checkout:      summed.funnel_atc     ? Math.round(summed.funnel_checkout  / summed.funnel_atc      * 1000) / 10 : 0,
                checkout_to_purchase: summed.funnel_checkout? Math.round(summed.funnel_purchase  / summed.funnel_checkout * 1000) / 10 : 0,
                er: 0, median_sec: 0,  // not summable across countries
            }});
        }});
        items.sort((a, b) => b.sessions - a.sessions);

        // Compute deltas vs avg of prev N periods using channel_country
        const nPrev = _N_PREV_BY_GRAIN[currentGrain] || 4;
        const prevStart = Math.max(0, periods.length - 1 - nPrev);
        const prevPeriods = periods.slice(prevStart, periods.length - 1);
        const STAGE_PAIRS = [
            ['cat_to_prod',          'delta_cat_to_prod',          'funnel_catalog',  'funnel_product'],
            ['prod_to_atc',          'delta_prod_to_atc',          'funnel_product',  'funnel_atc'],
            ['atc_to_checkout',      'delta_atc_to_checkout',      'funnel_atc',      'funnel_checkout'],
            ['checkout_to_purchase', 'delta_checkout_to_purchase', 'funnel_checkout', 'funnel_purchase'],
        ];
        items.forEach(item => {{
            STAGE_PAIRS.forEach(([metric, deltaKey, denomField, numerField]) => {{
                const prevVals = prevPeriods.map(p => {{
                    const sums = _sumByCountryAtPeriod(chc[item.name] || {{}}, p, picked);
                    return sums[denomField] ? sums[numerField] / sums[denomField] * 100 : 0;
                }});
                const avg = _avgArr(prevVals);
                const cur = item[metric];
                item[deltaKey] = (avg > 0 || cur > 0) ? Math.round((cur - avg) * 10) / 10 : null;
            }});
        }});
        return items;
    }}

    // Builds a trend bundle with the same shape as DATA.channel_trend[dev], but
    // datasets recomputed from channel_country sums per period for picked countries.
    function _ccRecomputeTrendBundle(dev, picked, baseTrend) {{
        const chc = (DATA.channel_country || {{}})[dev] || {{}};
        const periods = DATA.periods || [];
        const channels = baseTrend.channels || [];
        const channelColors = baseTrend.channel_colors || {{}};
        const STAGE_KEYS = [
            ['cat_to_prod',          'funnel_catalog',  'funnel_product'],
            ['prod_to_atc',          'funnel_product',  'funnel_atc'],
            ['atc_to_checkout',      'funnel_atc',      'funnel_checkout'],
            ['checkout_to_purchase', 'funnel_checkout', 'funnel_purchase'],
        ];
        const bundle = {{ channels, channel_colors: channelColors }};
        STAGE_KEYS.forEach(([metric, denomField, numerField]) => {{
            bundle[metric] = {{
                labels: periods,
                datasets: channels.map(ch => ({{
                    label: ch,
                    data: periods.map(p => {{
                        const sums = _sumByCountryAtPeriod(chc[ch] || {{}}, p, picked);
                        return sums[denomField] ? Math.round(sums[numerField] / sums[denomField] * 1000) / 10 : null;
                    }}),
                    borderColor: channelColors[ch] || '#999',
                    backgroundColor: channelColors[ch] || '#999',
                    tension: 0.3, pointRadius: 3, spanGaps: true,
                }})),
            }};
        }});
        return bundle;
    }}

    // =========================================================================
    // Phase 6 — Analytics tab country reactivity for per_card_time-based blocks.
    // Other Analytics charts (scroll, catalog_depth, product_time, top_products,
    // cohort) don't carry a country dimension in their BigQuery aggregations —
    // they stay static under country filter changes.
    // =========================================================================
    function _activePerCardRows() {{
        const all = (DATA.analytics && DATA.analytics.per_card_time) || [];
        if (FILTERS.countries) {{
            const picked = FILTERS.countries;
            return all.filter(r => picked.has(r.country));
        }}
        return all.filter(r => !_DEFAULT_EXCLUDED.has(r.country));
    }}

    // Mirror of Python's _build_per_card_chart — session-weighted mean, true median
    // (extends the values list by card_views like the Python builder does).
    function _buildPerCardChart(rows, device) {{
        const acc = new Map();  // period -> bucket: card_views, _med (list), _mean_w
        for (const r of rows) {{
            if (!r.period) continue;
            if (device != null && r.device !== device) continue;
            let b = acc.get(r.period);
            if (!b) {{ b = {{ card_views: 0, _med: [], _mean_w: 0 }}; acc.set(r.period, b); }}
            b.card_views += (r.card_views || 0);
            if (r.median_sec != null && r.card_views) {{
                for (let i = 0; i < r.card_views; i++) b._med.push(r.median_sec);
            }}
            if (r.mean_sec != null) b._mean_w += r.mean_sec * (r.card_views || 0);
        }}
        const out = [];
        for (const [p, b] of acc.entries()) {{
            if (b.card_views === 0) continue;
            const med = b._med.length ? Math.round(b._med.sort((a,c) => a - c)[Math.floor(b._med.length / 2)] * 10) / 10 : 0;
            const mean = b.card_views ? Math.round(b._mean_w / b.card_views * 10) / 10 : 0;
            out.push({{ period: p, card_views: b.card_views, median_sec: med, mean_sec: mean }});
        }}
        out.sort((a, b) => a.period.localeCompare(b.period));
        return out;
    }}

    // Mirror of Python's build_per_card_breakdown — current period per group_key.
    function _buildPerCardBreakdown(rows, groupKey, device, periods, nPrev) {{
        if (!periods.length) return [];
        const curP = periods[periods.length - 1];
        const prevSet = new Set(periods.slice(Math.max(0, periods.length - 1 - nPrev), periods.length - 1));
        function _bucketRow(r) {{ return device == null || r.device === device; }}
        const cur = new Map();
        const prev = new Map();
        for (const r of rows) {{
            if (!_bucketRow(r)) continue;
            const key = r[groupKey]; if (!key) continue;
            const target = r.period === curP ? cur : (prevSet.has(r.period) ? prev : null);
            if (!target) continue;
            let b = target.get(key);
            if (!b) {{ b = {{ card_views: 0, _med: [], _mean_w: 0 }}; target.set(key, b); }}
            b.card_views += (r.card_views || 0);
            if (r.median_sec != null && r.card_views) {{
                for (let i = 0; i < r.card_views; i++) b._med.push(r.median_sec);
            }}
            if (r.mean_sec != null && r.card_views) b._mean_w += r.mean_sec * r.card_views;
        }}
        const out = [];
        for (const [k, b] of cur.entries()) {{
            if (b.card_views < 10) continue;
            const curMed = b._med.length ? Math.round(b._med.sort((a,c) => a - c)[Math.floor(b._med.length / 2)] * 10) / 10 : 0;
            const curMean = b.card_views ? Math.round(b._mean_w / b.card_views * 10) / 10 : 0;
            const p = prev.get(k) || {{ card_views: 0, _med: [], _mean_w: 0 }};
            const prevMed = p._med.length ? Math.round(p._med.sort((a,c) => a - c)[Math.floor(p._med.length / 2)] * 10) / 10 : 0;
            const prevMean = p.card_views ? Math.round(p._mean_w / p.card_views * 10) / 10 : 0;
            const dMed = prevMed > 0 ? Math.round((curMed - prevMed) * 10) / 10 : null;
            const dMean = prevMean > 0 ? Math.round((curMean - prevMean) * 10) / 10 : null;
            out.push({{ name: k, card_views: b.card_views, median_sec: curMed, mean_sec: curMean, delta_median: dMed, delta_mean: dMean }});
        }}
        return out.sort((a, b) => b.card_views - a.card_views).slice(0, 15);
    }}

    // Mirror of Python's build_cards_breakdown — main rows query (uses raw_rows).
    function _buildCardsBreakdown(rows, groupKey, device, periods, nPrev) {{
        if (!periods.length) return [];
        const curP = periods[periods.length - 1];
        const prevSet = new Set(periods.slice(Math.max(0, periods.length - 1 - nPrev), periods.length - 1));
        const devMatch = (r) => device == null || r.device === device;
        const curAgg = _aggregateRows(rows, [groupKey], r => devMatch(r) && r.period === curP);
        const prevAgg = _aggregateRows(rows, [groupKey, 'period'], r => devMatch(r) && prevSet.has(r.period));
        const out = [];
        for (const d of curAgg.values()) {{
            if (d.sessions < 10) continue;
            const key = d._key[0];
            const prevMedVals = [];
            const prevMeanVals = [];
            for (const p of prevSet) {{
                const e = prevAgg.get([key, p].join('||'));
                if (e) {{
                    if (e.median_product_views > 0) prevMedVals.push(e.median_product_views);
                    if (e.avg_product_views > 0) prevMeanVals.push(e.avg_product_views);
                }}
            }}
            const avgMed = prevMedVals.length ? prevMedVals.reduce((a,b)=>a+b,0) / prevMedVals.length : 0;
            const avgMean = prevMeanVals.length ? prevMeanVals.reduce((a,b)=>a+b,0) / prevMeanVals.length : 0;
            const dMed = avgMed > 0 ? Math.round((d.median_product_views - avgMed) * 10) / 10 : null;
            const dMean = avgMean > 0 ? Math.round((d.avg_product_views - avgMean) * 10) / 10 : null;
            out.push({{ name: key, sessions: d.sessions, median_products: d.median_product_views, mean_products: d.avg_product_views, delta_median: dMed, delta_mean: dMean }});
        }}
        return out.sort((a, b) => b.sessions - a.sessions).slice(0, 15);
    }}

    function _rebuildAnalyticsData() {{
        const periods = DATA.periods || [];
        const nPrev = (DATA.summary && DATA.summary.n_prev) || 4;
        const pcRows = _activePerCardRows();
        const mainRows = _activeRows();
        const devices = ['all', 'mobile', 'desktop', 'tablet'];

        const newPerCardChart = {{}};
        const newPerCardByCountry = {{}};
        const newPerCardBySource = {{}};
        const newCardsByCountry = {{}};
        const newCardsBySource = {{}};
        for (const dev of devices) {{
            const d = dev === 'all' ? null : dev;
            newPerCardChart[dev]    = _buildPerCardChart(pcRows, d);
            newPerCardByCountry[dev] = _buildPerCardBreakdown(pcRows, 'country', d, periods, nPrev);
            newPerCardBySource[dev]  = _buildPerCardBreakdown(pcRows, 'source',  d, periods, nPrev);
            newCardsByCountry[dev]   = _buildCardsBreakdown(mainRows, 'country', d, periods, nPrev);
            newCardsBySource[dev]    = _buildCardsBreakdown(mainRows, 'source',  d, periods, nPrev);
        }}

        if (DATA.per_card_chart) Object.assign(DATA.per_card_chart, newPerCardChart);
        if (DATA.per_card_breakdown) {{
            if (DATA.per_card_breakdown.by_country) Object.assign(DATA.per_card_breakdown.by_country, newPerCardByCountry);
            if (DATA.per_card_breakdown.by_source)  Object.assign(DATA.per_card_breakdown.by_source,  newPerCardBySource);
        }}
        if (DATA.cards_breakdown) {{
            if (DATA.cards_breakdown.by_country) Object.assign(DATA.cards_breakdown.by_country, newCardsByCountry);
            if (DATA.cards_breakdown.by_source)  Object.assign(DATA.cards_breakdown.by_source,  newCardsBySource);
        }}
    }}

    // ---------- Bulk-toggle helpers (4 dropdown buttons) ----------
    function setAllCountries(checked) {{
        document.querySelectorAll('.country-section.included input[type="checkbox"]')
            .forEach(cb => {{ cb.checked = checked; }});
        applyCountryFilter();
    }}
    function setExcludedSection(checked) {{
        document.querySelectorAll('.country-section.excluded input[type="checkbox"]')
            .forEach(cb => {{ cb.checked = checked; }});
        applyCountryFilter();
    }}

    // ---------- Orchestrator (called by checkbox change handler) ----------
    function applyCountryFilter() {{
        FILTERS.countries = getSelectedCountries();
        updateCountryCount();

        // Phase 5: rebuild summary_data from active rows. Existing handlers close
        // over `const S = DATA.summary` AND sometimes deeper refs like
        // `_kpiSource = DATA.summary.kpi`. To keep all those refs live we mutate
        // ONE LEVEL DEEP — every sub-object reference in DATA.summary keeps its
        // identity, only its inner keys (per-device slices) get swapped.
        if (DATA.raw_rows && DATA.summary) {{
            const nPrev = DATA.summary.n_prev || 4;
            const fresh = _rebuildSummaryData(_activeRows(), DATA.periods || [], nPrev);
            for (const k of Object.keys(fresh)) {{
                const cur = DATA.summary[k];
                if (cur && typeof cur === 'object' && !Array.isArray(cur)) {{
                    // Drop stale keys that aren't in the fresh slice, then merge.
                    for (const sk of Object.keys(cur)) {{
                        if (!(sk in fresh[k])) delete cur[sk];
                    }}
                    Object.assign(cur, fresh[k]);
                }} else {{
                    DATA.summary[k] = fresh[k];
                }}
            }}
            // Mirror into DATA_BY_GRAIN[currentGrain].summary too, so handlers that
            // captured that reference (Summary _kpiSource path) see updated data.
            if (DATA_BY_GRAIN && DATA_BY_GRAIN[currentGrain] && DATA_BY_GRAIN[currentGrain].summary) {{
                DATA_BY_GRAIN[currentGrain].summary = DATA.summary;
            }}
        }}

        // Phase 6: rebuild per_card_chart + cards/per_card breakdowns for the
        // Analytics tab. Other Analytics charts (scroll, catalog_depth, product_time,
        // top_products, cohort) lack a country dimension in their BigQuery aggregations
        // and stay at SSR data.
        if (DATA.raw_rows) {{
            _rebuildAnalyticsData();
        }}

        // Funnels-tab specifics (only fire when Funnels is initialized).
        if (tabInited.funnels) {{
            recomputeFunnelByCountry(FILTERS.countries);
            const dev = FILTERS.device || 'all';
            recomputeChannelCards(FILTERS.countries, dev);
            recomputeSourceCards(FILTERS.countries, dev);
        }}

        // Trigger the existing filter-handler chain — Summary, Funnels, Analytics
        // handlers all consume the now-updated DATA.summary / FILTERS.countries.
        if (typeof filterHandlers !== 'undefined') {{
            filterHandlers.forEach(fn => fn(FILTERS));
        }}
    }}

    document.addEventListener('DOMContentLoaded', () => {{
        document.querySelectorAll('.country-section input[type="checkbox"]').forEach(cb => {{
            cb.addEventListener('change', applyCountryFilter);
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
        btn.parentElement.querySelectorAll('.tab').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
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
    function _matchesDeviceFilter(r) {{ return FILTERS.device === 'all' || r.device === FILTERS.device; }}
    function scrollByDev(period, device, kind) {{ return _scrollAgg(period, r => r.device === device, kind); }}
    function scrollByCh(period, channel, kind)  {{
        return _scrollAgg(period, r => r.channel === channel && _matchesDeviceFilter(r), kind);
    }}

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

    // Sparkline for KPI cards (Charts v1.0 — Group F)
    // Min/max indicators with semantic color, light vertical grid, no tooltip/legend.
    function sparkline(id, data, color) {{
        const el = document.getElementById(id);
        if (!el || !data || data.length === 0) return null;
        const vals = data.filter(v => v != null);
        const vMax = Math.max(...vals);
        const vMin = Math.min(...vals);
        const cGrowth  = cssvar('--c-growth');
        const cDecline = cssvar('--c-decline');
        const baseColor = color || cssvar('--tx-primary');
        return new Chart(el, {{
            type: 'line',
            data: {{
                labels: data.map((_, i) => i),
                datasets: [{{
                    data,
                    borderColor: baseColor,
                    borderWidth: 1.5,
                    tension: 0.4,
                    fill: false,
                    pointRadius: ctx => {{
                        const v = ctx.parsed.y;
                        return (v === vMax || v === vMin) ? 2.5 : 0;
                    }},
                    pointBackgroundColor: ctx => {{
                        const v = ctx.parsed.y;
                        if (v === vMax) return cGrowth;
                        if (v === vMin) return cDecline;
                        return 'transparent';
                    }},
                    pointBorderWidth: 0
                }}]
            }},
            options: {{
                interaction: {{ mode: 'point', intersect: true }},
                layout: {{ padding: {{ top: 14, bottom: 20, left: 4, right: 18 }} }},
                plugins: {{
                    legend: legendPresets.none,
                    tooltip: {{ enabled: false }},
                    datalabels: {{
                        display: ctx => {{
                            const v = ctx.dataset.data[ctx.dataIndex];
                            return v === vMax || v === vMin;
                        }},
                        font: {{ size: 10 }},
                        color: ctx => {{
                            const v = ctx.dataset.data[ctx.dataIndex];
                            if (v === vMax) return cGrowth;
                            if (v === vMin) return cDecline;
                            return cssvar('--tx-primary');
                        }},
                        align: ctx => {{
                            const v = ctx.dataset.data[ctx.dataIndex];
                            return v === vMax ? 'top' : 'bottom';
                        }},
                        offset: 4,
                        formatter: fmt.num
                    }}
                }},
                scales: {{
                    x: {{ display: true, grid: {{ color: cssvar('--c-grid') || 'rgba(0,0,0,0.06)', drawTicks: false }}, ticks: {{ display: false }}, border: {{ display: false }} }},
                    y: {{ display: false }}
                }}
            }}
        }});
    }}

    // Funnel bar chart — Charts v1.0 Group A (Grouped Bar)
    function funnelBar(id, chartData) {{
        const datasets = chartData.datasets.map(ds => ({{
            ...ds,
            maxBarThickness: 40,
            categoryPercentage: 0.8,
            barPercentage: 0.9,
        }}));
        new Chart(document.getElementById(id), {{
            type: 'bar',
            data: {{ labels: chartData.labels, datasets }},
            options: {{
                plugins: {{
                    legend: legendPresets.bar,
                    datalabels: {{ ...dlPresets.barTop, formatter: fmt.num }}
                }},
                layout: {{ padding: {{ top: 10 }} }},
                scales: {{
                    x: {{ stacked: false }},
                    y: {{ beginAtZero: true, grace: '15%' }}
                }}
            }}
        }});
    }}

    // Funnel % line — Charts v1.0 Group D (Line)
    function funnelPctLine(id, chartData) {{
        const datasets = chartData.datasets.map(ds => ({{
            borderWidth: 2, tension: 0.3,
            pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
            ...ds
        }}));
        new Chart(document.getElementById(id), {{
            type: 'line',
            data: {{ labels: chartData.labels, datasets }},
            options: {{
                plugins: {{
                    legend: legendPresets.line,
                    datalabels: {{ ...dlPresets.line, formatter: v => fmt.pct(v, 1) }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => ctx.dataset.label + ': ' + fmt.pct(ctx.parsed.y, 1)
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

    // Channel trend % line — Charts v1.0 Group D (Line, no datalabels — too many series)
    function channelTrendLine(id, chartData) {{
        const datasets = chartData.datasets.map(ds => ({{
            borderWidth: 2, tension: 0.3,
            pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
            ...ds
        }}));
        return new Chart(document.getElementById(id), {{
            type: 'line',
            data: {{ labels: chartData.labels, datasets }},
            options: {{
                plugins: {{
                    legend: legendPresets.none,
                    datalabels: {{ ...dlPresets.line, formatter: v => fmt.pct(v, 1) }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => ctx.dataset.label + ': ' + (ctx.parsed.y == null ? '—' : fmt.pct(ctx.parsed.y, 1))
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
        // 4 device variants of channel/source sliders coexist in DOM, init each set.
        const _devPrefixes = {{ all: '', mobile: 'mobile-', desktop: 'desktop-', tablet: 'tablet-' }};
        Object.entries(DATA.channel_cards).forEach(([dev, cards]) => {{
            const prefix = _devPrefixes[dev] || '';
            cards.forEach(card => {{
                const id = prefix + 'funnel-channel-' + card.channel.toLowerCase().replace(/\\s/g, '-');
                if (!document.getElementById(id)) return;
                funnelBar(id, card.funnel);
            }});
        }});
        Object.entries(DATA.source_cards).forEach(([dev, cards]) => {{
            const prefix = _devPrefixes[dev] || '';
            cards.forEach(card => {{
                const id = prefix + 'funnel-source-' + card.source.replace(/\\./g, '_').replace(/[()]/g, '').replace(/ /g, '-');
                if (!document.getElementById(id)) return;
                funnelBar(id, card.funnel);
            }});
        }});

        // Channel effectiveness — per-stage bubble + trend pair, each with its own checkbox filter
        const CHANNEL_STAGES = [
            {{ stage: 'prod',     sessKey: 'funnel_catalog',  convKey: 'cat_to_prod',          deltaKey: 'delta_cat_to_prod',          xLabel: 'Сессии в каталоге',  trendKey: 'cat_to_prod' }},
            {{ stage: 'atc',      sessKey: 'funnel_product',  convKey: 'prod_to_atc',          deltaKey: 'delta_prod_to_atc',          xLabel: 'Сессии на товаре',   trendKey: 'prod_to_atc' }},
            {{ stage: 'checkout', sessKey: 'funnel_atc',      convKey: 'atc_to_checkout',      deltaKey: 'delta_atc_to_checkout',      xLabel: 'Сессии с корзиной',  trendKey: 'atc_to_checkout' }},
            {{ stage: 'purchase', sessKey: 'funnel_checkout', convKey: 'checkout_to_purchase', deltaKey: 'delta_checkout_to_purchase', xLabel: 'Сессии с чекаутом', trendKey: 'checkout_to_purchase' }},
        ];
        // Bubble + trend are per-device. Initial render for the active filter; rebuild
        // (destroy+recreate) on filter change. The per-stage stage-isolated checkbox
        // filters are wired against the initial dataset; they will be re-wired on rebuild.
        const _trendInitial = DATA.channel_trend[FILTERS.device] || DATA.channel_trend.all;
        const channelOrder = _trendInitial.channels;
        const channelColors = _trendInitial.channel_colors;
        const _stageTrends = {{}}; // stage -> trend chart instance, used by checkbox sync
        CHANNEL_STAGES.forEach(s => {{
            const bubbleId = 'bubble-channel-' + s.stage;
            const trendId  = 'trend-channel-'  + s.stage;
            const filterId = 'filter-channel-' + s.stage;
            const prefix   = 'ch-' + s.stage;

            const bubbleData = DATA.bubble_channel[FILTERS.device] || DATA.bubble_channel.all;
            const trendData  = (DATA.channel_trend[FILTERS.device] || DATA.channel_trend.all)[s.trendKey];
            const bubble = bubbleChart(bubbleId, bubbleData, s.sessKey, s.convKey, s.xLabel, s.deltaKey, channelColors);
            const trend  = channelTrendLine(trendId, trendData);
            _stageTrends[s.stage] = trend;

            bubbleCharts[prefix] = [{{
                id: bubbleId, sessKey: s.sessKey, convKey: s.convKey, xLabel: s.xLabel,
                deltaKey: s.deltaKey, colorMap: channelColors, chart: bubble
            }}];
            buildBubbleFilters(filterId, bubbleData, prefix, channelColors, channelOrder);

            // Sync this stage's trend visibility with this stage's checkboxes only
            document.querySelectorAll('input[data-prefix="' + prefix + '"]').forEach(cb => {{
                cb.addEventListener('change', () => {{
                    const idx = channelOrder.indexOf(cb.dataset.name);
                    if (idx === -1) return;
                    const ds = _stageTrends[s.stage].data.datasets[idx];
                    if (ds) ds.hidden = !cb.checked;
                    _stageTrends[s.stage].update();
                }});
            }});
        }});

        // ---- Filter handler: rebuild bubbles + trends with current device slice ----
        // FILTERS.countries (when set) replaces server-side bubble_channel / channel_trend
        // data with on-the-fly sums over selected countries (using bubble_channel_country
        // and channel_country payload keys from Phase 1).
        registerFilterHandler(f => {{
            const dev = f.device;
            let bubbleData, trendBundle;
            if (FILTERS.countries && DATA.bubble_channel_country && DATA.channel_country) {{
                bubbleData = _ccRecomputeBubbleItems(dev, FILTERS.countries);
                trendBundle = _ccRecomputeTrendBundle(dev, FILTERS.countries, _trendInitial);
            }} else {{
                bubbleData = DATA.bubble_channel[dev] || DATA.bubble_channel.all;
                trendBundle = DATA.channel_trend[dev] || DATA.channel_trend.all;
            }}
            CHANNEL_STAGES.forEach(s => {{
                const cfg = bubbleCharts['ch-' + s.stage];
                if (cfg && cfg[0]) {{
                    cfg[0].chart.destroy();
                    cfg[0].chart = bubbleChart('bubble-channel-' + s.stage, bubbleData,
                        s.sessKey, s.convKey, s.xLabel, s.deltaKey, channelColors);
                }}
                const trend = _stageTrends[s.stage];
                if (trend) {{
                    const newDatasets = trendBundle[s.trendKey].datasets;
                    trend.data.datasets.forEach((ds, i) => {{
                        if (newDatasets[i]) ds.data = newDatasets[i].data;
                    }});
                    trend.update('none');
                }}
            }});
        }});

        // ---- Bottom funnel table ----
        // FILTERS.countries (set by applyCountryFilter) makes this country-reactive:
        // filter bottom_funnel_full instead of using the SSR (default-excluded) set.
        function _renderBottomFunnel(dev) {{
            let rows;
            if (FILTERS.countries && DATA.bottom_funnel_full) {{
                const allRows = DATA.bottom_funnel_full[dev] || DATA.bottom_funnel_full.all || [];
                rows = allRows.filter(r => FILTERS.countries.has(r.country));
            }} else {{
                rows = (DATA.bottom_funnel && (DATA.bottom_funnel[dev] || DATA.bottom_funnel.all)) || [];
            }}
            const tbody = document.getElementById('tbody-bottom-funnel');
            if (!tbody) return;
            tbody.innerHTML = rows.map(r =>
                '<tr><td>' + r.source + '</td>' +
                '<td>' + ((COUNTRY_FLAGS[r.country] || '🏳️') + ' ' + r.country) + '</td>' +
                '<td>' + r.sessions + '</td>' +
                '<td>' + r.catalog + '</td>' +
                '<td>' + r.product + '</td>' +
                '<td class="highlight">' + r.atc + '</td>' +
                '<td class="highlight">' + r.checkout + '</td>' +
                '<td class="highlight">' + r.purchase + '</td></tr>'
            ).join('');
        }}
        _renderBottomFunnel(FILTERS.device);
        registerFilterHandler(f => _renderBottomFunnel(f.device));

        // ---- Stage tables (Каталог→Товар, Товар→Корзина, etc) ----
        const STAGE_LABELS = {{
            prod: 'Сессии в каталоге', atc: 'Сессии на товаре',
            checkout: 'Сессии с корзиной', purchase: 'Сессии с чекаутом'
        }};
        function _stageDelta(v) {{
            if (v == null) return '<td><span class="delta neutral">—</span></td>';
            if (v > 0)     return '<td><span class="delta green">↑ +' + v + ' п.п.</span></td>';
            if (v < 0)     return '<td><span class="delta red">↓ ' + v + ' п.п.</span></td>';
            return '<td><span class="delta neutral">→ 0 п.п.</span></td>';
        }}
        function _renderStageTable(stageKey, dev) {{
            const wrapper = document.getElementById('stage-table-' + stageKey);
            if (!wrapper) return;
            // FILTERS.countries makes this country-reactive: filter stage_tables_full
            // instead of using the SSR (default-excluded) set.
            let rows;
            if (FILTERS.countries && DATA.stage_tables_full) {{
                const stagesFull = DATA.stage_tables_full[dev] || DATA.stage_tables_full.all || {{}};
                rows = (stagesFull[stageKey] || []).filter(r => FILTERS.countries.has(r.country));
            }} else {{
                const stages = DATA.stage_tables[dev] || DATA.stage_tables.all || {{}};
                rows = stages[stageKey] || [];
            }}
            const inputLabel = STAGE_LABELS[stageKey];
            let body;
            if (!rows.length) {{
                body = '<tr><td colspan="5" class="empty-row">Нет данных</td></tr>';
            }} else {{
                body = rows.map(r =>
                    '<tr><td>' + ((COUNTRY_FLAGS[r.country] || '🏳️') + ' ' + r.country) + '</td>' +
                    '<td><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:' + r.channel_color + '; margin-right:6px; vertical-align:middle;"></span>' + r.channel + '</td>' +
                    '<td>' + r.input + '</td><td>' + r.conv + '%</td>' +
                    _stageDelta(r.delta) + '</tr>'
                ).join('');
            }}
            const prevShort = (GRAIN_LABELS[currentGrain] || GRAIN_LABELS.week).prev_short;
            wrapper.innerHTML =
                '<div class="data-table-wrap"><table class="data-table">' +
                '<thead><tr><th>Страна</th><th>Канал</th><th>' + inputLabel +
                '</th><th>Конверсия</th><th><span data-grain-label="prev_short">' + prevShort + '</span></th></tr></thead>' +
                '<tbody>' + body + '</tbody></table></div>';
        }}
        function _renderAllStageTables(dev) {{
            ['prod', 'atc', 'checkout', 'purchase'].forEach(k => _renderStageTable(k, dev));
        }}
        _renderAllStageTables(FILTERS.device);
        registerFilterHandler(f => _renderAllStageTables(f.device));

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
    let bubbleCharts = {{}};

    function buildBubbleFilters(containerId, items, prefix, colorMap, names) {{
        const container = document.getElementById(containerId);
        if (!container) return;
        // Clear any previous checkboxes — initFunnelsTab() runs again on every grain
        // switch and would otherwise stack a fresh row on top of the existing ones.
        while (container.firstChild) container.removeChild(container.firstChild);
        const list = names && names.length ? names : items.map(i => i.name);
        list.forEach(name => {{
            const label = document.createElement('label');
            label.className = 'check';
            label.style.marginRight = '10px';
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

    // Bubble effectiveness chart — Charts v1.0 Group E (Bubble)
    function bubbleChart(id, items, sessKey, convKey, xLabel, deltaKey, colorMap) {{
        const datasets = items.filter(item => item[sessKey] > 0).map(item => {{
            const color = (colorMap && colorMap[item.name]) || cssvar('--c-channel-social');
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
                interaction: {{ mode: 'point', intersect: true }},
                layout: {{ padding: {{ top: 16, right: 32, bottom: 4, left: 4 }} }},
                plugins: {{
                    legend: legendPresets.none,
                    datalabels: {{
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
                        offset: 6,
                        clamp: true,
                        color: cssvar('--tx-primary'),
                        formatter: (val, ctx) => ctx.dataset.label || '',
                        ...dlPad
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => {{
                                const filtered = items.filter(i => i[sessKey] > 0);
                                const item = filtered[ctx.datasetIndex];
                                if (!item) return '';
                                const p = ctx.raw;
                                const lines = [
                                    item.name,
                                    xLabel + ': ' + fmt.num(p.x) + ' сес. → ' + fmt.pct(p.y, 1)
                                ];
                                if (deltaKey && item[deltaKey] != null) {{
                                    const d = item[deltaKey];
                                    const sign = d > 0 ? '+' : '';
                                    const prevShort = (GRAIN_LABELS[currentGrain] || GRAIN_LABELS.week).prev_short;
                                    lines.push(prevShort + ': ' + sign + d + ' п.п.');
                                }}
                                lines.push('ER: ' + item.er + '%');
                                lines.push('Median: ' + item.median_sec + 's');
                                return lines;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ title: {{ display: true, text: xLabel }} }},
                    y: {{ title: {{ display: true, text: 'Конверсия %' }}, beginAtZero: true, ticks: {{ callback: v => v + '%' }} }}
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
        const chColors = {{
            Social:   cssvar('--c-channel-social'),
            Paid:     cssvar('--c-channel-paid'),
            Direct:   cssvar('--c-channel-direct'),
            Organic:  cssvar('--c-channel-organic'),
            Referral: cssvar('--c-channel-referral')
        }};
        const devColors = {{ mobile: cssvar('--c-channel-social'), desktop: cssvar('--c-channel-paid') }};
        const devices = ['mobile', 'desktop'];
        const lineOpts = {{
            plugins: {{
                legend: legendPresets.line,
                datalabels: {{ ...dlPresets.line, formatter: v => fmt.pct(v, 1) }},
                tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmt.pct(ctx.parsed.y, 1) }} }}
            }},
            scales: {{ y: {{ beginAtZero: true, max: 100, ticks: {{ callback: v => v + '%' }} }} }}
        }};

        const cvProductDev = document.getElementById('analytics-scroll-product-device');
        let scrollProdDevChart = null;
        if (cvProductDev) {{
            scrollProdDevChart = new Chart(cvProductDev, {{
                type: 'line',
                data: {{
                    labels: DATA.periods,
                    datasets: devices.map(dev => ({{
                        label: dev === 'mobile' ? 'Мобилка' : 'Десктоп',
                        _device: dev,
                        data: DATA.periods.map(p => scrollByDev(p, dev, 'product')),
                        borderColor: devColors[dev], tension: 0.3, borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                    }}))
                }},
                options: lineOpts
            }});
            registerFilterHandler(f => {{
                scrollProdDevChart.data.datasets.forEach(ds => {{
                    ds.hidden = f.device !== 'all' && ds._device !== f.device;
                }});
                scrollProdDevChart.update('none');
            }});
        }}

        const cvProductCh = document.getElementById('analytics-scroll-product-channel');
        let scrollProdChChart = null;
        if (cvProductCh) {{
            scrollProdChChart = new Chart(cvProductCh, {{
                type: 'line',
                data: {{
                    labels: DATA.periods,
                    datasets: scrollChannels.map(ch => ({{
                        label: ch,
                        _channel: ch,
                        data: DATA.periods.map(p => scrollByCh(p, ch, 'product')),
                        borderColor: chColors[ch], tension: 0.3, borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                    }}))
                }},
                options: lineOpts
            }});
            registerFilterHandler(() => {{
                scrollProdChChart.data.datasets.forEach(ds => {{
                    ds.data = DATA.periods.map(p => scrollByCh(p, ds._channel, 'product'));
                }});
                scrollProdChChart.update('none');
            }});
        }}
    }}

    // 3. Time on Product Page by channel — aggregated per channel/period, device-filtered.
    // Each row in A.product_time has device after the SQL change. We re-aggregate in JS
    // weighted by sessions_with_product to keep the median honest under the filter.
    if (A.product_time && A.product_time.length > 0) {{
        const ptChannels = ['Social', 'Paid', 'Direct', 'Organic', 'Referral'];
        const ptColors = {{
            Social:   cssvar('--c-channel-social'),
            Paid:     cssvar('--c-channel-paid'),
            Direct:   cssvar('--c-channel-direct'),
            Organic:  cssvar('--c-channel-organic'),
            Referral: cssvar('--c-channel-referral')
        }};
        function _ptAgg(period, channel, device) {{
            // Weighted average median (proxy for combined median when slicing across devices).
            let totalSec = 0, totalSess = 0;
            A.product_time.forEach(r => {{
                if (r.period !== period || r.channel !== channel) return;
                if (device !== 'all' && r.device !== device) return;
                const w = r.sessions_with_product || 0;
                totalSec += (r.median_sec || 0) * w;
                totalSess += w;
            }});
            return {{ median: totalSess > 0 ? totalSec / totalSess : 0, sessions: totalSess }};
        }}
        const ptChart = new Chart(document.getElementById('analytics-product-time'), {{
            type: 'line',
            data: {{
                labels: DATA.periods,
                datasets: ptChannels.map(ch => ({{
                    label: ch,
                    _channel: ch,
                    data: DATA.periods.map(p => _ptAgg(p, ch, FILTERS.device).median),
                    borderColor: ptColors[ch],
                    tension: 0.3, borderWidth: 2,
                    pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                }}))
            }},
            options: {{
                plugins: {{
                    legend: legendPresets.line,
                    datalabels: {{ ...dlPresets.line, formatter: fmt.sec }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => {{
                                const r = _ptAgg(DATA.periods[ctx.dataIndex], ctx.dataset.label, FILTERS.device);
                                return ctx.dataset.label + ': ' + fmt.sec(ctx.parsed.y) + ' (' + fmt.num(r.sessions) + ' сес.)';
                            }}
                        }}
                    }}
                }},
                scales: {{ y: {{ beginAtZero: true, grace: '15%', title: {{ display: true, text: 'Median sec' }} }} }}
            }}
        }});
        registerFilterHandler(f => {{
            ptChart.data.datasets.forEach(ds => {{
                ds.data = DATA.periods.map(p => _ptAgg(p, ds._channel, f.device).median);
            }});
            ptChart.update('none');
        }});
    }}

    // 3b. Per-card view time (per-device dict; one median + one mean line)
    if (DATA.per_card_chart && (DATA.per_card_chart.all || []).length > 0) {{
        function _pcSlice(dev) {{
            const list = DATA.per_card_chart[dev] || DATA.per_card_chart.all || [];
            const m = {{}};
            list.forEach(r => {{ m[r.period] = r; }});
            return m;
        }}
        let pcByPeriod = _pcSlice(FILTERS.device);
        const perCardChart = new Chart(document.getElementById('analytics-per-card-time'), {{
            type: 'line',
            data: {{
                labels: DATA.periods,
                datasets: [
                    {{
                        label: 'Median sec / card',
                        data: DATA.periods.map(p => pcByPeriod[p] ? pcByPeriod[p].median_sec : null),
                        borderColor: cssvar('--c-channel-social'), backgroundColor: cssvar('--c-channel-social'),
                        tension: 0.3, borderWidth: 2,
                        pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                    }},
                    {{
                        label: 'Mean sec / card',
                        data: DATA.periods.map(p => pcByPeriod[p] ? pcByPeriod[p].mean_sec : null),
                        borderColor: cssvar('--c-channel-paid'), backgroundColor: cssvar('--c-channel-paid'),
                        borderDash: [6, 4], tension: 0.3, borderWidth: 2,
                        pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                    }}
                ]
            }},
            options: {{
                plugins: {{
                    legend: legendPresets.line,
                    datalabels: {{ ...dlPresets.line, formatter: fmt.sec }},
                    tooltip: {{
                        callbacks: {{
                            label: ctx => {{
                                const r = pcByPeriod[DATA.periods[ctx.dataIndex]];
                                const views = r ? r.card_views : 0;
                                return ctx.dataset.label + ': ' + fmt.sec(ctx.parsed.y) + ' (' + fmt.num(views) + ' card views)';
                            }}
                        }}
                    }}
                }},
                scales: {{ y: {{ beginAtZero: true, grace: '15%', title: {{ display: true, text: 'sec per card view' }} }} }}
            }}
        }});
        registerFilterHandler(f => {{
            pcByPeriod = _pcSlice(f.device);
            perCardChart.data.datasets[0].data = DATA.periods.map(p => pcByPeriod[p] ? pcByPeriod[p].median_sec : null);
            perCardChart.data.datasets[1].data = DATA.periods.map(p => pcByPeriod[p] ? pcByPeriod[p].mean_sec : null);
            perCardChart.update('none');
        }});
    }}

    // 3c. Top-30 product cards table — per-device. Period toggle stays.
    if (DATA.top_products) {{
        let _tpPeriod = 'week';
        // top_products[period] is now {{all, mobile, desktop, tablet}} dicts
        const _tpData = () => {{
            const periodDict = DATA.top_products[_tpPeriod] || {{}};
            return periodDict[FILTERS.device] || periodDict.all || [];
        }};

        window.setTopProductsPeriod = function(period, btn) {{
            _tpPeriod = period;
            document.getElementById('tp-period-week').classList.toggle('is-active', period === 'week');
            document.getElementById('tp-period-4w').classList.toggle('is-active', period === 'agg_4w');
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
        registerFilterHandler(() => renderTopProducts());
    }}

    // 4. Catalog Depth (stacked bar) — rows now include device, aggregate per filter.
    if (A.catalog_depth && A.catalog_depth.length > 0) {{
        function _cdAgg(device) {{
            // Sum page1..4+ per period, scoped to device.
            const byPeriod = {{}};
            A.catalog_depth.forEach(r => {{
                if (device !== 'all' && r.device !== device) return;
                if (!byPeriod[r.period]) byPeriod[r.period] = {{ page1: 0, page2: 0, page3: 0, page4plus: 0, sessions: 0 }};
                const b = byPeriod[r.period];
                b.page1 += r.page1 || 0; b.page2 += r.page2 || 0;
                b.page3 += r.page3 || 0; b.page4plus += r.page4plus || 0;
                b.sessions += r.sessions || 0;
            }});
            const periods = Object.keys(byPeriod).sort();
            return {{
                periods,
                rows: periods.map(p => ({{ period: p, ...byPeriod[p] }})),
            }};
        }}
        const initialCd = _cdAgg(FILTERS.device);
        const catalogDepthChart = new Chart(document.getElementById('analytics-catalog-depth'), {{
            type: 'bar',
            data: {{
                labels: initialCd.periods,
                datasets: [
                    {{ label: 'Стр. 1',  data: initialCd.rows.map(r => r.page1),     backgroundColor: cssvar('--c-channel-direct'),  maxBarThickness: 40 }},
                    {{ label: 'Стр. 2',  data: initialCd.rows.map(r => r.page2),     backgroundColor: cssvar('--c-channel-social'),  maxBarThickness: 40 }},
                    {{ label: 'Стр. 3',  data: initialCd.rows.map(r => r.page3),     backgroundColor: cssvar('--c-channel-organic'), maxBarThickness: 40 }},
                    {{ label: 'Стр. 4+', data: initialCd.rows.map(r => r.page4plus), backgroundColor: cssvar('--c-channel-paid'),    maxBarThickness: 40 }},
                ]
            }},
            options: {{
                plugins: {{
                    legend: legendPresets.bar,
                    datalabels: {{ ...dlPresets.barCenter, display: ctx => ctx.dataset.data[ctx.dataIndex] > 30, formatter: fmt.num }}
                }},
                scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true, title: {{ display: true, text: 'Сессии' }} }} }}
            }}
        }});
        registerFilterHandler(f => {{
            const cd = _cdAgg(f.device);
            catalogDepthChart.data.labels = cd.periods;
            catalogDepthChart.data.datasets[0].data = cd.rows.map(r => r.page1);
            catalogDepthChart.data.datasets[1].data = cd.rows.map(r => r.page2);
            catalogDepthChart.data.datasets[2].data = cd.rows.map(r => r.page3);
            catalogDepthChart.data.datasets[3].data = cd.rows.map(r => r.page4plus);
            catalogDepthChart.update('none');
        }});
    }}

    // ---- Analytics tab tables: re-render per-device on filter change ----
    function _aDelta(v, suffix) {{
        if (v == null) return '<td><span class="delta neutral">—</span></td>';
        if (v > 0)     return '<td><span class="delta green">↑ +' + v + (suffix || '') + '</span></td>';
        if (v < 0)     return '<td><span class="delta red">↓ ' + v + (suffix || '') + '</span></td>';
        return '<td><span class="delta neutral">→ 0' + (suffix || '') + '</span></td>';
    }}
    function _flagPrefix(name) {{ return (COUNTRY_FLAGS[name] || '🏳️') + ' ' + name; }}

    function _renderPerCardTable(tableId, rows, withFlag) {{
        const tbody = document.querySelector('#' + tableId + ' tbody');
        if (!tbody) return;
        if (!rows.length) {{
            tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Нет данных</td></tr>';
            return;
        }}
        tbody.innerHTML = rows.map(r =>
            '<tr><td>' + (withFlag ? _flagPrefix(r.name) : r.name) + '</td>' +
            '<td>' + r.card_views + '</td>' +
            '<td>' + r.median_sec + 's</td>' + _aDelta(r.delta_median, 's') +
            '<td>' + r.mean_sec + 's</td>' + _aDelta(r.delta_mean, 's') + '</tr>'
        ).join('');
    }}
    function _renderCardsTable(tableId, rows, withFlag) {{
        const tbody = document.querySelector('#' + tableId + ' tbody');
        if (!tbody) return;
        if (!rows.length) {{
            tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Нет данных</td></tr>';
            return;
        }}
        tbody.innerHTML = rows.map(r =>
            '<tr><td>' + (withFlag ? _flagPrefix(r.name) : r.name) + '</td>' +
            '<td>' + r.sessions + '</td>' +
            '<td>' + r.median_products + '</td>' + _aDelta(r.delta_median) +
            '<td>' + r.mean_products + '</td>' + _aDelta(r.delta_mean) + '</tr>'
        ).join('');
    }}
    function _applyAnalyticsTables(dev) {{
        const pcc = (DATA.per_card_breakdown.by_country || {{}})[dev] || (DATA.per_card_breakdown.by_country || {{}}).all || [];
        const pcs = (DATA.per_card_breakdown.by_source  || {{}})[dev] || (DATA.per_card_breakdown.by_source  || {{}}).all || [];
        const cbc = (DATA.cards_breakdown.by_country     || {{}})[dev] || (DATA.cards_breakdown.by_country     || {{}}).all || [];
        const cbs = (DATA.cards_breakdown.by_source      || {{}})[dev] || (DATA.cards_breakdown.by_source      || {{}}).all || [];
        _renderPerCardTable('tbl-per-card-country', pcc, true);
        _renderPerCardTable('tbl-per-card-source',  pcs, false);
        _renderCardsTable('tbl-cards-country', cbc, true);
        _renderCardsTable('tbl-cards-source',  cbs, false);
    }}
    _applyAnalyticsTables(FILTERS.device);
    registerFilterHandler(f => _applyAnalyticsTables(f.device));

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
        // KPI tiles + sparklines: ALWAYS sourced from the weekly payload, regardless of
        // the current grain selector. The user explicitly wanted the KPI block to stay
        // weekly even when D is active, so the D/W toggle does not influence these tiles.
        let sparkAtc = null, sparkPr = null;
        const _kpiSource = (DATA_BY_GRAIN && DATA_BY_GRAIN.week && DATA_BY_GRAIN.week.summary && DATA_BY_GRAIN.week.summary.kpi)
            || S.kpi;
        function applyKpiSlice(dev) {{
            const k = _kpiSource[dev] || _kpiSource.all;
            setKpi('sum-kpi-rps', '$' + k.revenue_per_session.value, k.revenue_per_session.delta);
            setKpi('sum-kpi-rev', '$' + k.revenue.value, k.revenue.delta);
            setKpi('sum-kpi-atc', k.atc_rate.value + '%', k.atc_rate.delta, true);
            setKpi('sum-kpi-pr',  k.purchase_rate.value + '%', k.purchase_rate.delta, true);
            setKpi('sum-kpi-c2p', k.cart_to_purchase.value + '%', k.cart_to_purchase.delta, true);
            if (sparkAtc) sparkAtc.destroy();
            if (sparkPr) sparkPr.destroy();
            sparkAtc = sparkline('sum-spark-atc', k.atc_rate.trend,      cssvar('--c-channel-social'));
            sparkPr  = sparkline('sum-spark-pr',  k.purchase_rate.trend, cssvar('--c-channel-paid'));
        }}
        applyKpiSlice(FILTERS.device);
        registerFilterHandler(f => applyKpiSlice(f.device));

        // ---- Visitors & Sessions (dual axis: line=visitors, bars=sessions) ----
        const visSessChart = new Chart(document.getElementById('sum-visitors-sessions'), {{
            type: 'bar',
            data: {{
                labels: S.visitors_sessions.labels,
                datasets: [
                    {{ type: 'bar', label: 'Сессии', data: S.visitors_sessions.all.sessions,
                       backgroundColor: cssvar('--c-channel-social') + '4D', borderColor: cssvar('--c-channel-social'),
                       yAxisID: 'y', order: 2, maxBarThickness: 40 }},
                    {{ type: 'line', label: 'Посетители', data: S.visitors_sessions.all.visitors,
                       borderColor: cssvar('--c-channel-paid'), borderWidth: 2, tension: 0.3,
                       pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                       yAxisID: 'y1', order: 0 }}
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
                        offset: 6,
                        color: ctx => ctx.dataset.type === 'line' ? cssvar('--c-channel-paid') : cssvar('--c-channel-social'),
                        backgroundColor: ctx => ctx.dataset.type === 'line' ? 'rgba(255,255,255,0.85)' : null,
                        borderRadius: 3,
                        padding: ctx => ctx.dataset.type === 'line' ? {{ top: 1, bottom: 1, left: 4, right: 4 }} : 0,
                        formatter: fmt.num
                    }},
                    tooltip: {{ mode: 'index', intersect: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, grace: '15%', position: 'left', title: {{ display: true, text: 'Сессии' }} }},
                    y1: {{ beginAtZero: true, grace: '20%', position: 'right', title: {{ display: true, text: 'Посетители' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});
        registerFilterHandler(f => {{
            const slice = S.visitors_sessions[f.device] || S.visitors_sessions.all;
            visSessChart.data.datasets[0].data = slice.sessions;
            visSessChart.data.datasets[1].data = slice.visitors;
            visSessChart.update('none');
        }});

        // ---- Device Sessions (stacked bar) ----
        const devColors = {{
            mobile:  cssvar('--c-channel-social'),
            desktop: cssvar('--c-channel-organic'),
            tablet:  cssvar('--c-channel-referral')
        }};
        const devSessChart = new Chart(document.getElementById('sum-device-sessions'), {{
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
                        font: {{ size: 11, weight: 'bold' }}, color: cssvar('--tx-ondark'),
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
        registerDeviceChart(devSessChart);
        // Country-reactive: re-bind data from (now-fresh) DATA.summary.device_sessions.
        registerFilterHandler(() => {{
            ['mobile', 'desktop', 'tablet'].forEach((dev, i) => {{
                if (devSessChart.data.datasets[i]) devSessChart.data.datasets[i].data = S.device_sessions[dev];
            }});
            devSessChart.update('none');
        }});

        // ---- New vs Returning ----
        const nrInit = S.new_returning[FILTERS.device] || S.new_returning.all;
        const newRetChart = new Chart(document.getElementById('sum-new-returning'), {{
            type: 'line',
            data: {{
                labels: S.new_returning.labels,
                datasets: [
                    {{ label: 'Новые',       data: nrInit.new,       borderColor: cssvar('--c-channel-organic'), borderWidth: 2, tension: 0.3, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0, _align: 'top' }},
                    {{ label: 'Вернувшиеся', data: nrInit.returning, borderColor: cssvar('--c-channel-social'),  borderWidth: 2, tension: 0.3, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0, _align: 'bottom' }}
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
                                const slice = S.new_returning[FILTERS.device] || S.new_returning.all;
                                const total = (slice.new[ctx.dataIndex] || 0) + (slice.returning[ctx.dataIndex] || 0);
                                const pct = total > 0 ? Math.round(ctx.parsed.y / total * 100) : 0;
                                return ctx.dataset.label + ': ' + ctx.parsed.y + ' (' + pct + '%)';
                            }}
                        }}
                    }}
                }},
                scales: {{ y: {{ beginAtZero: true, grace: '15%' }} }}
            }}
        }});
        registerFilterHandler(f => {{
            const slice = S.new_returning[f.device] || S.new_returning.all;
            newRetChart.data.datasets[0].data = slice.new;
            newRetChart.data.datasets[1].data = slice.returning;
            newRetChart.update('none');
        }});

        // ---- Time on Site per device (median) ----
        const timeOnSiteChart = new Chart(document.getElementById('sum-time-on-site'), {{
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
        registerDeviceChart(timeOnSiteChart);
        registerFilterHandler(() => {{
            ['mobile','desktop','tablet'].forEach((dev, i) => {{
                if (timeOnSiteChart.data.datasets[i]) timeOnSiteChart.data.datasets[i].data = S.time_on_site[dev];
            }});
            timeOnSiteChart.update('none');
        }});

        // ---- Bounce Rate per device ----
        const bounceDevChart = new Chart(document.getElementById('sum-bounce-device'), {{
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
        registerDeviceChart(bounceDevChart);
        registerFilterHandler(() => {{
            ['mobile','desktop','tablet'].forEach((dev, i) => {{
                if (bounceDevChart.data.datasets[i]) bounceDevChart.data.datasets[i].data = S.bounce_device[dev];
            }});
            bounceDevChart.update('none');
        }});

        // ---- Source trend (multi-line with session counts) ----
        const srcColors = {{
            Social:   cssvar('--c-channel-social'),
            Paid:     cssvar('--c-channel-paid'),
            Direct:   cssvar('--c-channel-direct'),
            Organic:  cssvar('--c-channel-organic'),
            Referral: cssvar('--c-channel-referral')
        }};
        const srcInit = S.source_trend[FILTERS.device] || S.source_trend.all;
        const sourceTrendChart = new Chart(document.getElementById('sum-source-trend'), {{
            type: 'line',
            data: {{
                labels: S.source_trend.labels,
                datasets: srcInit.map((src, i) => ({{
                    label: src.name, data: src.sessions,
                    borderColor: srcColors[src.name] || cssvar('--tx-muted'),
                    borderWidth: 2, tension: 0.3, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
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
        registerFilterHandler(f => {{
            const slice = S.source_trend[f.device] || S.source_trend.all;
            sourceTrendChart.data.datasets.forEach((ds, i) => {{
                if (slice[i]) {{
                    ds.data = slice[i].sessions;
                    ds._share = slice[i].share_pct;
                }}
            }});
            sourceTrendChart.update('none');
        }});

        // ---- ATC + PR dual axis ----
        const atcPrInit = S.atc_pr_trend[FILTERS.device] || S.atc_pr_trend.all;
        const atcPrChart = new Chart(document.getElementById('sum-atc-pr-trend'), {{
            type: 'line',
            data: {{
                labels: S.atc_pr_trend.labels,
                datasets: [
                    {{ label: 'ATC Rate',      data: atcPrInit.atc_rate,      borderColor: cssvar('--c-channel-social'), borderWidth: 2, tension: 0.3, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0, yAxisID: 'y'  }},
                    {{ label: 'Purchase Rate', data: atcPrInit.purchase_rate, borderColor: cssvar('--c-channel-paid'),   borderWidth: 2, tension: 0.3, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                plugins: {{
                    legend: legendPresets.line,
                    datalabels: {{ ...dlPresets.line, formatter: v => fmt.pct(v, 1) }},
                    tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmt.pct(ctx.parsed.y, 1) }} }}
                }},
                scales: {{
                    y:  {{ beginAtZero: true, grace: '15%', position: 'left',  title: {{ display: true, text: 'ATC Rate %',      color: cssvar('--c-channel-social') }}, ticks: {{ callback: v => v + '%', color: cssvar('--c-channel-social') }} }},
                    y1: {{ beginAtZero: true, grace: '15%', position: 'right', title: {{ display: true, text: 'Purchase Rate %', color: cssvar('--c-channel-paid')   }}, ticks: {{ callback: v => v + '%', color: cssvar('--c-channel-paid')   }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});
        registerFilterHandler(f => {{
            const slice = S.atc_pr_trend[f.device] || S.atc_pr_trend.all;
            atcPrChart.data.datasets[0].data = slice.atc_rate;
            atcPrChart.data.datasets[1].data = slice.purchase_rate;
            atcPrChart.update('none');
        }});

        // ---- Tables (source + country) ----
        function deltaBadge(delta, deltaType) {{
            if (delta == null) return '';
            const up = delta > 0;
            const arrow = up ? '↑' : '↓';
            const sign = up ? '+' : '';
            const suffix = deltaType === 'pp' ? ' п.п.' : '%';
            const tone = up ? 'green' : 'red';
            return '<span class="delta delta-sm ' + tone + '">' + arrow + sign + delta + suffix + '</span>';
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
        const countryTbody = document.querySelector('#sum-country-table tbody');
        function renderCountryRow(r) {{
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
        }}
        function renderSummaryTables(dev) {{
            const src = S.source_table[dev] || S.source_table.all;
            const ctry = S.country_table[dev] || S.country_table.all;
            srcTbody.innerHTML = src.map(renderRow).join('');
            countryTbody.innerHTML = ctry.map(renderCountryRow).join('');
        }}
        renderSummaryTables(FILTERS.device);
        registerFilterHandler(f => renderSummaryTables(f.device));

        // ---- Rankings ----
        function renderRankings(dev) {{
            const atcRows = S.ranking_atc[dev] || S.ranking_atc.all;
            const prRows  = S.ranking_pr[dev]  || S.ranking_pr.all;
            document.getElementById('sum-ranking-atc').innerHTML = atcRows.map(r =>
                '<tr><td>' + r.source + '</td><td>' + r.country + '</td><td>' + r.user_type + '</td><td>' + r.sessions + '</td><td><b>' + r.atc_rate + '%</b></td></tr>'
            ).join('');
            document.getElementById('sum-ranking-pr').innerHTML = prRows.map(r =>
                '<tr><td>' + r.source + '</td><td>' + r.country + '</td><td>' + r.user_type + '</td><td>' + r.sessions + '</td><td><b>' + r.purchase_rate + '%</b></td></tr>'
            ).join('');
        }}
        renderRankings(FILTERS.device);
        registerFilterHandler(f => renderRankings(f.device));

        // ---- Scroll Rate (site-wide) — by device + by channel ----
        const A = DATA.analytics;
        if (A && A.scroll && A.scroll.length > 0) {{
            const scrollChannels = ['Social', 'Paid', 'Direct', 'Organic', 'Referral'];
            const chColors = {{
                Social:   cssvar('--c-channel-social'),
                Paid:     cssvar('--c-channel-paid'),
                Direct:   cssvar('--c-channel-direct'),
                Organic:  cssvar('--c-channel-organic'),
                Referral: cssvar('--c-channel-referral')
            }};
            const devColors = {{ mobile: cssvar('--c-channel-social'), desktop: cssvar('--c-channel-paid') }};
            const lineOpts = {{
                plugins: {{
                    legend: legendPresets.line,
                    datalabels: {{ ...dlPresets.line, formatter: v => fmt.pct(v, 1) }},
                    tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmt.pct(ctx.parsed.y, 1) }} }}
                }},
                scales: {{ y: {{ beginAtZero: true, max: 100, ticks: {{ callback: v => v + '%' }} }} }}
            }};
            const cvSiteDev = document.getElementById('sum-scroll-site-device');
            let scrollSiteDevChart = null;
            if (cvSiteDev) {{
                scrollSiteDevChart = new Chart(cvSiteDev, {{
                    type: 'line',
                    data: {{
                        labels: DATA.periods,
                        datasets: ['mobile', 'desktop'].map(dev => ({{
                            label: dev === 'mobile' ? 'Мобилка' : 'Десктоп',
                            _device: dev,
                            data: DATA.periods.map(p => scrollByDev(p, dev, 'site')),
                            borderColor: devColors[dev], tension: 0.3, borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                        }}))
                    }},
                    options: lineOpts
                }});
                registerFilterHandler(f => {{
                    scrollSiteDevChart.data.datasets.forEach(ds => {{
                        ds.hidden = f.device !== 'all' && ds._device !== f.device;
                    }});
                    scrollSiteDevChart.update('none');
                }});
            }}
            const cvSiteCh = document.getElementById('sum-scroll-site-channel');
            let scrollSiteChChart = null;
            if (cvSiteCh) {{
                scrollSiteChChart = new Chart(cvSiteCh, {{
                    type: 'line',
                    data: {{
                        labels: DATA.periods,
                        datasets: scrollChannels.map(ch => ({{
                            label: ch,
                            _channel: ch,
                            data: DATA.periods.map(p => scrollByCh(p, ch, 'site')),
                            borderColor: chColors[ch], tension: 0.3, borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, pointBorderWidth: 0,
                        }}))
                    }},
                    options: lineOpts
                }});
                registerFilterHandler(() => {{
                    // scrollByCh already consults FILTERS.device internally — recompute series.
                    scrollSiteChChart.data.datasets.forEach(ds => {{
                        ds.data = DATA.periods.map(p => scrollByCh(p, ds._channel, 'site'));
                    }});
                    scrollSiteChChart.update('none');
                }});
            }}
        }}

        // ---- Cohort Retention ----
        // Cohorts are partitioned by the device of the user's first_visit.
        // The chart's bars/percentages are rebuilt when the device filter flips.
        if (A && A.cohort && A.cohort.length > 0) {{
            function _buildCohortDatasets(device) {{
                const cohorts = {{}};
                A.cohort.forEach(r => {{
                    if (device !== 'all' && r.device !== device) return;
                    if (!cohorts[r.cohort_week]) cohorts[r.cohort_week] = {{}};
                    cohorts[r.cohort_week][r.weeks_since] =
                        (cohorts[r.cohort_week][r.weeks_since] || 0) + r.users;
                }});
                const cohortWeeks = Object.keys(cohorts).sort();
                const cohortLabels = cohortWeeks.map(w => w.replace('2026-', ''));
                const maxWeeksSince = 8;
                const palette = [
                    cssvar('--c-channel-social'),  cssvar('--c-channel-organic'), cssvar('--c-channel-paid'),    cssvar('--c-channel-referral'),
                    cssvar('--c-channel-email'),   cssvar('--c-channel-direct'),  cssvar('--tx-muted'),          cssvar('--bg-border')
                ];
                const retentionData = [];
                for (let ws = 0; ws <= maxWeeksSince; ws++) {{
                    retentionData.push({{
                        label: ws === 0 ? 'Неделя 0 (размер когорты)' : '+' + ws + ' нед.',
                        data: cohortWeeks.map(cw => {{
                            const week0 = cohorts[cw][0] || 1;
                            const weekN = cohorts[cw][ws] || 0;
                            return ws === 0 ? week0 : Math.round(weekN / week0 * 100);
                        }}),
                        backgroundColor: ws === 0 ? cssvar('--tx-primary') : palette[ws - 1],
                        hidden: ws === 0,
                    }});
                }}
                return {{ labels: cohortLabels, datasets: retentionData }};
            }}

            const cvCohort = document.getElementById('sum-cohort');
            if (cvCohort) {{
                const initial = _buildCohortDatasets(FILTERS.device);
                const cohortChart = new Chart(cvCohort, {{
                    type: 'bar',
                    data: {{ labels: initial.labels, datasets: initial.datasets }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ position: 'top' }},
                            datalabels: {{
                                display: ctx => ctx.dataset.data[ctx.dataIndex] > 0,
                                anchor: 'end', align: 'top', clamp: true,
                                font: {{ size: 10, weight: 'bold' }}, color: cssvar('--tx-primary'),
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
                registerFilterHandler(f => {{
                    const next = _buildCohortDatasets(f.device);
                    cohortChart.data.labels = next.labels;
                    next.datasets.forEach((ds, i) => {{
                        if (cohortChart.data.datasets[i]) {{
                            cohortChart.data.datasets[i].data = ds.data;
                        }}
                    }});
                    cohortChart.update('none');
                }});
            }}
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
    # Default ("unified") fetches day + week and ships them in one HTML so the user
    # can flip grain without a page reload. --grain day|week|month still produces
    # a single-grain file (used for the month CLI workflow until the M button reappears).
    parser.add_argument("--grain", choices=["day", "week", "month", "unified", "all"], default="unified")
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

    def _fetch_payload(g):
        print(f"Pinkspink Analytics — Building payload ({g})")
        rows = fetch_session_data(client, g)
        analytics = fetch_analytics_data(client, g)
        return generate_html(rows, g, EXCLUDED_COUNTRIES_DEFAULT, analytics, _payload_only=True)

    if args.grain in ("unified", "all"):
        # Build payloads for day + week and inject both into a single HTML.
        payload_day = _fetch_payload("day")
        payload_week = _fetch_payload("week")
        html = build_html({
            "_unified": True,
            "_default_grain": "week",
            "_payloads": {"day": payload_day, "week": payload_week},
            # Top-level "default" payload is used by SSR for the initial render.
            **payload_week,
        })
        out_path = os.path.join(base_dir, "report_week.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ Unified report saved to {out_path}")
        # Also write report_day.html as a copy so old D-button bookmarks still work.
        with open(os.path.join(base_dir, "report_day.html"), "w", encoding="utf-8") as f:
            f.write(html)
        if args.grain == "all":
            payload_month = _fetch_payload("month")
            html_month = build_html(payload_month)
            with open(os.path.join(base_dir, "report_month.html"), "w", encoding="utf-8") as f:
                f.write(html_month)
            print(f"  ✓ report_month.html written separately (CLI-only until July 2026)")
        print(f"\n  Open: file://{out_path}")
    else:
        print(f"Pinkspink Analytics — Generating single-grain report ({args.grain})")
        payload = _fetch_payload(args.grain)
        html = build_html(payload)
        out = os.path.join(base_dir, f"report_{args.grain}.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ Report saved to {out}")
        print(f"  Open in browser: file://{os.path.abspath(out)}")


if __name__ == "__main__":
    main()
