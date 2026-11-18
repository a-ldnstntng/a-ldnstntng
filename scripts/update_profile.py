"""Fetch live GitHub profile metrics & 52-week calendar and regenerate Mashup 1 contributions SVGs."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

THEMES = {
    "dark": {
        "card_bg": "#0d1014",
        "border": "#262a33",
        "text": "#f3f4f6",
        "muted": "#8b949e",
        "label": "#6e7681",
        "levels": ["#161a20", "#5c2b12", "#a16207", "#eab308", "#fde047"],
        "rain": "#44577d",
        "rain_hi": "#8396b8",
    },
    "light": {
        "card_bg": "#ffffff",
        "border": "#d0d7de",
        "text": "#1f2328",
        "muted": "#57606a",
        "label": "#6e7781",
        "levels": ["#ebedf0", "#fef08a", "#facc15", "#eab308", "#ca8a04"],
        "rain": "#94a3b8",
        "rain_hi": "#64748b",
    },
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
X0, Y0, PITCH, SIZE = 48, 56, 15, 11


def fetch_github_data(username: str, token: str) -> dict:
    """Query GitHub GraphQL API for repository count, contribution totals, and 52-week grid."""
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(privacy: PUBLIC) {
          totalCount
        }
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalPullRequestReviewContributions
          contributionCalendar {
            totalContributions
            weeks {
              firstDay
              contributionDays {
                weekday
                contributionLevel
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{username}-profile-updater",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")
    return data["data"]["user"]


def pixel_diagonal_slash(x1: int, y1: int, x2: int, y2: int) -> str:
    """Build a tapered stepped pixel diagonal cleave with dithered wake."""
    steps = max(4, max(abs(x2 - x1), abs(y2 - y1)) // 3)
    rects = []
    for i in range(steps + 1):
        u = i / float(steps)
        px = round((x1 + (x2 - x1) * u) / 3) * 3
        py = round((y1 + (y2 - y1) * u) / 3) * 3
        if 0.22 <= u <= 0.78:
            rects.append(f'<rect x="{px - 3}" y="{py - 3}" width="9" height="9" fill="#eab308" fill-opacity="0.45"/>')
            rects.append(f'<rect x="{px}" y="{py}" width="6" height="6" fill="#fde047"/>')
            rects.append(f'<rect x="{px + 1}" y="{py + 1}" width="3" height="3" fill="#ffffff"/>')
        elif 0.10 <= u <= 0.90:
            rects.append(f'<rect x="{px}" y="{py}" width="4" height="4" fill="#fde047"/>')
        else:
            rects.append(f'<rect x="{px}" y="{py}" width="3" height="3" fill="#a16207"/>')
        if i % 3 == 0 and 0.18 <= u <= 0.82:
            rects.append(f'<rect x="{px - 9}" y="{py + 3}" width="3" height="3" fill="#eab308" fill-opacity="0.7"/>')
            rects.append(f'<rect x="{px - 15}" y="{py - 3}" width="3" height="3" fill="#a16207" fill-opacity="0.55"/>')
    return "".join(rects)


def update_hero_counts(repo_count: int, total_contribs: int) -> None:
    """Update REPOSITORIES and CONTRIBUTIONS numbers in hero-dark.svg and hero-light.svg."""
    for name in ("hero-dark.svg", "hero-light.svg"):
        path = ASSETS / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r'(<text id="stat-repos"[^>]*>)[^<]*(</text>)',
            rf"\g<1>{repo_count}\g<2>",
            text,
        )
        text = re.sub(
            r'(<text id="stat-contribs"[^>]*>)[^<]*(</text>)',
            rf"\g<1>{total_contribs}\g<2>",
            text,
        )
        path.write_text(text, encoding="utf-8")


def render_contributions_svg(theme_name: str, user_data: dict) -> None:
    """Render Mashup 1 (Rain + Cleave + Petals) contributions SVG from live GitHub data."""
    t = THEMES[theme_name]
    col_data = user_data["contributionsCollection"]
    cal = col_data["contributionCalendar"]
    total = int(cal["totalContributions"])
    weeks = cal["weeks"][-52:]

    commits = int(col_data.get("totalCommitContributions", 0))
    prs = int(col_data.get("totalPullRequestContributions", 0))
    issues = int(col_data.get("totalIssueContributions", 0))
    reviews = int(col_data.get("totalPullRequestReviewContributions", 0))
    denom = max(1, commits + prs + issues + reviews)
    commit_pct = round((commits / denom) * 100)
    pr_pct = 100 - commit_pct
    breakdown = f"{commit_pct}% COMMITS  ·  {pr_pct}% PULL REQUESTS" if prs > 0 or pr_pct == 0 else f"{commit_pct}% COMMITS  ·  {pr_pct}% OTHER"

    # Build 52x7 grid & month labels
    cols = len(weeks)
    grid = [[0 for _ in range(cols)] for _ in range(7)]
    month_positions = []
    last_month = None
    active_spots = []

    for c, week in enumerate(weeks):
        first_day = dt.date.fromisoformat(week["firstDay"])
        m_label = MONTH_NAMES[first_day.month - 1]
        if m_label != last_month and (not month_positions or c - month_positions[-1][0] >= 3):
            month_positions.append((c, m_label))
            last_month = m_label
        for day in week["contributionDays"]:
            r = int(day["weekday"])
            lvl = LEVEL_MAP.get(day["contributionLevel"], 0)
            grid[r][c] = lvl
            if lvl > 0:
                active_spots.append((c, r, lvl))

    # Pick up to 3 active spots well-spaced across early/mid/late year for subtle gold ripples
    ripples = []
    if active_spots:
        early = [s for s in active_spots if s[0] < 18]
        mid = [s for s in active_spots if 18 <= s[0] < 38]
        late = [s for s in active_spots if s[0] >= 38]
        picks = [p[-1] for p in (early, mid, late) if p]
        for idx, (sc, sr, _) in enumerate(picks):
            rx = X0 + sc * PITCH + 5
            ry = Y0 + sr * PITCH + 5
            rdel = -0.4 - idx * 1.1
            ripples.append(
                f'<rect x="{rx - 7}" y="{ry - 7}" width="14" height="14" rx="2" stroke="#fde047" stroke-width="1.5" fill="none" '
                f'style="transform-box: fill-box; transform-origin: center; animation: rippleOut 3.6s ease-out {rdel:.1f}s infinite;"/>'
            )

    # Position final X cross-cleave over the peak 10-column window
    best_start = max(0, cols - 10)
    best_score = -1
    for s in range(0, max(1, cols - 9)):
        score = sum(grid[r][c] for c in range(s, min(cols, s + 10)) for r in range(7))
        if score >= best_score:
            best_score = score
            best_start = s
    x_left = X0 + best_start * PITCH
    x_right = min(824, x_left + 146)

    base_cells, active_cells, flash_rects = [], [], []
    for c in range(cols):
        for r in range(7):
            cx, cy = X0 + c * PITCH, Y0 + r * PITCH
            base_cells.append(f'<rect x="{cx}" y="{cy}" width="{SIZE}" height="{SIZE}" rx="1.5" fill="{t["levels"][0]}"/>')
            lvl = grid[r][c]
            if lvl > 0:
                active_cells.append(f'<rect x="{cx}" y="{cy}" width="{SIZE}" height="{SIZE}" rx="1.5" fill="{t["levels"][lvl]}"/>')
                if 18 <= c <= 35:
                    flash_rects.append(f'<rect class="mfl1" x="{cx}" y="{cy}" width="{SIZE}" height="{SIZE}" rx="1.5" fill="#ffffff"/>')
                elif best_start <= c <= best_start + 10:
                    flash_rects.append(f'<rect class="mfl2" x="{cx}" y="{cy}" width="{SIZE}" height="{SIZE}" rx="1.5" fill="#ffffff"/>')

    drops = [
        (108, 0.0, 2.7), (204, -1.2, 2.9), (312, -0.6, 2.5),
        (418, -1.8, 2.8), (528, -0.9, 2.6), (628, -2.1, 2.7),
        (718, -0.4, 2.5), (795, -1.5, 2.8),
    ]
    rain_svg = "".join(
        f'<g style="animation: rainDrop {dur:.1f}s linear {delay:.1f}s infinite;">'
        f'<rect x="{dx}" y="42" width="2" height="6" fill="{t["rain"]}" fill-opacity="0.75"/>'
        f'<rect x="{dx - 2}" y="48" width="2" height="6" fill="{t["rain_hi"]}" fill-opacity="0.8"/>'
        f'</g>'
        for dx, delay, dur in drops
    )

    cut_mid = pixel_diagonal_slash(320, 58, 520, 162)
    cut_xa = pixel_diagonal_slash(x_left, 56, x_right, 162)
    cut_xb = pixel_diagonal_slash(x_right - 2, 58, x_left + 2, 162)
    petal_x = (x_left + x_right) // 2

    month_txt = "".join(
        f'<text x="{X0 + c * PITCH}" y="49" fill="{t["label"]}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9">{m}</text>'
        for c, m in month_positions
    )
    legend = "".join(
        f'<rect x="{748 + idx * 14}" y="182" width="10" height="10" rx="1.5" fill="{lcol}"/>'
        for idx, lcol in enumerate(t["levels"])
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="848" height="212" viewBox="0 0 848 212" fill="none">
  <defs>
    <clipPath id="m1-clip">
      <rect x="44" y="52" width="788" height="114"/>
    </clipPath>
    <style>
      @keyframes rainDrop {{
        0%   {{ transform: translate(18px, -16px); opacity: 0; }}
        15%  {{ opacity: 0.65; }}
        85%  {{ opacity: 0.65; }}
        100% {{ transform: translate(-42px, 128px); opacity: 0; }}
      }}
      @keyframes rippleOut {{
        0%   {{ transform: scale(0.75); opacity: 0; }}
        18%  {{ opacity: 0.85; }}
        100% {{ transform: scale(2.05); opacity: 0; }}
      }}
      @keyframes mSlash1 {{
        0%, 16%  {{ opacity: 0; transform: translate(-16px, -12px) scale(0.86); }}
        18%      {{ opacity: 1; transform: translate(0px, 0px) scale(1); }}
        25%      {{ opacity: 0.8; transform: translate(6px, 4px); }}
        36%, 100% {{ opacity: 0; transform: translate(10px, 6px); }}
      }}
      @keyframes mSlash2a {{
        0%, 46%  {{ opacity: 0; transform: translate(-14px, -12px) scale(0.88); }}
        48%      {{ opacity: 1; transform: translate(0px, 0px) scale(1); }}
        57%      {{ opacity: 0.85; transform: translate(4px, 3px); }}
        72%, 100% {{ opacity: 0; transform: translate(8px, 6px); }}
      }}
      @keyframes mSlash2b {{
        0%, 51%  {{ opacity: 0; transform: translate(14px, -12px) scale(0.88); }}
        53%      {{ opacity: 1; transform: translate(0px, 0px) scale(1); }}
        62%      {{ opacity: 0.85; transform: translate(-4px, 3px); }}
        77%, 100% {{ opacity: 0; transform: translate(-8px, 6px); }}
      }}
      @keyframes mFlash1 {{ 0%, 17% {{ opacity: 0; }} 18.5% {{ opacity: 0.9; }} 34%, 100% {{ opacity: 0; }} }}
      @keyframes mFlash2 {{ 0%, 47% {{ opacity: 0; }} 53.5% {{ opacity: 0.95; }} 72%, 100% {{ opacity: 0; }} }}
      @keyframes mPetalA {{
        0%, 49%  {{ opacity: 0; transform: translate(0px, 0px); }}
        55%      {{ opacity: 0.95; }}
        92%      {{ opacity: 0.72; }}
        100%     {{ opacity: 0; transform: translate(-240px, 28px); }}
      }}
      @keyframes mPetalB {{
        0%, 52%  {{ opacity: 0; transform: translate(0px, 0px); }}
        58%      {{ opacity: 0.9; }}
        94%      {{ opacity: 0.68; }}
        100%     {{ opacity: 0; transform: translate(-290px, -20px); }}
      }}
      .ms1 {{ transform-box: fill-box; transform-origin: center; opacity: 0; animation: mSlash1 8.5s cubic-bezier(0.16, 1, 0.3, 1) infinite; }}
      .ms2a {{ transform-box: fill-box; transform-origin: center; opacity: 0; animation: mSlash2a 8.5s cubic-bezier(0.16, 1, 0.3, 1) infinite; }}
      .ms2b {{ transform-box: fill-box; transform-origin: center; opacity: 0; animation: mSlash2b 8.5s cubic-bezier(0.16, 1, 0.3, 1) infinite; }}
      .mfl1 {{ opacity: 0; animation: mFlash1 8.5s linear infinite; }}
      .mfl2 {{ opacity: 0; animation: mFlash2 8.5s linear infinite; }}
      .mp1 {{ opacity: 0; animation: mPetalA 8.5s ease-out infinite; }}
      .mp2 {{ opacity: 0; animation: mPetalB 8.5s ease-out infinite; }}
      .mp3 {{ opacity: 0; animation: mPetalA 8.5s ease-out -0.4s infinite; }}
    </style>
  </defs>

  <rect x="0.5" y="0.5" width="847" height="211" rx="2" fill="{t['card_bg']}" stroke="{t['border']}"/>
  <text x="16" y="23" fill="{t['text']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12" font-weight="600">contributions</text>
  <text x="122" y="23" fill="{t['label']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.06em">{total} IN THE LAST YEAR</text>
  <text x="832" y="23" text-anchor="end" fill="{t['muted']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.06em">RAIN · CLEAVE · PETALS</text>
  <line x1="1" y1="36.5" x2="847" y2="36.5" stroke="{t['border']}"/>

  <text x="16" y="{Y0 + 1 * PITCH + 9}" fill="{t['label']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9">Mon</text>
  <text x="16" y="{Y0 + 3 * PITCH + 9}" fill="{t['label']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9">Wed</text>
  <text x="16" y="{Y0 + 5 * PITCH + 9}" fill="{t['label']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9">Fri</text>
  {month_txt}

  <g clip-path="url(#m1-clip)" shape-rendering="crispEdges">
    {"".join(base_cells)}
    {"".join(active_cells)}
    {rain_svg}
    {"".join(ripples)}
    {"".join(flash_rects)}
    <g class="ms1">{cut_mid}</g>
    <g class="ms2a">{cut_xa}</g>
    <g class="ms2b">{cut_xb}</g>
    <g class="mp1">
      <rect x="{petal_x}" y="94" width="6" height="3" fill="#fef3c7"/>
      <rect x="{petal_x + 3}" y="97" width="3" height="3" fill="#fde68a"/>
    </g>
    <g class="mp2">
      <rect x="{petal_x - 20}" y="114" width="6" height="3" fill="#ffffff"/>
      <rect x="{petal_x - 23}" y="117" width="3" height="3" fill="#fef3c7"/>
    </g>
    <g class="mp3">
      <rect x="{petal_x + 18}" y="82" width="3" height="3" fill="#ffffff"/>
      <rect x="{petal_x + 21}" y="85" width="6" height="3" fill="#fef3c7"/>
    </g>
  </g>

  <line x1="1" y1="173.5" x2="847" y2="173.5" stroke="{t['border']}"/>
  <text x="16" y="191" fill="{t['label']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10">{breakdown}</text>
  <text x="716" y="191" fill="{t['label']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9.5">LESS</text>
  {legend}
  <text x="822" y="191" fill="{t['label']}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="9.5">MORE</text>
</svg>
"""
    (ASSETS / f"contributions-{theme_name}.svg").write_text(svg, encoding="utf-8")


def main() -> int:
    username = os.environ.get("GITHUB_USERNAME", "a-ldnstntng")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN is required to fetch GitHub GraphQL contribution data.", file=sys.stderr)
        return 1

    user_data = fetch_github_data(username, token)
    repo_count = int(user_data["repositories"]["totalCount"])
    total_contribs = int(user_data["contributionsCollection"]["contributionCalendar"]["totalContributions"])

    update_hero_counts(repo_count, total_contribs)
    render_contributions_svg("dark", user_data)
    render_contributions_svg("light", user_data)
    print(f"Updated profile SVGs for {username}: {repo_count} repos, {total_contribs} contributions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
