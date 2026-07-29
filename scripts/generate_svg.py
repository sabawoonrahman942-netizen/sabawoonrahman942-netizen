#!/usr/bin/env python3
"""
Turns data.json into assets/dashboard.svg, styled like the new
reference dashboard image (stat cards + sparklines, GitHub Score ring,
contribution heatmap, language donut, stars-over-time chart, Tech
Stack panel and footer bar).
"""

import json
import math
import os

BASE = os.path.join(os.path.dirname(__file__), "..")

BG = "#0b0e17"
CARD = "#121523"
BORDER = "#232841"
TEXT = "#e7e9f5"
MUTED = "#8b90ab"
VIOLET = "#8b5cf6"

LANG_COLORS = ["#3b82f6", "#f97316", "#8b5cf6", "#8b90ab", "#22c55e", "#eab308", "#06b6d4"]

WIDTH = 1536
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------- widgets ---

def sparkline(x, y, w, h, values, color):
    values = values or [0]
    if max(values) == 0:
        values = [1] * len(values)
    mn, mx = min(values), max(values)
    rng = (mx - mn) or 1
    pts = []
    for i, v in enumerate(values):
        px = x + i * (w / (len(values) - 1 or 1))
        py = y + h - ((v - mn) / rng) * h
        pts.append((px, py))
    poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{pts[0][0]:.1f},{y+h:.1f} " + poly + f" {pts[-1][0]:.1f},{y+h:.1f}"
    return (
        f'<polygon points="{area}" fill="{color}" opacity="0.15"/>'
        f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/>'
    )


def score_ring(cx, cy, r, pct, grade, color="#eab308"):
    circumference = 2 * math.pi * r
    dash = circumference * pct / 100
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BORDER}" stroke-width="9"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="9" '
        f'stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}" '
        f'transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy+9}" font-size="26" font-weight="700" fill="{TEXT}" text-anchor="middle">{grade}</text>'
    )


def donut(cx, cy, r_outer, r_inner, languages):
    parts, angle = [], -90.0
    for i, lang in enumerate(languages):
        color = LANG_COLORS[i % len(LANG_COLORS)]
        sweep = lang["pct"] / 100 * 360
        a0, a1 = math.radians(angle), math.radians(angle + sweep)
        x0, y0 = cx + r_outer * math.cos(a0), cy + r_outer * math.sin(a0)
        x1, y1 = cx + r_outer * math.cos(a1), cy + r_outer * math.sin(a1)
        large = 1 if sweep > 180 else 0
        parts.append(
            f'<path d="M{cx},{cy} L{x0:.2f},{y0:.2f} A{r_outer},{r_outer} 0 {large} 1 '
            f'{x1:.2f},{y1:.2f} Z" fill="{color}"/>'
        )
        angle += sweep
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_inner}" fill="{CARD}"/>')
    return "".join(parts)


def heatmap(weeks, x, y, cell=11, gap=3, n_weeks=52):
    recent = weeks[-n_weeks:]
    svg = []
    month_labels = []
    seen_months = set()
    for wi, w in enumerate(recent):
        for di, d in enumerate(w["contributionDays"]):
            c = d["contributionCount"]
            color = "#1c2036" if c == 0 else "#2f6f3e" if c <= 2 else "#3fa955" if c <= 5 else "#4ade80"
            cx_ = x + wi * (cell + gap)
            cy_ = y + di * (cell + gap)
            svg.append(f'<rect x="{cx_:.1f}" y="{cy_:.1f}" width="{cell}" height="{cell}" rx="2" fill="{color}"/>')
            date = d.get("date", "")
            if date:
                key = date[:7]
                if key not in seen_months:
                    seen_months.add(key)
                    m = int(date[5:7])
                    month_labels.append((wi, MONTH_ABBR[m - 1]))
    for wi, label in month_labels:
        svg.append(f'<text x="{x+wi*(cell+gap)}" y="{y-10}" font-size="10" fill="{MUTED}">{label}</text>')
    day_labels = ["", "Mon", "", "Wed", "", "Fri", ""]
    for di, lbl in enumerate(day_labels):
        if lbl:
            svg.append(f'<text x="{x-45}" y="{y+di*(cell+gap)+9}" font-size="10" fill="{MUTED}">{lbl}</text>')
    return "".join(svg)


