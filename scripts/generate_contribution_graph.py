#!/usr/bin/env python3
"""
Generate a 3D isometric GitHub contribution graph matching the 0xraiven cyberpunk/wine theme.
Integrates live GitHub developer stats (commits, PRs, issues, contributed repos) and developer rank grade,
excluding total stars earned.
"""
import os
import sys
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

def exp_cdf(x, median):
    return 1 - (2 ** (-(max(0, x) / max(1, median))))

def calculate_rank(commits, prs, issues, repos):
    """
    Computes global developer rank (S, A+, A, A-, B+, etc.) using CDF distributions,
    specifically excluding total stars earned, weighted fairly for systems/tooling engineers.
    """
    c_score = exp_cdf(commits, 200)
    p_score = exp_cdf(prs, 10)
    i_score = exp_cdf(issues, 8)
    r_score = exp_cdf(repos, 3)

    score = (5.0 * c_score + 2.0 * r_score + 2.0 * p_score + 1.0 * i_score) / 10.0
    percentile = (1.0 - score) * 100

    if percentile <= 5.0:
        rank = "S"
    elif percentile <= 15.0:
        rank = "A+"
    elif percentile <= 28.0:
        rank = "A"
    elif percentile <= 42.0:
        rank = "A-"
    elif percentile <= 58.0:
        rank = "B+"
    elif percentile <= 72.0:
        rank = "B"
    elif percentile <= 85.0:
        rank = "B-"
    else:
        rank = "C"

    return rank, score, percentile

def fetch_github_data(token, username):
    headers = {
        "Authorization": f"bearer {token}",
        "User-Agent": "0xraiven-Contribution-Builder",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json"
    }

    query = f"""
    query {{
      user(login: "{username}") {{
        contributionsCollection {{
          totalCommitContributions
          restrictedContributionsCount
          totalPullRequestContributions
          totalIssueContributions
          totalRepositoryContributions
          totalPullRequestReviewContributions
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                date
                contributionCount
                weekday
              }}
            }}
          }}
        }}
        repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {{
          totalCount
        }}
        repositories(ownerAffiliations: OWNER) {{
          totalCount
        }}
      }}
      prs: search(query: "type:pr author:{username}", type: ISSUE) {{
        issueCount
      }}
      issues: search(query: "type:issue author:{username}", type: ISSUE) {{
        issueCount
      }}
    }}
    """
    url = "https://api.github.com/graphql"
    req = urllib.request.Request(url, data=json.dumps({"query": query}).encode("utf-8"), headers=headers)
    
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    u = data.get("data", {}).get("user", {})
    cc = u.get("contributionsCollection", {})
    cal = cc.get("contributionCalendar", {})

    cal_total = cal.get("totalContributions", 0)
    commit_contributions = cc.get("totalCommitContributions", 0) + cc.get("restrictedContributionsCount", 0)

    # Fetch all-time commits count via search API
    all_time_commits = 0
    try:
        search_commit_url = f"https://api.github.com/search/commits?q=author:{username}"
        req_commits = urllib.request.Request(
            search_commit_url,
            headers={**headers, "Accept": "application/vnd.github.cloak-preview+json"}
        )
        with urllib.request.urlopen(req_commits, timeout=10) as c_resp:
            c_data = json.loads(c_resp.read().decode("utf-8"))
            all_time_commits = c_data.get("total_count", 0)
    except Exception as e:
        print(f"Commit search fallback: {e}")

    commits = max(all_time_commits, commit_contributions, cal_total)

    # Pull requests (search + collection)
    search_prs = data.get("data", {}).get("prs", {}).get("issueCount", 0)
    contrib_prs = cc.get("totalPullRequestContributions", 0)
    prs = max(search_prs, contrib_prs)

    # Issues (search + collection)
    search_issues = data.get("data", {}).get("issues", {}).get("issueCount", 0)
    contrib_issues = cc.get("totalIssueContributions", 0)
    issues = max(search_issues, contrib_issues)

    # Repositories
    repos_contrib = u.get("repositoriesContributedTo", {}).get("totalCount", 0)
    repos_owned = u.get("repositories", {}).get("totalCount", 0)
    contrib_repos = cc.get("totalRepositoryContributions", 0)
    repos = max(repos_contrib, repos_owned, contrib_repos)

    reviews = cc.get("totalPullRequestReviewContributions", 0)

    return {
        "calendar": cal,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "repos": repos,
        "reviews": reviews
    }

