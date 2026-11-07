#!/usr/bin/env python3
"""
Generate a 3D isometric GitHub contribution graph matching the 0xraiven cyberpunk/wine theme.
"""
import os
import json
import urllib.request
import datetime
import math

USERNAME = os.environ.get("GH_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "0xraiven"
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "assets/contribution-3d.svg")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# 0xraiven Theme Palette
THEME = {
    "card_bg_start": "#0E0D12",
    "card_bg_mid": "#111016",
    "card_bg_end": "#0E0D12",
    "card_border": "#292329",
    "wine_glow": "#B8325A",
    "wine_primary": "#8B1E3F",
    "wine_deep": "#5C1029",
    "wine_bright": "#FF5C8D",
    "panel_bg": "#14131A",
    "panel_border": "#26212D",
    "text_main": "#E8E6E8",
    "text_muted": "#8E8A90",
    "text_dim": "#57525C",
    "cubes": [
        # 0: empty
        {"top": "#16151D", "left": "#131218", "right": "#0F0E14", "stroke": "#221D27"},
        # 1: 1-2 contributions
        {"top": "#5C1029", "left": "#440B1D", "right": "#300714", "stroke": "#701633"},
        # 2: 3-5 contributions
        {"top": "#8B1E3F", "left": "#6E1631", "right": "#500F23", "stroke": "#A8244B"},
        # 3: 6-9 contributions
        {"top": "#B8325A", "left": "#942647", "right": "#6E1833", "stroke": "#D63C6B"},
        # 4: 10+ contributions
        {"top": "#FF5C8D", "left": "#D9366B", "right": "#A6224D", "stroke": "#FF80A8"},
    ]
}

def fetch_contributions_graphql(token, username):
    url = "https://api.github.com/graphql"
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                weekday
              }
            }
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        url,
        data=json.dumps({"query": query, "variables": {"user": username}}).encode("utf-8"),
        headers={
            "Authorization": f"bearer {token}",
            "User-Agent": "0xraiven-Contribution-Builder",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        return cal

def generate_sample_data():
    """Generates realistic baseline contribution data for 53 weeks."""
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=364)
    weeks = []
    curr = start_date
    total = 0
    
    # Deterministic pattern resembling active developer
    day_idx = 0
    for w in range(53):
        days = []
        for d in range(7):
            date_str = curr.strftime("%Y-%m-%d")
            # Create natural commit patterns
            val = int(abs(math.sin(day_idx * 0.17) * 4 + math.cos(day_idx * 0.31) * 3))
            if d in (0, 6): # weekend
                val = max(0, val - 2)
            if (day_idx % 19 == 0): # occasional busy sprint
                val += 6
            if (day_idx % 29 == 0): # quiet period
                val = 0
                
            total += val
            days.append({
                "date": date_str,
                "contributionCount": val,
                "weekday": d
            })
            curr += datetime.timedelta(days=1)
            day_idx += 1
        weeks.append({"contributionDays": days})
        
    return {
        "totalContributions": total,
        "weeks": weeks
    }