def line_chart(x, y, w, h, values, labels, color=VIOLET):
    mx = max(values) if values and max(values) > 0 else 1
    svg = []
    for gy in range(5):
        yy = y + h - gy * (h / 4)
        svg.append(f'<line x1="{x}" y1="{yy:.1f}" x2="{x+w}" y2="{yy:.1f}" stroke="{BORDER}" stroke-width="1"/>')
    pts = []
    for i, v in enumerate(values):
        px = x + i * (w / (len(values) - 1 or 1))
        py = y + h - (v / mx) * h
        pts.append((px, py))
    poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{pts[0][0]:.1f},{y+h:.1f} " + poly + f" {pts[-1][0]:.1f},{y+h:.1f}"
    svg.append(f'<polygon points="{area}" fill="{color}" opacity="0.18"/>')
    svg.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.5"/>')
    for px, py in pts:
        svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{color}"/>')
    for (px, _), lbl in zip(pts, labels):
        svg.append(f'<text x="{px:.1f}" y="{y+h+18}" font-size="10" fill="{MUTED}" text-anchor="middle">{lbl}</text>')
    return "".join(svg)


# ---------------------------------------------------------- score/trend ---

def compute_score(stats):
    raw = (
        min(stats["total_stars"], 500) / 500 * 35
        + min(stats["total_repos"], 100) / 100 * 20
        + min(stats["total_prs"], 200) / 200 * 20
        + min(stats["followers"], 200) / 200 * 15
        + min(stats["contributors"], 30) / 30 * 10
    )
    return max(1, min(100, round(raw)))


def grade_from_score(score):
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B+"
    if score >= 60: return "B"
    if score >= 45: return "C"
    return "D"


def simple_trend(total, points=12, seed=1.0):
    """Toplam bir sayidan gorsel olarak makul, artan bir egilim serisi turetir.
    Aylik kirilim GitHub API'sinde bazi metrikler icin (PR/issue) ucretsiz
    alinamadigindan bu bir yaklasimdir; toplam deger gercek ve dogrudur."""
    if total <= 0:
        return [0] * points
    weights = [0.4 + 0.6 * (i / (points - 1)) + 0.15 * math.sin(i * seed) for i in range(points)]
    s = sum(weights)
    acc, out = 0, []
    for wgt in weights:
        acc += total * wgt / s
        out.append(round(acc))
    out[-1] = total
    return out


TECH_CATEGORIES = [
    {"title": "Development", "icon": "💻", "color": "#a78bfa", "tools": [
        {"name": "Python", "icon": "🐍"}, {"name": "Git", "icon": "🔶"}, {"name": "GitHub", "icon": "🐙"},
        {"name": "Docker", "icon": "🐳"}, {"name": "Linux", "icon": "🐧"}, {"name": "VS Code", "icon": "🧩"},
    ]},
    {"title": "Databases", "icon": "🗄️", "color": "#60a5fa", "tools": [
        {"name": "MySQL", "icon": "🐬"}, {"name": "PostgreSQL", "icon": "🐘"}, {"name": "MongoDB", "icon": "🍃"},
    ]},
    {"title": "Analytics &amp; Data Science", "icon": "📊", "color": "#4ade80", "tools": [
        {"name": "pandas", "icon": "🐼"}, {"name": "NumPy", "icon": "🔢"}, {"name": "Matplotlib", "icon": "📈"},
        {"name": "Seaborn", "icon": "🌊"}, {"name": "Plotly", "icon": "📉"},
    ]},
    {"title": "Data Engineering", "icon": "⚙️", "color": "#fb923c", "tools": [
        {"name": "Spark", "icon": "✨"}, {"name": "Airflow", "icon": "🌬️"}, {"name": "Kafka", "icon": "🔗"},
    ]},
    {"title": "Cloud &amp; Platforms", "icon": "☁️", "color": "#38bdf8", "tools": [
        {"name": "AWS", "icon": "☁️"}, {"name": "Azure Data Factory", "icon": "🏭"}, {"name": "BigQuery", "icon": "🔷"},
    ]},
]


# --------------------------------------------------------------- build ---

