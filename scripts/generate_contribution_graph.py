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
import re

USERNAME = os.environ.get("GH_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "0xraiven"
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "assets/contribution-3d.svg")
HERO_PATH = os.environ.get("HERO_PATH", "assets/hero-card.svg")
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
    svg_h = 570

    origin_x = 158
    origin_y = 108
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
      .claude-serif {{
        font-family: 'Copernicus', 'Tiempos Text', 'Charter', 'Iowan Old Style', Georgia, 'Times New Roman', serif;
      }}
      .claude-sans {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      }}
      .heading-title {{
        font-family: 'Copernicus', 'Tiempos Text', 'Charter', 'Iowan Old Style', Georgia, 'Times New Roman', serif;
        font-size: 18px;
        font-weight: 600;
        fill: {THEME['text_main']};
      }}
      .heading-sub {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 12px;
        font-weight: 500;
        fill: {THEME['text_muted']};
      }}
      .card-header {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.4px;
        fill: {THEME['wine_glow']};
      }}
      .metric-val {{
        font-family: 'Copernicus', 'Tiempos Text', 'Charter', 'Iowan Old Style', Georgia, 'Times New Roman', serif;
        font-size: 24px;
        font-weight: 700;
        fill: {THEME['text_main']};
      }}
      .metric-val-sm {{
        font-family: 'Copernicus', 'Tiempos Text', 'Charter', 'Iowan Old Style', Georgia, 'Times New Roman', serif;
        font-size: 21px;
        font-weight: 700;
        fill: {THEME['text_main']};
      }}
      .metric-val-wine {{
        font-family: 'Copernicus', 'Tiempos Text', 'Charter', 'Iowan Old Style', Georgia, 'Times New Roman', serif;
        font-size: 24px;
        font-weight: 700;
        fill: {THEME['wine_glow']};
      }}
      .metric-lbl {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 11px;
        font-weight: 600;
        fill: {THEME['text_main']};
      }}
      .metric-tag {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 10.5px;
        font-weight: 600;
        letter-spacing: 0.3px;
        fill: {THEME['wine_glow']};
      }}
      .metric-sub {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 10px;
        fill: {THEME['text_muted']};
      }}
      .avg-text {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 11px;
        fill: {THEME['text_muted']};
      }}
    </style>
  </defs>

  <!-- Container Base -->
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="10" fill="url(#cardBg)"/>
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="10" fill="url(#wineAura)"/>

  <!-- Integrated Top-Left Title (no separate header bar) -->
  <g transform="translate(28, 28)">
    <text x="0" y="24" class="claude-serif" font-size="28" font-weight="700" fill="{THEME['text_main']}">Contribution Graph</text>
    <text x="0" y="45" class="claude-sans" font-size="12" fill="{THEME['text_muted']}">
      <tspan fill="{THEME['wine_glow']}" font-weight="600">{total_fmt}</tspan> contributions · {stats['total_range']}
    </text>
  </g>

  <!-- ==================== 3D ISOMETRIC CONTRIBUTION GRAPH ==================== -->
  <g id="isometric-grid">
    {cubes_markup}
  </g>

  <!-- ==================== TOP-RIGHT: CONTRIBUTIONS CARD ==================== -->
  <g transform="translate(502, 24)">
    <rect width="374" height="120" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">Contributions</text>

    <!-- Col 1: Total -->
    <g transform="translate(22, 40)">
      <text x="0" y="20" class="metric-val">{total_fmt}</text>
      <text x="0" y="37" class="metric-lbl">Total</text>
      <text x="0" y="52" class="metric-sub">{stats['total_range']}</text>
    </g>

    <!-- Col 2: This week -->
    <g transform="translate(160, 40)">
      <text x="0" y="20" class="metric-val">{stats['this_week']}</text>
      <text x="0" y="37" class="metric-lbl">This week</text>
      <text x="0" y="52" class="metric-sub">{stats['this_week_range']}</text>
    </g>

    <!-- Col 3: Best day -->
    <g transform="translate(284, 40)">
      <text x="0" y="20" class="metric-val">{stats['best_day']}</text>
      <text x="0" y="37" class="metric-lbl">Best day</text>
      <text x="0" y="52" class="metric-sub">{stats['best_day_date']}</text>
    </g>

    <text x="374" y="138" text-anchor="end" class="avg-text">
      Average: <tspan fill="{THEME['wine_glow']}" font-weight="700">{avg_fmt}</tspan> / day
    </text>
  </g>

  <!-- ==================== BOTTOM-LEFT: STREAKS CARD ==================== -->
  <g transform="translate(24, 346)">
    <rect width="264" height="100" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">Streaks</text>

    <!-- Col 1: Longest -->
    <g transform="translate(22, 38)">
      <text x="0" y="20" class="metric-val-wine">{stats['longest_streak']} <tspan class="claude-sans" fill="{THEME['text_main']}" font-size="12" font-weight="600">days</tspan></text>
      <text x="0" y="36" class="metric-lbl">Longest</text>
      <text x="0" y="50" class="metric-sub">{stats['longest_range']}</text>
    </g>

    <!-- Col 2: Current -->
    <g transform="translate(144, 38)">
      <text x="0" y="20" class="metric-val-wine">{stats['current_streak']} <tspan class="claude-sans" fill="{THEME['text_main']}" font-size="12" font-weight="600">days</tspan></text>
      <text x="0" y="36" class="metric-lbl">Current</text>
      <text x="0" y="50" class="metric-sub">{stats['curr_range']}</text>
    </g>
  </g>

  <!-- ==================== BOTTOM BAR: DEVELOPER STATS & RANK ==================== -->
  <g transform="translate(24, 458)">
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
      <text x="31" y="38" text-anchor="middle" class="claude-serif" font-size="21" font-weight="700" fill="{THEME['text_main']}">{stats['rank']}</text>
      
      <!-- Rank Meta Label -->
      <g transform="translate(70, 14)">
        <text x="0" y="10" class="metric-tag">Developer Rank</text>
        <text x="0" y="24" class="metric-sub">Percentile Grade</text>
        <text x="0" y="38" class="claude-sans" font-size="11" font-weight="600" fill="{THEME['text_main']}">Tier: <tspan fill="{THEME['wine_glow']}">{stats['rank']}</tspan></text>
      </g>
    </g>

    <!-- Divider 1 -->
    <line x1="210" y1="18" x2="210" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 2: Total Commits -->
    <g transform="translate(230, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Total Commits</text>
      <text x="12" y="33" class="metric-val-sm">{commits_fmt}</text>
      <text x="12" y="47" class="metric-sub">Code activity</text>
    </g>

    <!-- Divider 2 -->
    <line x1="376" y1="18" x2="376" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 3: Pull Requests -->
    <g transform="translate(396, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Pull Requests</text>
      <text x="12" y="33" class="metric-val-sm">{prs_fmt}</text>
      <text x="12" y="47" class="metric-sub">Merged &amp; authored</text>
    </g>

    <!-- Divider 3 -->
    <line x1="538" y1="18" x2="538" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 4: Total Issues -->
    <g transform="translate(558, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Code Issues</text>
      <text x="12" y="33" class="metric-val-sm">{issues_fmt}</text>
      <text x="12" y="47" class="metric-sub">Reported &amp; tracked</text>
    </g>

    <!-- Divider 4 -->
    <line x1="696" y1="18" x2="696" y2="76" stroke="#211C24" stroke-width="1"/>

    <!-- Section 5: Contributed To -->
    <g transform="translate(716, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Contributed To</text>
      <text x="12" y="33" class="metric-val-sm">{repos_fmt} <tspan class="claude-sans" font-size="12" font-weight="500" fill="{THEME['text_muted']}">repos</tspan></text>
      <text x="12" y="47" class="metric-sub">Open-source impact</text>
    </g>
  </g>