def calculate_stats(calendar):
    total = calendar.get("totalContributions", 0)
    weeks = calendar.get("weeks", [])
    
    all_days = []
    for w in weeks:
        for d in w["contributionDays"]:
            all_days.append(d)
            
    # This week
    this_week_count = sum(d["contributionCount"] for d in weeks[-1]["contributionDays"])
    start_this_week = datetime.datetime.strptime(weeks[-1]["contributionDays"][0]["date"], "%Y-%m-%d").strftime("%b %d")
    end_this_week = datetime.datetime.strptime(weeks[-1]["contributionDays"][-1]["date"], "%Y-%m-%d").strftime("%b %d")

    # Overall start and end
    start_all = datetime.datetime.strptime(all_days[0]["date"], "%Y-%m-%d").strftime("%b %d")
    end_all = datetime.datetime.strptime(all_days[-1]["date"], "%Y-%m-%d").strftime("%b %d")

    # Best day
    best_day_count = 0
    best_day_date = ""
    for d in all_days:
        if d["contributionCount"] > best_day_count:
            best_day_count = d["contributionCount"]
            best_day_date = datetime.datetime.strptime(d["date"], "%Y-%m-%d").strftime("%b %d")

    # Average
    avg = total / max(1, len(all_days))

    # Streaks
    current_streak = 0
    longest_streak = 0
    current_streak_start = None
    longest_streak_start = None
    longest_streak_end = None
    
    streak = 0
    s_start = None
    
    for d in all_days:
        if d["contributionCount"] > 0:
            if streak == 0:
                s_start = d["date"]
            streak += 1
            if streak > longest_streak:
                longest_streak = streak
                longest_streak_start = s_start
                longest_streak_end = d["date"]
        else:
            streak = 0
            s_start = None
            
    # Calculate current streak from the end backwards
    rev_days = list(reversed(all_days))
    # skip trailing zeros if today has no commits yet
    idx = 0
    while idx < len(rev_days) and rev_days[idx]["contributionCount"] == 0 and idx < 2:
        idx += 1
        
    c_start = None
    c_end = None
    while idx < len(rev_days) and rev_days[idx]["contributionCount"] > 0:
        if c_end is None:
            c_end = rev_days[idx]["date"]
        c_start = rev_days[idx]["date"]
        current_streak += 1
        idx += 1
        
    # Format streak strings
    if longest_streak_start and longest_streak_end:
        l_s = datetime.datetime.strptime(longest_streak_start, "%Y-%m-%d").strftime("%b %d")
        l_e = datetime.datetime.strptime(longest_streak_end, "%Y-%m-%d").strftime("%b %d")
        longest_range = f"{l_s} \u2192 {l_e}"
    else:
        longest_range = "--"
        
    if c_start and c_end:
        c_s = datetime.datetime.strptime(c_start, "%Y-%m-%d").strftime("%b %d")
        c_e = datetime.datetime.strptime(c_end, "%Y-%m-%d").strftime("%b %d")
        curr_range = f"{c_s} \u2192 {c_e}"
    else:
        curr_range = "--"

    return {
        "total": total,
        "total_range": f"{start_all} \u2192 {end_all}",
        "this_week": this_week_count,
        "this_week_range": f"{start_this_week} \u2192 {end_this_week}",
        "best_day": best_day_count,
        "best_day_date": best_day_date or "--",
        "average": avg,
        "longest_streak": longest_streak,
        "longest_range": longest_range,
        "current_streak": current_streak,
        "curr_range": curr_range,
    }

