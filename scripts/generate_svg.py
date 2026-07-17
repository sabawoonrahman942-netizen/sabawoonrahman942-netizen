#!/usr/bin/env python3
"""
Turns data.json into assets/dashboard.svg, styled like the reference
dark GitHub-Analytics dashboard image.
"""

import json
import math
import os

BASE = os.path.join(os.path.dirname(__file__), "..")

BG = "#0d1117"
CARD_BG = "#111826"
BORDER = "#22283a"
TEXT = "#e6e6ef"
SUBTEXT = "#8b8fa3"
PURPLE = "#8b5cf6"
GREEN = "#22c55e"
YELLOW = "#eab308"
BLUE = "#3b82f6"
CYAN = "#06b6d4"
ORANGE = "#f97316"
GREY = "#6b7280"

LANG_COLORS = [PURPLE, BLUE, YELLOW, CYAN, GREEN, ORANGE, GREY]

WIDTH = 1200


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def heatmap_svg(weeks, x0, y0, total_width, n_weeks=53):
    """Fits n_weeks columns x 7 rows into total_width, preserving square-ish cells."""
    svg = []
    recent = weeks[-n_weeks:]
    step = total_width / len(recent)
    cell = max(2.0, step * 0.72)
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    max_c = max(counts) if counts else 1
    for wi, w in enumerate(recent):
        for di, d in enumerate(w["contributionDays"]):
            c = d["contributionCount"]
            if c == 0:
                color = "#161b22"
            else:
                level = min(4, math.ceil((c / max_c) * 4)) if max_c else 0
                color = ["#161b22", "#3b2a6e", "#5c3fae", "#8b5cf6", "#c4b5fd"][level]
            x = x0 + wi * step
            y = y0 + di * step
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="1.5" fill="{color}"/>')
    return "".join(svg)


def donut_svg(languages, cx, cy, r, stroke=26):
    svg = []
    start = -90.0
    circumference = 2 * math.pi * r
    for i, lang in enumerate(languages):
        pct = lang["pct"]
        frac = pct / 100.0
        dash = frac * circumference
        color = LANG_COLORS[i % len(LANG_COLORS)]
        rot = start
        svg.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {circumference:.2f}" '
            f'transform="rotate({rot:.2f} {cx} {cy})"/>'
        )
        start += frac * 360
    return "".join(svg)


def line_chart_svg(months, x0, y0, w, h):
    max_v = max(months) if months and max(months) > 0 else 1
    pts = []
    n = len(months)
    for i, v in enumerate(months):
        x = x0 + (i / (n - 1)) * w
        y = y0 + h - (v / max_v) * h
        pts.append((x, y))

    path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = path + f" L {pts[-1][0]:.1f},{y0+h} L {pts[0][0]:.1f},{y0+h} Z"

    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{PURPLE}" stroke="{BG}" stroke-width="1.5"/>'
        for x, y in pts
    )

    grid = "".join(
        f'<line x1="{x0}" y1="{y0 + h * (1 - g/4)}" x2="{x0+w}" y2="{y0 + h * (1 - g/4)}" '
        f'stroke="{BORDER}" stroke-width="1" stroke-dasharray="4 4"/>'
        for g in range(5)
    )

    return f"""
    {grid}
    <path d="{area}" fill="{PURPLE}" fill-opacity="0.15" stroke="none"/>
    <path d="{path}" fill="none" stroke="{PURPLE}" stroke-width="3"/>
    {dots}
    """