def build(data):
    stats = data["stats"]
    languages = data["languages"]
    score = compute_score(stats)
    grade = grade_from_score(score)
    score_label = "Excellent" if score >= 80 else "Good" if score >= 60 else "Growing"

    s = []
    A = s.append

    def card(x, y, w, h, stroke=BORDER):
        A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{stroke}"/>')

    # ---- header ----
    header_h = 100
    A(f'<text x="40" y="46" font-size="30" font-weight="700" fill="{TEXT}">📊 GitHub Analytics</text>')
    A(f'<text x="40" y="72" font-size="14" fill="{MUTED}">My GitHub journey in numbers — @{esc(data["username"])}</text>')
    A(f'<circle cx="{WIDTH-235}" cy="34" r="5" fill="#22c55e"/>')
    A(f'<text x="{WIDTH-222}" y="39" font-size="14" font-weight="700" fill="#22c55e">LIVE DATA</text>')
    A(f'<text x="{WIDTH-235}" y="58" font-size="11" fill="{MUTED}">Data updates automatically</text>')
    A(f'<rect x="40" y="{header_h}" width="{WIDTH-80}" height="2" fill="url(#hgrad)"/>')
    A(f'<defs><linearGradient id="hgrad" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="#3b82f6"/></linearGradient></defs>')

    # ---- 6 stat cards ----
    row1_y = header_h + 25
    card_w, card_h, gap = 240, 175, 16
    stat_defs = [
        ("⭐", "#a78bfa", "Total Stars Earned", stats["total_stars"], simple_trend(stats["total_stars"], seed=1.1)),
        ("&lt;/&gt;", "#60a5fa", "Total Commits", stats["total_commits"], simple_trend(stats["total_commits"], seed=0.9)),
        ("🔀", "#4ade80", "Total PRs", stats["total_prs"], simple_trend(stats["total_prs"], seed=1.3)),
        ("🐛", "#fb923c", "Issues Closed", stats["issues_closed"], simple_trend(stats["issues_closed"], seed=0.7)),
        ("👥", "#2dd4bf", "Contributors", stats["contributors"], simple_trend(stats["contributors"], seed=1.6)),
        (None, None, None, None, None),  # score card
    ]
    for i, (icon, color, label, value, trend) in enumerate(stat_defs):
        cx0 = 40 + i * (card_w + gap)
        card(cx0, row1_y, card_w, card_h)
        if icon is None:
            A(f'<text x="{cx0+22}" y="{row1_y+34}" font-size="14" font-weight="600" fill="{TEXT}">🏆 GitHub Score</text>')
            A(score_ring(cx0 + card_w / 2, row1_y + 105, 45, score, grade))
            A(f'<text x="{cx0+card_w/2}" y="{row1_y+card_h-14}" font-size="12" font-weight="600" fill="#eab308" text-anchor="middle">{score_label}</text>')
            continue
        A(f'<circle cx="{cx0+30}" cy="{row1_y+32}" r="18" fill="{color}22"/>')
        A(f'<text x="{cx0+30}" y="{row1_y+38}" font-size="15" fill="{color}" text-anchor="middle">{icon}</text>')
        A(f'<text x="{cx0+58}" y="{row1_y+28}" font-size="13" fill="{MUTED}">{esc(label)}</text>')
        A(f'<text x="{cx0+58}" y="{row1_y+60}" font-size="26" font-weight="700" fill="{TEXT}">{value:,}</text>')
        A(sparkline(cx0 + 18, row1_y + 100, card_w - 36, 55, trend, color))

    # ---- row 2 ----
    row2_y = row1_y + card_h + 20
    row2_h = 260

    heat_w = 560
    card(40, row2_y, heat_w, row2_h)
    A(f'<text x="60" y="{row2_y+32}" font-size="15" font-weight="600" fill="{TEXT}">🔥 Contribution Activity</text>')
    A(heatmap(data["weeks"], x=105, y=row2_y + 55))
    A(f'<text x="60" y="{row2_y+row2_h-20}" font-size="12" fill="#4ade80">🔥 Current streak: {data["streak"]["current"]} days</text>')
    A(f'<text x="{40+heat_w-190}" y="{row2_y+row2_h-20}" font-size="12" fill="{MUTED}">Longest streak: {data["streak"]["longest"]} days</text>')

    lang_x, lang_w = 40 + heat_w + 16, 430
    card(lang_x, row2_y, lang_w, row2_h)
    A(f'<text x="{lang_x+20}" y="{row2_y+32}" font-size="15" font-weight="600" fill="{TEXT}">&lt;/&gt; Languages by Commit</text>')
    A(donut(lang_x + 95, row2_y + 140, 68, 40, languages))
    ly = row2_y + 65
    for i, lang in enumerate(languages):
        color = LANG_COLORS[i % len(LANG_COLORS)]
        A(f'<circle cx="{lang_x+195}" cy="{ly-5}" r="5" fill="{color}"/>')
        A(f'<text x="{lang_x+210}" y="{ly}" font-size="12" fill="{TEXT}">{esc(lang["name"])}</text>')
        A(f'<text x="{lang_x+lang_w-25}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">{lang["pct"]}%</text>')
        ly += 26

    stars_x = lang_x + lang_w + 16
    stars_w = WIDTH - stars_x - 40
    card(stars_x, row2_y, stars_w, row2_h)
    A(f'<text x="{stars_x+20}" y="{row2_y+32}" font-size="15" font-weight="600" fill="{TEXT}">⭐ Stars Earned (Last 12 Months)</text>')
    A(line_chart(stars_x + 45, row2_y + 55, stars_w - 80, row2_h - 110, data["stars_monthly"], data["stars_month_labels"]))

    # ---- Tech Stack ----
    ts_y = row2_y + row2_h + 30
    A(f'<line x1="40" y1="{ts_y+18}" x2="{WIDTH/2-140}" y2="{ts_y+18}" stroke="{VIOLET}" stroke-width="2"/>')
    A(f'<text x="{WIDTH/2}" y="{ts_y+26}" font-size="24" font-weight="700" fill="{TEXT}" text-anchor="middle">🚀 Tech Stack</text>')
    A(f'<line x1="{WIDTH/2+140}" y1="{ts_y+18}" x2="{WIDTH-40}" y2="{ts_y+18}" stroke="{VIOLET}" stroke-width="2"/>')

    ts_cards_y = ts_y + 50
    ts_h = 260
    ts_gap = 15
    ts_w = (WIDTH - 80 - ts_gap * (len(TECH_CATEGORIES) - 1)) / len(TECH_CATEGORIES)
    for i, cat in enumerate(TECH_CATEGORIES):
        cx0 = 40 + i * (ts_w + ts_gap)
        card(cx0, ts_cards_y, ts_w, ts_h, stroke=cat["color"] + "55")
        A(f'<text x="{cx0+16}" y="{ts_cards_y+30}" font-size="14" font-weight="700" fill="{cat["color"]}">{cat["icon"]} {cat["title"]}</text>')
        cols, pad, gy = 3, 18, 55
        for j, tool in enumerate(cat["tools"]):
            col, row = j % cols, j // cols
            ix = cx0 + pad + col * ((ts_w - 2 * pad) / cols)
            iy = ts_cards_y + gy + row * 78
            A(f'<circle cx="{ix+22}" cy="{iy+22}" r="22" fill="#ffffff10" stroke="{BORDER}"/>')
            A(f'<text x="{ix+22}" y="{iy+29}" font-size="18" text-anchor="middle">{tool["icon"]}</text>')
            A(f'<text x="{ix+22}" y="{iy+58}" font-size="10.5" fill="{MUTED}" text-anchor="middle">{esc(tool["name"])}</text>')

    # ---- footer ----
    footer_y = ts_cards_y + ts_h + 30
    A(f'<line x1="40" y1="{footer_y}" x2="{WIDTH-40}" y2="{footer_y}" stroke="{BORDER}"/>')
    A(f'<text x="40" y="{footer_y+30}" font-size="12" fill="{MUTED}">🌐 Data is fetched live from GitHub API</text>')
    A(f'<text x="440" y="{footer_y+30}" font-size="12" fill="{MUTED}">⏱ Auto-updated every 30 minutes</text>')
    A(f'<text x="780" y="{footer_y+30}" font-size="12" fill="{MUTED}">🌍 Last update: {esc(data["generated_at"])}</text>')
    A(f'<rect x="{WIDTH-260}" y="{footer_y+6}" width="220" height="34" rx="8" fill="none" stroke="{VIOLET}"/>')
    A(f'<text x="{WIDTH-150}" y="{footer_y+28}" font-size="12" fill="{VIOLET}" text-anchor="middle">💜 Thanks for visiting!</text>')

    total_h = footer_y + 60
    return (
        f'<svg viewBox="0 0 {WIDTH} {total_h}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="\'Segoe UI\', Helvetica, Arial, sans-serif">'
        f'<rect width="{WIDTH}" height="{total_h}" fill="{BG}"/>' + "".join(s) + "</svg>"
    )


def main():
    with open(os.path.join(BASE, "data.json")) as f:
        data = json.load(f)
    svg = build(data)
    out_path = os.path.join(BASE, "assets", "dashboard.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(svg)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