def render_svg(calendar, stats):
    weeks = calendar.get("weeks", [])
    
    # Dimensions
    svg_w = 900
    svg_h = 470
    
    # Isometric grid constants
    origin_x = 158
    origin_y = 126
    dx_w = 11.2
    dy_w = 5.6
    dx_d = 11.2
    dy_d = 5.6
    
    cubes_svg = []
    
    # Painter's algorithm: draw from back to front
    for w_idx, week in enumerate(weeks):
        for d_idx, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]
            
            # Level and height
            if count == 0:
                level = 0
                h = 4
            elif count <= 2:
                level = 1
                h = 10
            elif count <= 5:
                level = 2
                h = 18
            elif count <= 9:
                level = 3
                h = 28
            else:
                level = 4
                h = min(48, 28 + (count - 9) * 2.5)
                
            colors = THEME["cubes"][level]
            
            # Calculate coordinates
            # Base rhombus top vertex
            bx = origin_x + w_idx * dx_w - d_idx * dx_d
            by = origin_y + w_idx * dy_w + d_idx * dy_d
            
            # Elevated top face vertices
            T = (bx, by - h)
            R = (bx + dx_w, by + dy_w - h)
            B = (bx + dx_w - dx_d, by + dy_w + dy_d - h)
            L = (bx - dx_d, by + dy_d - h)
            
            # Base bottom face vertices
            B_base = (bx + dx_w - dx_d, by + dy_w + dy_d)
            L_base = (bx - dx_d, by + dy_d)
            R_base = (bx + dx_w, by + dy_w)
            
            # Build SVG paths
            cube_group = []
            
            # Left Face (facing SW)
            cube_group.append(
                f'<polygon points="{L[0]:.1f},{L[1]:.1f} {B[0]:.1f},{B[1]:.1f} {B_base[0]:.1f},{B_base[1]:.1f} {L_base[0]:.1f},{L_base[1]:.1f}" '
                f'fill="{colors["left"]}" stroke="{colors["stroke"]}" stroke-width="0.4"/>'
            )
            # Right Face (facing SE)
            cube_group.append(
                f'<polygon points="{R[0]:.1f},{R[1]:.1f} {B[0]:.1f},{B[1]:.1f} {B_base[0]:.1f},{B_base[1]:.1f} {R_base[0]:.1f},{R_base[1]:.1f}" '
                f'fill="{colors["right"]}" stroke="{colors["stroke"]}" stroke-width="0.4"/>'
            )
            # Top Face (rhombus)
            cube_group.append(
                f'<polygon points="{T[0]:.1f},{T[1]:.1f} {R[0]:.1f},{R[1]:.1f} {B[0]:.1f},{B[1]:.1f} {L[0]:.1f},{L[1]:.1f}" '
                f'fill="{colors["top"]}" stroke="{colors["stroke"]}" stroke-width="0.5"/>'
            )
            
            cubes_svg.append("".join(cube_group))
            
    cubes_markup = "\n    ".join(cubes_svg)
    
    total_fmt = f"{stats['total']:,}"
    avg_fmt = f"{stats['average']:.2f}"
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}" fill="none" role="img" aria-label="{USERNAME} — 3D Isometric Contribution Graph">
  <title>{USERNAME} — 3D Isometric Contribution Graph</title>
  <defs>
    <!-- Card Gradient -->
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{THEME['card_bg_start']}"/>
      <stop offset="50%" stop-color="{THEME['card_bg_mid']}"/>
      <stop offset="100%" stop-color="{THEME['card_bg_end']}"/>
    </linearGradient>

    <!-- Deep Wine Glow -->
    <radialGradient id="wineAura" cx="35%" cy="50%" r="55%">
      <stop offset="0%" stop-color="{THEME['wine_glow']}" stop-opacity="0.16"/>
      <stop offset="50%" stop-color="{THEME['wine_primary']}" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="{THEME['card_bg_start']}" stop-opacity="0"/>
    </radialGradient>

    <!-- Overlay Panel Gradient -->
    <linearGradient id="panelBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#15141D"/>
      <stop offset="100%" stop-color="#0E0D13"/>
    </linearGradient>

    <!-- Wine Glow Filter -->
    <filter id="accentGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <style>
      .mono-title {{
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.5px;
        fill: {THEME['text_main']};
      }}
      .card-header {{
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        fill: {THEME['wine_glow']};
      }}
      .metric-val {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 24px;
        font-weight: 800;
        fill: {THEME['text_main']};
      }}
      .metric-val-wine {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 24px;
        font-weight: 800;
        fill: {THEME['wine_glow']};
      }}
      .metric-lbl {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 11px;
        font-weight: 600;
        fill: {THEME['text_main']};
      }}
      .metric-sub {{
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 9.5px;
        fill: {THEME['text_muted']};
      }}
      .avg-text {{
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 11px;
        fill: {THEME['text_muted']};
      }}
      .toggle-box {{
        fill: #16151D;
        stroke: {THEME['panel_border']};
        stroke-width: 1;
        rx: 5px;
      }}
      .toggle-text {{
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 11px;
        font-weight: 700;
      }}
    </style>
  </defs>

  <!-- Container Base -->
  <rect x="1" y="1" width="{svg_w - 2}" height="{svg_h - 2}" rx="8" fill="url(#cardBg)" stroke="{THEME['card_border']}" stroke-width="1"/>
  <rect x="1" y="1" width="{svg_w - 2}" height="{svg_h - 2}" rx="8" fill="url(#wineAura)"/>

  <!-- Top Header Bar -->
  <g transform="translate(0, 0)">
    <!-- Terminal Status Dots -->
    <circle cx="26" cy="25" r="3.5" fill="{THEME['wine_glow']}" filter="url(#accentGlow)"/>
    <circle cx="38" cy="25" r="3.5" fill="{THEME['wine_primary']}"/>
    <circle cx="50" cy="25" r="3.5" fill="{THEME['card_border']}"/>

    <!-- Main Title -->
    <text x="68" y="29" class="mono-title">
      {total_fmt} contributions in the last year
    </text>

    <!-- Top Right 2D | 3D Pill Toggle -->
    <g transform="translate(814, 13)">
      <rect width="66" height="24" rx="4" class="toggle-box"/>
      <text x="33" y="16" text-anchor="middle" class="toggle-text">
        <tspan fill="{THEME['text_dim']}">2D</tspan> <tspan fill="{THEME['text_dim']}">|</tspan> <tspan fill="{THEME['wine_glow']}">3D</tspan>
      </text>
    </g>

    <!-- Header Divider Line -->
    <line x1="16" y1="46" x2="{svg_w - 16}" y2="46" stroke="#211C24" stroke-width="1"/>
  </g>

  <!-- ==================== 3D ISOMETRIC CONTRIBUTION GRAPH ==================== -->
  <g id="isometric-grid">
    {cubes_markup}
  </g>

  <!-- ==================== TOP-RIGHT: CONTRIBUTIONS CARD ==================== -->
  <g transform="translate(534, 60)">
    <!-- Panel Box -->
    <rect width="346" height="120" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <!-- Header -->
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">CONTRIBUTIONS</text>

    <!-- Metric Columns -->
    <!-- Col 1: Total -->
    <g transform="translate(24, 40)">
      <text x="0" y="22" class="metric-val">{total_fmt}</text>
      <text x="0" y="38" class="metric-lbl">Total</text>
      <text x="0" y="52" class="metric-sub">{stats['total_range']}</text>
    </g>

    <!-- Col 2: This week -->
    <g transform="translate(132, 40)">
      <text x="0" y="22" class="metric-val">{stats['this_week']}</text>
      <text x="0" y="38" class="metric-lbl">This week</text>
      <text x="0" y="52" class="metric-sub">{stats['this_week_range']}</text>
    </g>

    <!-- Col 3: Best day -->
    <g transform="translate(236, 40)">
      <text x="0" y="22" class="metric-val">{stats['best_day']}</text>
      <text x="0" y="38" class="metric-lbl">Best day</text>
      <text x="0" y="52" class="metric-sub">{stats['best_day_date']}</text>
    </g>

    <!-- Average subline -->
    <text x="346" y="136" text-anchor="end" class="avg-text">
      Average: <tspan fill="{THEME['wine_glow']}" font-weight="700">{avg_fmt}</tspan> / day
    </text>
  </g>

  <!-- ==================== BOTTOM-LEFT: STREAKS CARD ==================== -->
  <g transform="translate(24, 342)">
    <!-- Panel Box -->
    <rect width="250" height="98" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <!-- Header -->
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">STREAKS</text>

    <!-- Col 1: Longest -->
    <g transform="translate(20, 38)">
      <text x="0" y="20" class="metric-val-wine">{stats['longest_streak']} <tspan fill="{THEME['text_main']}" font-size="14" font-weight="600">days</tspan></text>
      <text x="0" y="34" class="metric-lbl">Longest</text>
      <text x="0" y="47" class="metric-sub">{stats['longest_range']}</text>
    </g>

    <!-- Col 2: Current -->
    <g transform="translate(132, 38)">
      <text x="0" y="20" class="metric-val-wine">{stats['current_streak']} <tspan fill="{THEME['text_main']}" font-size="14" font-weight="600">days</tspan></text>
      <text x="0" y="34" class="metric-lbl">Current</text>
      <text x="0" y="47" class="metric-sub">{stats['curr_range']}</text>
    </g>
  </g>
</svg>"""
    return svg

def main():
    cal = None
    if GITHUB_TOKEN:
        try:
            print("Fetching live GitHub contributions via GraphQL...")
            cal = fetch_contributions_graphql(GITHUB_TOKEN, USERNAME)
            print("Successfully fetched live contributions!")
        except Exception as e:
            print(f"GraphQL fetch failed: {e}. Falling back to baseline data.")
            
    if not cal:
        cal = generate_sample_data()
        
    stats = calculate_stats(cal)
    svg_content = render_svg(cal, stats)
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated 3D contribution graph SVG at {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