def build(data):
    stats = data["stats"]
    streak = data["streak"]
    languages = data["languages"]
    months = data["months"]
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    height = 980

    heatmap = heatmap_svg(data["weeks"], x0=40, y0=170, total_width=350)
    donut = donut_svg(languages, cx=890, cy=260, r=62, stroke=24)
    chart = line_chart_svg(months, x0=90, y0=680, w=1050, h=180)

    lang_rows = ""
    for i, lang in enumerate(languages):
        color = LANG_COLORS[i % len(LANG_COLORS)]
        y = 175 + i * 27
        lang_rows += f"""
        <circle cx="990" cy="{y-5}" r="5" fill="{color}"/>
        <text x="1005" y="{y}" fill="{TEXT}" font-size="14">{esc(lang['name'])}</text>
        <text x="1180" y="{y}" fill="{SUBTEXT}" font-size="14" text-anchor="end">{lang['pct']}%</text>
        """

    stat_rows_data = [
        ("Total Repositories", stats["total_repos"], PURPLE),
        ("Total Stars Earned", stats["total_stars"], YELLOW),
        ("Total Commits", stats["total_commits"], GREEN),
        ("Total PRs", stats["total_prs"], YELLOW),
        ("Followers", stats["followers"], PURPLE),
        ("Following", stats["following"], BLUE),
    ]
    stat_rows = ""
    for i, (label, value, color) in enumerate(stat_rows_data):
        y = 175 + i * 34
        stat_rows += f"""
        <text x="440" y="{y}" fill="{TEXT}" font-size="15">{esc(label)}</text>
        <text x="775" y="{y}" fill="{color}" font-size="16" font-weight="600" text-anchor="end">{value}</text>
        """

    footer_stats = [
        ("Current Streak", f'{streak["current"]}', "days"),
        ("Longest Streak", f'{streak["longest"]}', "days"),
        ("Total Contributions", f'{streak["total_contributions"]}', ""),
        ("Active Year", f'{streak["active_year"]}', ""),
    ]
    footer_svg = ""
    for i, (label, value, unit) in enumerate(footer_stats):
        x = 40 + i * 145
        footer_svg += f"""
        <text x="{x}" y="400" fill="{TEXT}" font-size="20" font-weight="700">{esc(value)} {esc(unit)}</text>
        <text x="{x}" y="420" fill="{SUBTEXT}" font-size="12">{esc(label)}</text>
        """

    month_axis = "".join(
        f'<text x="{90 + i*(1050/11):.0f}" y="885" fill="{SUBTEXT}" font-size="12" text-anchor="middle">{m}</text>'
        for i, m in enumerate(month_labels)
    )

    svg = f"""<svg viewBox="0 0 {WIDTH} {height}" xmlns="http://www.w3.org/2000/svg" font-family="'Segoe UI', Helvetica, Arial, sans-serif">
  <rect width="{WIDTH}" height="{height}" fill="{BG}"/>

  <text x="40" y="50" fill="{TEXT}" font-size="26" font-weight="700">📊 GitHub Analytics</text>
  <text x="40" y="78" fill="{SUBTEXT}" font-size="14">My GitHub journey in numbers &#8212; @{esc(data['username'])}</text>
  <rect x="40" y="90" width="120" height="3" fill="{PURPLE}"/>

  <rect x="20" y="120" width="400" height="330" rx="14" fill="{CARD_BG}" stroke="{BORDER}"/>
  <text x="40" y="150" fill="{TEXT}" font-size="16" font-weight="600">📈 Contributions Overview</text>
  {heatmap}
  {footer_svg}

  <rect x="430" y="120" width="360" height="330" rx="14" fill="{CARD_BG}" stroke="{BORDER}"/>
  <text x="440" y="150" fill="{TEXT}" font-size="16" font-weight="600">⚡ GitHub Stats</text>
  {stat_rows}

  <rect x="800" y="120" width="400" height="330" rx="14" fill="{CARD_BG}" stroke="{BORDER}"/>
  <text x="820" y="150" fill="{TEXT}" font-size="16" font-weight="600">&lt;&gt; Most Used Languages</text>
  {donut}
  {lang_rows}

  <rect x="20" y="470" width="1160" height="440" rx="14" fill="{CARD_BG}" stroke="{BORDER}"/>
  <text x="40" y="505" fill="{TEXT}" font-size="16" font-weight="600">📊 Contribution Activity</text>
  {chart}
  {month_axis}

  <text x="{WIDTH-40}" y="{height-20}" fill="{SUBTEXT}" font-size="12" text-anchor="end">Last updated: {esc(data['generated_at'])}</text>
</svg>"""
    return svg


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