def calculate_stats(calendar, raw_metrics):
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

    # Overall start and end: formatted as Month Year -> Month Year (e.g. Nov 2025 -> Nov 2026)
    start_dt = datetime.datetime.strptime(all_days[0]["date"], "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(all_days[-1]["date"], "%Y-%m-%d")
    total_range = f"{start_dt.strftime('%b %Y')} \u2192 {end_dt.strftime('%b %Y')}"

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

    rev_days = list(reversed(all_days))
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

    commits = raw_metrics.get("commits") or total
    prs = raw_metrics.get("prs", 0)
    issues = raw_metrics.get("issues", 0)
    repos = raw_metrics.get("repos", 0)
    reviews = raw_metrics.get("reviews", 0)

    rank, score, pct = calculate_rank(commits, prs, issues, repos)

    return {
        "total": total,
        "total_range": total_range,
        "this_week": this_week_count,
        "this_week_range": f"{start_this_week} \u2192 {end_this_week}",
        "best_day": best_day_count,
        "best_day_date": best_day_date or "--",
        "average": avg,
        "longest_streak": longest_streak,
        "longest_range": longest_range,
        "current_streak": current_streak,
        "curr_range": curr_range,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "repos": repos,
        "rank": rank,
        "rank_score": score,
        "rank_pct": pct,
    }

def render_svg(calendar, stats):
    weeks = calendar.get("weeks", [])

    svg_w = 900
    svg_h = 556

    origin_x = 158
    origin_y = 126
    dx_w = 11.2
    dy_w = 5.6
    dx_d = 11.2
    dy_d = 5.6

    cubes_svg = []

    for w_idx, week in enumerate(weeks):
        for d_idx, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]

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

            bx = origin_x + w_idx * dx_w - d_idx * dx_d
            by = origin_y + w_idx * dy_w + d_idx * dy_d

            T = (bx, by - h)
            R = (bx + dx_w, by + dy_w - h)
            B = (bx + dx_w - dx_d, by + dy_w + dy_d - h)
            L = (bx - dx_d, by + dy_d - h)

            B_base = (bx + dx_w - dx_d, by + dy_w + dy_d)
            L_base = (bx - dx_d, by + dy_d)
            R_base = (bx + dx_w, by + dy_w)

            cube_group = [
                f'<polygon points="{L[0]:.1f},{L[1]:.1f} {B[0]:.1f},{B[1]:.1f} {B_base[0]:.1f},{B_base[1]:.1f} {L_base[0]:.1f},{L_base[1]:.1f}" '
                f'fill="{colors["left"]}" stroke="{colors["stroke"]}" stroke-width="0.4"/>',
                f'<polygon points="{R[0]:.1f},{R[1]:.1f} {B[0]:.1f},{B[1]:.1f} {B_base[0]:.1f},{B_base[1]:.1f} {R_base[0]:.1f},{R_base[1]:.1f}" '
                f'fill="{colors["right"]}" stroke="{colors["stroke"]}" stroke-width="0.4"/>',
                f'<polygon points="{T[0]:.1f},{T[1]:.1f} {R[0]:.1f},{R[1]:.1f} {B[0]:.1f},{B[1]:.1f} {L[0]:.1f},{L[1]:.1f}" '
                f'fill="{colors["top"]}" stroke="{colors["stroke"]}" stroke-width="0.5"/>'
            ]
            cubes_svg.append("".join(cube_group))

    cubes_markup = "\n    ".join(cubes_svg)

    total_fmt = f"{stats['total']:,}"
    avg_fmt = f"{stats['average']:.2f}"
    commits_fmt = f"{stats['commits']:,}"
    prs_fmt = f"{stats['prs']:,}"
    issues_fmt = f"{stats['issues']:,}"
    repos_fmt = f"{stats['repos']:,}"

    # Rank Gauge Calculation
    circ_r = 25
    circumference = 2 * math.pi * circ_r
    score_clamped = min(1.0, max(0.08, stats["rank_score"]))
    dash_offset = circumference * (1.0 - score_clamped)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}" fill="none" role="img" aria-label="{USERNAME} — 3D Isometric Contribution Graph &amp; Developer Metrics">
  <title>{USERNAME} — 3D Isometric Contribution Graph &amp; Developer Metrics</title>
  <defs>
    <!-- Card Gradient -->
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{THEME['card_bg_start']}"/>
      <stop offset="50%" stop-color="{THEME['card_bg_mid']}"/>
      <stop offset="100%" stop-color="{THEME['card_bg_end']}"/>
    </linearGradient>

    <!-- Deep Wine Glow -->
    <radialGradient id="wineAura" cx="35%" cy="45%" r="55%">
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
        font-size: 10.5px;
        font-weight: 700;
        letter-spacing: 1.2px;
        fill: {THEME['wine_glow']};
      }}
      .metric-val {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 24px;
        font-weight: 800;
        fill: {THEME['text_main']};
      }}
      .metric-val-sm {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 20px;
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
      .metric-tag {{
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 9.5px;
        font-weight: 700;
        letter-spacing: 0.8px;
        fill: {THEME['wine_glow']};
      }}
      .metric-sub {{
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 9px;
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
  <g transform="translate(534, 58)">
    <rect width="346" height="114" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">CONTRIBUTIONS</text>

    <!-- Col 1: Total -->
    <g transform="translate(24, 38)">
      <text x="0" y="20" class="metric-val">{total_fmt}</text>
      <text x="0" y="34" class="metric-lbl">Total</text>
      <text x="0" y="47" class="metric-sub">{stats['total_range']}</text>
    </g>

    <!-- Col 2: This week -->
    <g transform="translate(132, 38)">
      <text x="0" y="20" class="metric-val">{stats['this_week']}</text>
      <text x="0" y="34" class="metric-lbl">This week</text>
      <text x="0" y="47" class="metric-sub">{stats['this_week_range']}</text>
    </g>

    <!-- Col 3: Best day -->
    <g transform="translate(236, 38)">
      <text x="0" y="20" class="metric-val">{stats['best_day']}</text>
      <text x="0" y="34" class="metric-lbl">Best day</text>
      <text x="0" y="47" class="metric-sub">{stats['best_day_date']}</text>
    </g>

    <text x="346" y="130" text-anchor="end" class="avg-text">
      Average: <tspan fill="{THEME['wine_glow']}" font-weight="700">{avg_fmt}</tspan> / day
    </text>
  </g>

  <!-- ==================== BOTTOM-LEFT: STREAKS CARD ==================== -->
  <g transform="translate(24, 332)">
    <rect width="250" height="96" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">STREAKS</text>

    <!-- Col 1: Longest -->
    <g transform="translate(20, 36)">
      <text x="0" y="20" class="metric-val-wine">{stats['longest_streak']} <tspan fill="{THEME['text_main']}" font-size="13" font-weight="600">days</tspan></text>
      <text x="0" y="34" class="metric-lbl">Longest</text>
      <text x="0" y="46" class="metric-sub">{stats['longest_range']}</text>
    </g>

    <!-- Col 2: Current -->
    <g transform="translate(132, 36)">
      <text x="0" y="20" class="metric-val-wine">{stats['current_streak']} <tspan fill="{THEME['text_main']}" font-size="13" font-weight="600">days</tspan></text>
      <text x="0" y="34" class="metric-lbl">Current</text>
      <text x="0" y="46" class="metric-sub">{stats['curr_range']}</text>
    </g>
  </g>

  <!-- ==================== BOTTOM BAR: DEVELOPER STATS & RANK ==================== -->
  <g transform="translate(24, 444)">
    <rect width="852" height="94" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>

    <!-- Section 1: Rank Badge -->
    <g transform="translate(20, 16)">
      <!-- Outer Track Circle -->
      <circle cx="31" cy="31" r="{circ_r}" fill="none" stroke="#221D27" stroke-width="3.5"/>
      <!-- Glowing Progress Arc -->
      <circle cx="31" cy="31" r="{circ_r}" fill="none" stroke="{THEME['wine_glow']}" stroke-width="3.5"
              stroke-linecap="round" stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{dash_offset:.1f}"
              transform="rotate(-90 31 31)" filter="url(#accentGlow)"/>
      <!-- Rank Letter Grade -->
      <text x="31" y="38" text-anchor="middle" font-family="'SFMono-Regular', Consolas, monospace" font-size="20" font-weight="900" fill="{THEME['text_main']}">{stats['rank']}</text>
      
      <!-- Rank Meta Label -->
      <g transform="translate(70, 14)">
        <text x="0" y="10" class="metric-tag">DEVELOPER RANK</text>
        <text x="0" y="24" class="metric-sub">Percentile Grade</text>
        <text x="0" y="38" font-family="'SFMono-Regular', Consolas, monospace" font-size="11" font-weight="700" fill="{THEME['text_main']}">Tier: <tspan fill="{THEME['wine_glow']}">{stats['rank']}</tspan></text>
      </g>
    </g>

    <!-- Divider 1 -->
    <line x1="210" y1="18" x2="210" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 2: Total Commits -->
    <g transform="translate(230, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">TOTAL COMMITS</text>
      <text x="12" y="33" class="metric-val-sm">{commits_fmt}</text>
      <text x="12" y="47" class="metric-sub">Code activity</text>
    </g>

    <!-- Divider 2 -->
    <line x1="376" y1="18" x2="376" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 3: Pull Requests -->
    <g transform="translate(396, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">PULL REQUESTS</text>
      <text x="12" y="33" class="metric-val-sm">{prs_fmt}</text>
      <text x="12" y="47" class="metric-sub">Merged &amp; authored</text>
    </g>

    <!-- Divider 3 -->
    <line x1="538" y1="18" x2="538" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 4: Total Issues -->
    <g transform="translate(558, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">CODE ISSUES</text>
      <text x="12" y="33" class="metric-val-sm">{issues_fmt}</text>
      <text x="12" y="47" class="metric-sub">Reported &amp; tracked</text>
    </g>

    <!-- Divider 4 -->
    <line x1="696" y1="18" x2="696" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 5: Contributed To -->
    <g transform="translate(716, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">CONTRIBUTED TO</text>
      <text x="12" y="33" class="metric-val-sm">{repos_fmt} <tspan font-size="12" font-weight="600" fill="{THEME['text_muted']}">repos</tspan></text>
      <text x="12" y="47" class="metric-sub">Open-source impact</text>
    </g>
  </g>
</svg>"""
    return svg

def main():
    if not GITHUB_TOKEN:
        sys.exit("Error: GITHUB_TOKEN environment variable is required to fetch real GitHub data.")

    print(f"Fetching live GitHub contributions & metrics for {USERNAME} via GraphQL...")
    raw_data = fetch_github_data(GITHUB_TOKEN, USERNAME)
    print("Successfully fetched live GitHub data!")

    cal = raw_data["calendar"]
    stats = calculate_stats(cal, raw_data)
    svg_content = render_svg(cal, stats)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated 3D contribution graph with live Developer Stats & Rank at {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