</svg>"""
    return svg

class _PixelCanvas:
    """2x2 pixel-grid buffer with horizontal run-length encoding for compact crispEdges SVG."""

    def __init__(self, size=2):
        self.size = size
        self.cells = {}

    def put(self, gx, gy, color):
        self.cells[(int(gx), int(gy))] = color

    def hline(self, gx0, gx1, gy, color):
        step = 1 if gx1 >= gx0 else -1
        for gx in range(int(gx0), int(gx1) + step, step):
            self.cells[(gx, int(gy))] = color

    def to_svg(self):
        if not self.cells:
            return ""
        rows = {}
        for (gx, gy), col in self.cells.items():
            rows.setdefault(gy, []).append((gx, col))
        out = []
        s = self.size
        for gy in sorted(rows):
            row = sorted(rows[gy], key=lambda item: item[0])
            run_x, run_col = row[0]
            run_len = 1
            for gx, col in row[1:]:
                if gx == run_x + run_len and col == run_col:
                    run_len += 1
                else:
                    out.append(f'<rect x="{run_x * s}" y="{gy * s}" width="{run_len * s}" height="{s}" fill="{run_col}"/>')
                    run_x, run_col, run_len = gx, col, 1
            out.append(f'<rect x="{run_x * s}" y="{gy * s}" width="{run_len * s}" height="{s}" fill="{run_col}"/>')
        return "\n    ".join(out)

def _px(x, y, color, cls="", size=2):
    c = f' class="{cls}"' if cls else ""
    return f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{color}"{c}/>'

def _read_existing_views(hero_path):
    """Preserve existing profile view count across daily contribution graph rebuilds."""
    for path in (hero_path, "assets/profile-views.svg"):
        try:
            if os.path.exists(path):
                content = open(path, "r", encoding="utf-8").read()
                m = re.search(r'id="profile-views-count"[^>]*>(.*?)</text>', content)
                if m:
                    digits = re.sub(r"<[^>]+>", "", m.group(1)).replace(",", "").strip()
                    if digits.isdigit() and 0 < int(digits) < 100_000_000:
                        return int(digits)
        except Exception:
            pass
    return 367

def render_hero_svg(stats, views_count):
    """Render 900x236 Hero Card SVG with a high-detail 2x2 pixel-art Wine-Blossom Bonsai & minimal inline view count."""
    commits = stats["commits"]
    this_week = stats["this_week"]
    streak = stats["current_streak"]
    best_day = stats["best_day"]
    repos = stats["repos"]
    rank = stats["rank"]

    if commits < 100:
        stage, stage_roman, next_target = 1, "I", 100
        sub_prog = commits / 100.0
    elif commits < 400:
        stage, stage_roman, next_target = 2, "II", 400
        sub_prog = (commits - 100) / 300.0
    elif commits < 800:
        stage, stage_roman, next_target = 3, "III", 800
        sub_prog = (commits - 400) / 400.0
    elif commits < 1500:
        stage, stage_roman, next_target = 4, "IV", 1500
        sub_prog = (commits - 800) / 700.0
    else:
        stage, stage_roman, next_target = 5, "V", None
        sub_prog = 1.0

    # 2x2 pixel grid: x = gx * 2, y = gy * 2
    # Stage canvas: gx 242..436 (x 484..872), gy 12..103 (y 24..206)
    base = _PixelCanvas(size=2)
    canopy = _PixelCanvas(size=2)
    lantern_fx = []

    # 1. Subtle night-sky dithered stars & crescent moon (A- and above)
    stars = [
        (248, 17, "#2A2230"), (272, 13, "#3D1624"), (304, 15, "#2A2230"),
        (378, 14, "#3D1624"), (258, 34, "#231B29"), (424, 42, "#2A2230"),
        (244, 48, "#2A2230"), (402, 58, "#231B29"), (292, 26, "#231B29"),
    ]
    for sx, sy, sc in stars:
        base.put(sx, sy, sc)

    if rank in ("A-", "A", "A+", "S"):
        # Delicate 2x2 pixel crescent moon at upper right (gx ~ 416, gy ~ 20)
        moon_pts = [
            (416, 15, "#4E4359"), (417, 15, "#6E5F7D"),
            (414, 16, "#5E516B"), (415, 16, "#8E8A90"),
            (413, 17, "#6E5F7D"), (414, 17, "#A8A2AC"),
            (413, 18, "#6E5F7D"), (414, 18, "#8E8A90"),
            (413, 19, "#6E5F7D"), (414, 19, "#A8A2AC"),
            (414, 20, "#5E516B"), (415, 20, "#8E8A90"),
            (416, 21, "#4E4359"), (417, 21, "#6E5F7D"),
        ]
        for mx, my, mc in moon_pts:
            base.put(mx, my, mc)

    # 2. Ground horizon table (gy = 102)
    for gx in range(244, 426):
        if gx % 3 != 0 or (295 <= gx <= 375):
            base.put(gx, 102, "#1C1722")
        if 302 <= gx <= 366:
            base.put(gx, 103, "#120F17")

    # 3. Carved Tokoname Ceramic Pot (centered gx=334, gy=89..101)
    # Rim lip with glazed specular highlight
    for gx in range(298, 371):
        col = "#9C254B" if 304 <= gx <= 324 else ("#7D1B3B" if gx < 354 else "#5C1029")
        base.put(gx, 89, col)
    base.hline(299, 369, 90, "#420B1D")
    # Pot body with recessed decorative panel & warm lantern reflection on right
    for gy in range(91, 99):
        for gx in range(301, 368):
            if 310 <= gx <= 358 and 92 <= gy <= 97:
                # Recessed carved panel
                if gy == 92 or gx == 310:
                    col = "#24050F"
                elif gy == 97 or gx == 358:
                    col = "#541026"
                else:
                    col = "#360817" if (gx + gy) % 4 else "#420B1D"
            else:
                col = "#5C1029" if gx >= 362 and gy <= 95 else ("#4A0D21" if gx < 312 else "#2D0713")
            base.put(gx, gy, col)
    base.hline(303, 365, 99, "#1A040B")
    # Kumo-ashi (cloud-shaped pot feet)
    for fx in (306, 307, 308, 359, 360, 361):
        base.put(fx, 100, "#360817")
    for fx in (307, 308, 359, 360):
        base.put(fx, 101, "#24050F")

    # 4. Mossy soil mound & creeping moss tufts (gy=85..88)
    for gx in range(302, 367):
        base.put(gx, 88, "#231B2A" if gx % 2 == 0 else "#1B1521")
    for gx in range(308, 361):
        base.put(gx, 87, "#2F2438" if (gx * 3) % 5 else "#4A182D")
    for gx in range(316, 352):
        base.put(gx, 86, "#392A42" if gx % 3 else "#5C1029")
    # Tiny moss & clover tufts on soil
    for mx in (305, 313, 349, 359, 363):
        base.put(mx, 87, "#5C1029")
        base.put(mx, 86, "#8B1E3F")
        if mx in (313, 359):
            base.put(mx + 1, 85, "#B8325A")

    # 5. Stone Toro Lantern on the right (gx=384..397, gy=84..101)
    if stage >= 3:
        # Pedestal & pillar
        base.hline(387, 394, 101, "#2A2330")
        base.hline(388, 393, 100, "#3D3445")
        for gy in range(93, 100):
            base.put(390, gy, "#4E4359")
            base.put(391, gy, "#342C3D")
        base.hline(387, 394, 92, "#4E4359")
        # Firebox housing
        for gy in (89, 90, 91):
            base.put(387, gy, "#3D3445")
            base.put(394, gy, "#2D2536")
        # Glowing wine flame (animated group)
        lantern_fx.extend([
            _px(388 * 2, 90 * 2, "#B8325A", "lantern-glow"),
            _px(389 * 2, 90 * 2, "#FF5C8D", "lantern-glow"),
            _px(390 * 2, 90 * 2, "#FFE0EA", "lantern-glow"),
            _px(391 * 2, 90 * 2, "#FF5C8D", "lantern-glow"),
            _px(392 * 2, 90 * 2, "#B8325A", "lantern-glow"),
            _px(393 * 2, 90 * 2, "#8B1E3F", "lantern-glow"),
            _px(390 * 2, 89 * 2, "#FFA3BF", "lantern-glow"),
            _px(391 * 2, 89 * 2, "#FF5C8D", "lantern-glow"),
        ])
        # Curved pagoda roof & finial
        base.hline(384, 397, 88, "#5E516B")
        base.hline(386, 395, 87, "#4E4359")
        base.hline(388, 393, 86, "#6D5E7D")
        base.hline(390, 391, 85, "#8E8A90")
        base.put(390, 84, "#A8A2AC")

    # 6. Weathered river stones & moss sprouts on the left (scaled by repos)
    sprouts = min(5, max(1, repos // 3))
    stone_spots = [254, 268, 281, 291, 374]
    for i in range(sprouts):
        sx = stone_spots[i]
        base.hline(sx, sx + 4, 101, "#241E29")
        base.hline(sx + 1, sx + 3, 100, "#3D3445")
        base.put(sx + 1, 100, "#52465C")
        if i % 2 == 0:
            base.put(sx + 2, 99, "#5C1029")
            base.put(sx + 2, 98, "#8B1E3F")
            base.put(sx + 3, 97, "#B8325A")

    # 7. Bark Palette (5-tone + Jin deadwood)
    b0, b1, b2, b3, b4 = "#19131F", "#2A2136", "#3E314F", "#56456B", "#715B8A"
    jin_d, jin_l = "#6E6875", "#A29BA8"

    def draw_wood(x0, y0, x1, y1, w_start, w_end, jin=False):
        steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) * 2))
        for i in range(steps + 1):
            t = i / steps
            cx = round(x0 + (x1 - x0) * t)
            cy = round(y0 + (y1 - y0) * t)
            w = max(1, round(w_start + (w_end - w_start) * t))
            for ox in range(w):
                if jin and ox == w - 1 and i % 2 == 0:
                    col = jin_l if i % 4 == 0 else jin_d
                elif ox == 0:
                    col = b4 if (cx + cy) % 3 else b3
                elif ox == w - 1:
                    col = b0
                elif ox == 1 and w >= 4:
                    col = b3 if (cx * 3 + cy) % 5 else b2
                elif (cx + cy * 2 + ox) % 7 == 0:
                    col = b0  # Bark fissure grain
                else:
                    col = b2 if ox < w / 2 else b1
                base.put(cx + ox, cy, col)

    # 8. Trunk, Nebari Roots & Branching by Stage
    if stage == 1:
        draw_wood(333, 86, 334, 81, 2, 1)
    elif stage == 2:
        draw_wood(331, 86, 334, 79, 4, 2)
        draw_wood(334, 79, 326, 72, 2, 1)
    else:
        # Multi-pronged Nebari roots gripping soil
        draw_wood(320, 87, 331, 84, 2, 3)
        draw_wood(326, 87, 333, 83, 2, 4)
        draw_wood(346, 87, 337, 84, 2, 3)
        draw_wood(341, 87, 335, 83, 2, 3)
        # Creeping moss on lower trunk base
        base.put(329, 85, "#5C1029")
        base.put(330, 84, "#8B1E3F")
        base.put(339, 85, "#5C1029")

        # Main gnarled S-curve trunk
        draw_wood(331, 85, 337, 76, 8, 6)
        draw_wood(337, 76, 321, 64, 6, 5)
        draw_wood(321, 64, 326, 52, 5, 3)
        draw_wood(326, 52, 334, 41, 3, 2)

        # Left cascading primary limb + twigs peeking into canopy
        draw_wood(322, 65, 304, 62, 4, 3)
        draw_wood(304, 62, 286, 55, 3, 2)
        draw_wood(286, 55, 274, 52, 2, 1)
        draw_wood(300, 60, 294, 54, 2, 1)  # Twig fork

        # Mid-left shoulder limb
        draw_wood(323, 55, 310, 49, 3, 2)
        draw_wood(310, 49, 302, 44, 2, 1)

        if stage >= 4:
            # Sweeping right reaching limb with Jin deadwood tip
            draw_wood(336, 72, 354, 63, 4, 3)
            draw_wood(354, 63, 372, 55, 3, 2)
            draw_wood(372, 55, 384, 50, 2, 1, jin=True)
            draw_wood(358, 61, 364, 53, 2, 1)  # Upper twig into right pad

            # Upper crown sub-branches (continuous sub-progress adds extra twigs)
            draw_wood(331, 46, 344, 40, 2, 1)
            draw_wood(326, 49, 318, 43, 2, 1)
            if sub_prog >= 0.35:
                draw_wood(342, 67, 348, 57, 2, 1)
            if sub_prog >= 0.7:
                draw_wood(290, 58, 280, 62, 2, 1)

        if stage >= 5:
            draw_wood(382, 51, 394, 46, 2, 1)
            draw_wood(274, 52, 262, 48, 2, 1)

    # 9. Sculpted 8-tone Dithered Blossom Pads + Florets + Hanging Tendrils
    def add_lobe(cx, cy, rx, ry):
        for gy in range(cy - ry, cy + ry + 1):
            for gx in range(cx - rx, cx + rx + 1):
                nx = (gx - cx) / max(1, rx)
                ny = (gy - cy) / max(1, ry)
                dist = nx * nx + ny * ny
                bayer = ((gx & 1) << 1) | (gy & 1)
                if dist <= 0.86 or (dist <= 1.06 and bayer in (0, 3)):
                    if ny > 0.50:
                        col = "#2E0614"
                    elif ny > 0.22:
                        col = "#4A0D21"
                    elif ny > -0.08:
                        col = "#6E1833"
                    elif ny > -0.38:
                        col = "#962248"
                    elif ny > -0.64:
                        col = "#C42E5E"
                    elif ny > -0.84:
                        col = "#EB4B7D"
                    else:
                        col = "#FF7AA3"
                    canopy.put(gx, gy, col)

    def add_floret(cx, cy, bright=True):
        c_edge = "#FF85AB" if bright else "#D9366B"
        c_core = "#FFE0EA" if bright else "#FFC2D4"
        canopy.put(cx, cy - 1, c_edge)
        canopy.put(cx - 1, cy, c_edge)
        canopy.put(cx + 1, cy, c_edge)
        canopy.put(cx, cy + 1, c_edge)
        canopy.put(cx, cy, c_core)

    if stage == 1:
        add_lobe(334, 78, 6, 4)
        add_floret(334, 77, True)
    elif stage == 2:
        add_lobe(325, 70, 12, 6)
        add_lobe(333, 73, 9, 5)
        add_floret(323, 68, True)
    elif stage == 3:
        add_lobe(286, 52, 16, 7)
        add_lobe(308, 45, 14, 6)
        add_lobe(332, 37, 22, 9)
        add_floret(330, 34, True)
        add_floret(284, 50, False)
    else:
        # Multi-lobe sculpted Stage IV / V pads
        # Far-left cascading pad
        add_lobe(276, 52, 18, 7)
        add_lobe(292, 50, 14, 6)
        # Mid-left shoulder pad
        add_lobe(306, 42, 16, 7)
        # Apex crown (3 overlapping lobes)
        add_lobe(324, 34, 18, 8)
        add_lobe(338, 32, 20, 8)
        add_lobe(350, 37, 14, 6)
        # Mid-right bridge pad
        add_lobe(354, 48, 16, 7)
        # Far-right reaching pad
        add_lobe(374, 52, 18, 7)
        add_lobe(388, 50, 12, 5)

        if stage >= 5 or sub_prog >= 0.45:
            add_lobe(264, 55, 11, 5)
        if stage >= 5 or sub_prog >= 0.75:
            add_lobe(394, 46, 12, 5)

        # Hanging blossom tendrils beneath lower pads
        tendrils = [(270, 59), (282, 59), (302, 49), (336, 40), (370, 59), (382, 57)]
        for tx, ty in tendrils[:3 + int(sub_prog * 3)]:
            canopy.put(tx, ty, "#8B1E3F")
            canopy.put(tx, ty + 1, "#D9366B")
            canopy.put(tx, ty + 2, "#FF7AA3")

        # Open sakura/wine florets scaled by weekly contributions
        floret_pts = [
            (334, 28, True), (322, 31, True), (346, 33, False), (276, 48, True),
            (304, 39, True), (374, 48, True), (354, 44, False), (290, 47, False),
            (386, 47, True), (330, 36, False),
        ]
        floret_count = min(len(floret_pts), max(4, this_week // 3 + 4))
        for fx, fy, br in floret_pts[:floret_count]:
            add_floret(fx, fy, br)

    # 10. Fallen petals resting on soil, pot rim, and ground table (scaled by this_week & commits)
    fallen = [
        (316, 86, "#FF5C8D"), (342, 87, "#B8325A"), (355, 86, "#FFA3BF"),
        (296, 101, "#B8325A"), (320, 102, "#FF5C8D"), (348, 101, "#D9366B"),
        (376, 101, "#FF5C8D"), (276, 101, "#8B1E3F"), (362, 89, "#FF5C8D"),
    ]
    for fx, fy, fc in fallen[:min(len(fallen), max(3, this_week // 4 + 3))]:
        base.put(fx, fy, fc)

    base_markup = base.to_svg()
    canopy_markup = canopy.to_svg()
    lantern_markup = "\n    ".join(lantern_fx)

    # 11. Animated drifting 2x2 pixel petals & bobbing fireflies
    petals_markup = ""
    if streak > 0:
        petals = [
            (552, 118, "#FF5C8D", "p1"),
            (612, 98, "#B8325A", "p2"),
            (668, 84, "#FFE0EA", "p3"),
            (748, 114, "#FF5C8D", "p4"),
            (708, 102, "#B8325A", "p1"),
            (584, 122, "#FF7AA3", "p3"),
            (768, 110, "#B8325A", "p2"),
            (644, 92, "#FF5C8D", "p4"),
            (536, 116, "#B8325A", "p1"),
            (732, 96, "#FFE0EA", "p3"),
        ]
        petals_markup = "\n    ".join(_px(x, y, c, cls, size=2) for x, y, c, cls in petals)

    fireflies_markup = ""
    if streak >= 7 or best_day >= 20:
        flies = [
            (516, 92, "#FFE0EA", "ff1"),
            (640, 48, "#FFA3BF", "ff2"),
            (796, 86, "#FFE0EA", "ff1"),
            (716, 60, "#FFA3BF", "ff2"),
        ]
        fireflies_markup = "\n    ".join(_px(x, y, c, cls, size=2) for x, y, c, cls in flies)

    formatted_views = f"{views_count:06,d}"
    lead_zeros = len(formatted_views) - len(str(views_count))
    views_inner = f'<tspan fill="#5C1029">{formatted_views[:lead_zeros]}</tspan><tspan fill="#E8E6E8">{formatted_views[lead_zeros:]}</tspan>'

    canopy_cls = ' class="canopy-sway"' if streak > 0 else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 236" width="900" height="236" fill="none" role="img" aria-label="{USERNAME} — Hero Card &amp; Profile Telemetry">
  <title>{USERNAME} — Pixel Wine-Blossom Bonsai &amp; Profile Telemetry</title>
  <defs>
    <linearGradient id="heroBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{THEME['card_bg_start']}"/>
      <stop offset="55%" stop-color="{THEME['card_bg_mid']}"/>
      <stop offset="100%" stop-color="#141017"/>
    </linearGradient>
    <radialGradient id="bonsaiAura" cx="73%" cy="46%" r="36%">
      <stop offset="0%" stop-color="{THEME['wine_glow']}" stop-opacity="0.22"/>
      <stop offset="55%" stop-color="{THEME['wine_primary']}" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="{THEME['card_bg_start']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="leftAura" cx="12%" cy="32%" r="38%">
      <stop offset="0%" stop-color="{THEME['wine_primary']}" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="{THEME['card_bg_start']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="accentRule" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{THEME['wine_bright']}" stop-opacity="0.9"/>
      <stop offset="55%" stop-color="{THEME['wine_glow']}" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="{THEME['card_border']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="vDivider" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{THEME['panel_border']}" stop-opacity="0"/>
      <stop offset="25%" stop-color="{THEME['panel_border']}" stop-opacity="0.85"/>
      <stop offset="75%" stop-color="{THEME['panel_border']}" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="{THEME['panel_border']}" stop-opacity="0"/>
    </linearGradient>
    <style>
      .claude-serif {{
        font-family: 'Copernicus', 'Tiempos Text', 'Charter', 'Iowan Old Style', Georgia, 'Times New Roman', serif;
      }}
      .claude-sans {{
        font-family: 'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      }}
      @keyframes liveBreath {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.35; }}
      }}
      @keyframes canopySway {{
        0%, 100% {{ transform: translateX(0px); }}
        50% {{ transform: translateX(2px); }}
      }}
      @keyframes lanternFlicker {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.55; }}
      }}
      @keyframes petalFall1 {{
        0% {{ transform: translate(0px, 0px); opacity: 0; }}
        15% {{ opacity: 0.95; }}
        85% {{ opacity: 0.75; }}
        100% {{ transform: translate(-22px, 68px); opacity: 0; }}
      }}
      @keyframes petalFall2 {{
        0% {{ transform: translate(0px, 0px); opacity: 0; }}
        15% {{ opacity: 0.9; }}
        85% {{ opacity: 0.7; }}
        100% {{ transform: translate(16px, 74px); opacity: 0; }}
      }}
      @keyframes fireflyBob {{
        0%, 100% {{ transform: translate(0px, 0px); opacity: 0.25; }}
        50% {{ transform: translate(3px, -5px); opacity: 0.95; }}
      }}
      .live-dot {{ animation: liveBreath 2.4s ease-in-out infinite; }}
      .canopy-sway {{ animation: canopySway 5.2s ease-in-out infinite; }}
      .lantern-glow {{ animation: lanternFlicker 2.6s ease-in-out infinite; }}
      .p1 {{ animation: petalFall1 4.6s ease-in-out infinite; }}
      .p2 {{ animation: petalFall2 5.4s ease-in-out 1.1s infinite; }}
      .p3 {{ animation: petalFall1 5.0s ease-in-out 2.3s infinite; }}
      .p4 {{ animation: petalFall2 5.8s ease-in-out 0.6s infinite; }}
      .ff1 {{ animation: fireflyBob 3.6s ease-in-out infinite; }}
      .ff2 {{ animation: fireflyBob 4.4s ease-in-out 1.4s infinite; }}
      @media (prefers-reduced-motion: reduce) {{
        .live-dot, .canopy-sway, .lantern-glow, .p1, .p2, .p3, .p4, .ff1, .ff2 {{ animation: none !important; }}
      }}
    </style>
  </defs>

  <!-- Outer Card -->
  <rect x="0" y="0" width="900" height="236" rx="10" fill="url(#heroBg)"/>
  <rect x="0" y="0" width="900" height="236" rx="10" fill="url(#leftAura)"/>
  <rect x="0" y="0" width="900" height="236" rx="10" fill="url(#bonsaiAura)"/>

  <!-- Minimal Inline Profile Views Indicator (top-right, no dedicated row) -->
  <g transform="translate(868, 32)">
    <circle cx="-94" cy="-4" r="2.6" fill="{THEME['wine_glow']}" class="live-dot"/>
    <text id="profile-views-count" x="-36" y="0" text-anchor="end" class="claude-serif" font-size="13" font-weight="700" font-variant-numeric="tabular-nums">{views_inner}</text>
    <text x="0" y="0" text-anchor="end" class="claude-sans" font-size="11.5" fill="{THEME['text_muted']}">views</text>
  </g>

  <!-- Left Zone: Minimal Username & Contact -->
  <g transform="translate(44, 82)">
    <text x="0" y="28" class="claude-serif" font-size="44" font-weight="700" fill="{THEME['text_main']}">{USERNAME} <tspan class="claude-sans" font-size="14" font-weight="500" fill="{THEME['wine_glow']}">/ r41n</tspan></text>
    <line x1="0" y1="46" x2="260" y2="46" stroke="url(#accentRule)" stroke-width="1.5"/>
    <text x="0" y="74" class="claude-sans" font-size="12.5" fill="{THEME['text_muted']}">0xraiven@proton.me <tspan fill="#3D3545"> · </tspan> github.com/0xraiven</text>
  </g>

  <!-- Subtle Vertical Divider -->
  <line x1="458" y1="22" x2="458" y2="214" stroke="url(#vDivider)" stroke-width="1"/>

  <!-- Right Zone: High-Detail 2x2 Pixel-Art Bonsai -->
  <g shape-rendering="crispEdges">
    {base_markup}
    {lantern_markup}
    <g{canopy_cls}>
      {canopy_markup}
    </g>
    {petals_markup}
    {fireflies_markup}
  </g>

  <text x="868" y="220" text-anchor="end" class="claude-sans" font-size="10" font-weight="500" fill="{THEME['text_dim']}">Stage {stage_roman} · {commits:,} commits</text>
</svg>"""

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

    existing_views = _read_existing_views(HERO_PATH)
    hero_svg = render_hero_svg(stats, existing_views)
    os.makedirs(os.path.dirname(HERO_PATH), exist_ok=True)
    with open(HERO_PATH, "w", encoding="utf-8") as hf:
        hf.write(hero_svg)
    print(f"Generated commit-driven Pixel Bonsai hero card at {HERO_PATH} (views={existing_views})")

    # Update cache-buster query param in README.md
    try:
        if os.path.exists("README.md"):
            with open("README.md", "r", encoding="utf-8") as rf:
                readme = rf.read()
            timestamp = int(datetime.datetime.now().timestamp())
            new_readme = re.sub(r'assets/contribution-3d\.svg(?:\?v=[^\s\"\'>]+)?', f'assets/contribution-3d.svg?v={timestamp}', readme)
            new_readme = re.sub(r'assets/hero-card\.svg(?:\?v=[^\s\"\'>]+)?', f'assets/hero-card.svg?v={timestamp}', new_readme)
            if new_readme != readme:
                with open("README.md", "w", encoding="utf-8") as wf:
                    wf.write(new_readme)
                print(f"Updated README.md cache-buster query params to ?v={timestamp}")
    except Exception as e:
        print(f"README cache-buster update note: {e}")

if __name__ == "__main__":
    main()
