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
  <rect x="1" y="1" width="{svg_w - 2}" height="{svg_h - 2}" rx="10" fill="url(#cardBg)" stroke="{THEME['card_border']}" stroke-width="1"/>
  <rect x="1" y="1" width="{svg_w - 2}" height="{svg_h - 2}" rx="10" fill="url(#wineAura)"/>

  <!-- Top Header Bar -->
  <g transform="translate(0, 0)">
    <circle cx="28" cy="25" r="3.5" fill="{THEME['wine_glow']}" filter="url(#accentGlow)"/>

    <!-- Integrated Contribution Graph Heading -->
    <text x="42" y="30" class="heading-title">Contribution Graph</text>

    <!-- Right-aligned Total Contributions Summary -->
    <text x="{svg_w - 24}" y="29" text-anchor="end" class="heading-sub">
      <tspan fill="{THEME['text_main']}" font-weight="600">{total_fmt}</tspan> contributions in the last year
    </text>

    <!-- Header Divider Line -->
    <line x1="20" y1="46" x2="{svg_w - 20}" y2="46" stroke="#211C24" stroke-width="1"/>
  </g>

  <!-- ==================== 3D ISOMETRIC CONTRIBUTION GRAPH ==================== -->
  <g id="isometric-grid">
    {cubes_markup}
  </g>

  <!-- ==================== TOP-RIGHT: CONTRIBUTIONS CARD ==================== -->
  <g transform="translate(534, 58)">
    <rect width="346" height="114" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">Contributions</text>

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
  <g transform="translate(24, 346)">
    <rect width="250" height="96" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">Streaks</text>

    <!-- Col 1: Longest -->
    <g transform="translate(20, 36)">
      <text x="0" y="20" class="metric-val-wine">{stats['longest_streak']} <tspan class="claude-sans" fill="{THEME['text_main']}" font-size="12" font-weight="600">days</tspan></text>
      <text x="0" y="34" class="metric-lbl">Longest</text>
      <text x="0" y="46" class="metric-sub">{stats['longest_range']}</text>
    </g>

    <!-- Col 2: Current -->
    <g transform="translate(132, 36)">
      <text x="0" y="20" class="metric-val-wine">{stats['current_streak']} <tspan class="claude-sans" fill="{THEME['text_main']}" font-size="12" font-weight="600">days</tspan></text>
      <text x="0" y="34" class="metric-lbl">Current</text>
      <text x="0" y="46" class="metric-sub">{stats['curr_range']}</text>
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

def _px(x, y, color, cls="", size=3):
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
    """Render 900x236 Hero Card SVG with a highly detailed 3x3 pixel-art Wine-Blossom Bonsai & minimal inline view count."""
    commits = stats["commits"]
    this_week = stats["this_week"]
    streak = stats["current_streak"]
    repos = stats["repos"]

    if commits < 100:
        stage, stage_roman = 1, "I"
    elif commits < 400:
        stage, stage_roman = 2, "II"
    elif commits < 800:
        stage, stage_roman = 3, "III"
    elif commits < 1500:
        stage, stage_roman = 4, "IV"
    else:
        stage, stage_roman = 5, "V"

    px = []
    # Subtle night-sky pixel stars/dust in upper bonsai space (3x3)
    for sx, sy, sc in [
        (486, 36, "#2A2230"), (543, 27, "#3D1624"), (615, 33, "#2A2230"),
        (762, 30, "#3D1624"), (828, 45, "#2A2230"), (846, 84, "#3D1624"),
        (468, 87, "#2A2230"), (807, 120, "#2A2230"), (510, 60, "#231B29"),
    ]:
        px.append(_px(sx, sy, sc))

    # Ground horizon line in subtle pixel dashes (y=204)
    for gx in range(486, 846, 6):
        px.append(_px(gx, 204, "#1E1924"))

    # Detailed stepped Tokoname ceramic bonsai pot (centered x=666, y=180..201)
    for x in range(606, 729, 3):
        px.append(_px(x, 180, "#7D1B3B"))  # Top rim highlight
    for x in range(609, 726, 3):
        px.append(_px(x, 183, "#5C1029"))
        px.append(_px(x, 186, "#420B1D"))
        px.append(_px(x, 189, "#330816"))
        px.append(_px(x, 192, "#290611"))
        px.append(_px(x, 195, "#20040D"))
    # Recessed decorative panel on pot front
    for x in range(624, 711, 3):
        px.append(_px(x, 189, "#4D0E23"))
        px.append(_px(x, 192, "#3D091A"))
    for x in range(615, 720, 3):
        px.append(_px(x, 198, "#170309"))
    # Pot feet
    for fx in (621, 624, 708, 711):
        px.append(_px(fx, 201, "#330816"))

    # Mossy soil mound & tufts (y=171..177)
    for x in range(615, 720, 3):
        px.append(_px(x, 177, "#241C2B"))
    for x in range(627, 708, 3):
        px.append(_px(x, 174, "#2F2438"))
    for mx in (621, 633, 696, 711):
        px.append(_px(mx, 174, "#4A182D"))
        px.append(_px(mx, 171, "#6E1E3B"))

    # Pixel Japanese Stone Lantern (Tōrō) on the right (x=765..783, y=174..201)
    if stage >= 3:
        for lx in range(768, 783, 3):
            px.append(_px(lx, 201, "#2A2330"))
        for ly in range(189, 201, 3):
            px.append(_px(774, ly, "#3D3445"))
        # Lantern firebox with glowing wine flame
        px.append(_px(768, 183, "#3D3445"))
        px.append(_px(768, 186, "#3D3445"))
        px.append(_px(780, 183, "#3D3445"))
        px.append(_px(780, 186, "#3D3445"))
        px.append(_px(771, 186, "#B8325A", "lantern-glow"))
        px.append(_px(774, 183, "#FF5C8D", "lantern-glow"))
        px.append(_px(774, 186, "#FFA3BF", "lantern-glow"))
        px.append(_px(777, 186, "#B8325A", "lantern-glow"))
        # Lantern roof
        for lx in range(765, 786, 3):
            px.append(_px(lx, 180, "#4E4359"))
        for lx in range(768, 783, 3):
            px.append(_px(lx, 177, "#5E516B"))
        px.append(_px(774, 174, "#716280"))

    # Satellite river stones & moss sprouts on the left (scaled by repos)
    sprouts = min(5, max(1, repos // 3))
    stone_spots = [516, 540, 564, 585, 741]
    for i in range(sprouts):
        sx = stone_spots[i]
        px.append(_px(sx, 201, "#2A2330"))
        px.append(_px(sx + 3, 201, "#3D3445"))
        px.append(_px(sx + 6, 201, "#241E29"))
        if i % 2 == 0:
            px.append(_px(sx + 3, 198, "#5C1029"))
            px.append(_px(sx + 3, 195, "#8B1E3F"))

    # Detailed 4-tone bark trunk & branches (3x3 grid)
    b0, b1, b2, b3 = "#1F1826", "#31273D", "#473957", "#614F75"
    trunk = []
    if stage == 1:
        trunk = [(663, 171, b1), (666, 171, b2), (663, 168, b2), (666, 165, b3)]
    elif stage == 2:
        trunk = [
            (660, 174, b1), (663, 171, b1), (666, 171, b2),
            (663, 168, b2), (660, 165, b2), (657, 162, b3),
            (654, 159, b2), (651, 156, b3), (648, 153, b3),
        ]
    else:
        # Flared nebari roots
        for rx in range(645, 684, 3):
            col = b0 if rx in (645, 681) else (b1 if rx in (648, 678) else b2)
            trunk.append((rx, 174, col))
        for rx in range(651, 678, 3):
            trunk.append((rx, 171, b2 if rx < 666 else b1))

        # Thick gnarled S-curve trunk
        spine = [
            (660, 168, 15), (663, 165, 15), (666, 162, 15), (669, 159, 12),
            (672, 156, 12), (672, 153, 12), (669, 150, 12), (666, 147, 12),
            (663, 144, 12), (657, 141, 12), (654, 138, 12), (648, 135, 12),
            (645, 132, 9), (642, 129, 9), (639, 126, 9), (639, 123, 9),
            (642, 120, 9), (645, 117, 9), (648, 114, 9), (651, 111, 9),
            (654, 108, 9), (657, 105, 6), (660, 102, 6), (663, 99, 6),
            (663, 96, 6), (666, 93, 6),
        ]
        for tx, ty, w in spine:
            for offset in range(0, w, 3):
                if offset == 0:
                    c = b3
                elif offset >= w - 3:
                    c = b0
                elif offset == 3:
                    c = b2
                else:
                    c = b1
                trunk.append((tx + offset, ty, c))

        # Left cascading limb
        left_limb = [
            (636, 129, 6), (633, 129, 6), (627, 126, 6), (621, 126, 6),
            (615, 123, 6), (609, 123, 6), (603, 120, 6), (597, 117, 6),
            (591, 117, 3), (585, 114, 3), (579, 111, 3), (573, 108, 3),
        ]
        for tx, ty, w in left_limb:
            for offset in range(0, w, 3):
                trunk.append((tx + offset, ty, b3 if offset == 0 else b1))

        # Mid-left shoulder sub-branch
        for tx, ty in [(642, 111), (636, 108), (630, 105), (624, 102), (618, 99)]:
            trunk.append((tx, ty, b2))
            trunk.append((tx + 3, ty - 3, b3))

        if stage >= 4:
            # Sweeping right reaching limb
            right_limb = [
                (675, 141, 6), (681, 138, 6), (687, 135, 6), (693, 132, 6),
                (699, 129, 6), (705, 126, 6), (711, 123, 6), (717, 120, 6),
                (723, 117, 3), (729, 114, 3), (735, 111, 3), (741, 108, 3),
            ]
            for tx, ty, w in right_limb:
                for offset in range(0, w, 3):
                    trunk.append((tx + offset, ty, b3 if offset == 0 else b1))
            # Upper crown sub-branches
            for tx, ty in [(669, 90), (675, 87), (681, 84), (657, 93), (651, 90)]:
                trunk.append((tx, ty, b2))
        if stage >= 5:
            for tx, ty in [(747, 105), (753, 102), (567, 105), (561, 102)]:
                trunk.append((tx, ty, b2))

    for x, y, col in trunk:
        px.append(_px(x, y, col))

    # Sculpted 6-tone dithered pixel blossom pads (3x3)
    canopy_map = {}
    def add_pad(cx, cy, rx, ry):
        for py in range(cy - ry, cy + ry + 1, 3):
            for px_x in range(cx - rx, cx + rx + 1, 3):
                nx = (px_x - cx) / max(1, rx)
                ny = (py - cy) / max(1, ry)
                dist = nx * nx + ny * ny
                # Dithered organic silhouette edge
                edge_hash = ((px_x // 3) * 7 + (py // 3) * 13) % 5
                if dist <= 0.92 or (dist <= 1.08 and edge_hash in (0, 2, 4)):
                    if ny > 0.45:
                        col = "#2E0614"
                    elif ny > 0.12:
                        col = "#4A0D21"
                    elif ny > -0.25:
                        col = "#751736"
                    elif ny > -0.55:
                        col = "#A62850"
                    elif ny > -0.8:
                        col = "#D9366B"
                    else:
                        col = "#FF5C8D"
                    canopy_map[(px_x, py)] = col

    if stage == 1:
        add_pad(666, 159, 12, 6)
    elif stage == 2:
        add_pad(648, 144, 24, 12)
    elif stage == 3:
        add_pad(582, 105, 36, 15)
        add_pad(663, 84, 48, 21)
        add_pad(618, 93, 27, 12)
    else:
        add_pad(570, 105, 42, 16)   # Far-left cascading pad
        add_pad(618, 87, 36, 15)    # Mid-left shoulder pad
        add_pad(666, 69, 54, 22)    # Apex crown pad
        add_pad(705, 84, 33, 14)    # Upper-right bridge pad
        add_pad(744, 102, 45, 16)   # Far-right reaching pad
        if stage >= 5:
            add_pad(774, 90, 30, 13)
            add_pad(540, 96, 27, 12)

    # Weekly bright blossom highlights (#FF6B98 & #FFC2D4)
    bloom_spots = [
        (654, 51), (666, 48), (678, 51), (642, 54), (690, 57),
        (561, 93), (573, 90), (552, 96), (609, 75), (624, 75),
        (735, 90), (750, 90), (762, 93), (702, 72), (663, 57),
        (582, 96), (741, 96), (672, 54), (615, 81), (711, 78),
    ]
    bloom_count = min(len(bloom_spots), max(5, this_week // 2 + 5))
    for i, (bx, by) in enumerate(bloom_spots[:bloom_count]):
        canopy_map[(bx, by)] = "#FFC2D4" if i % 3 == 0 else "#FF6B98"

    canopy_markup = "\n      ".join(_px(x, y, col) for (x, y), col in canopy_map.items())
    base_markup = "\n    ".join(px)

    # Staggered drifting 3x3 pixel petals when streak > 0
    petals_markup = ""
    if streak > 0:
        petals = [
            (567, 117, "#FF5C8D", "p1"),
            (615, 102, "#B8325A", "p2"),
            (666, 90, "#FFC2D4", "p3"),
            (735, 117, "#FF5C8D", "p4"),
            (702, 99, "#B8325A", "p1"),
            (591, 123, "#FF5C8D", "p3"),
            (753, 114, "#B8325A", "p2"),
            (642, 96, "#FF6B98", "p4"),
            (549, 114, "#B8325A", "p1"),
        ]
        petals_markup = "\n    ".join(_px(x, y, c, cls) for x, y, c, cls in petals)

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
        50% {{ opacity: 0.6; }}
      }}
      @keyframes petalFall1 {{
        0% {{ transform: translate(0px, 0px); opacity: 0; }}
        15% {{ opacity: 0.95; }}
        85% {{ opacity: 0.75; }}
        100% {{ transform: translate(-21px, 66px); opacity: 0; }}
      }}
      @keyframes petalFall2 {{
        0% {{ transform: translate(0px, 0px); opacity: 0; }}
        15% {{ opacity: 0.9; }}
        85% {{ opacity: 0.7; }}
        100% {{ transform: translate(15px, 72px); opacity: 0; }}
      }}
      .live-dot {{ animation: liveBreath 2.4s ease-in-out infinite; }}
      .canopy-sway {{ animation: canopySway 5.2s ease-in-out infinite; }}
      .lantern-glow {{ animation: lanternFlicker 2.8s ease-in-out infinite; }}
      .p1 {{ animation: petalFall1 4.6s ease-in-out infinite; }}
      .p2 {{ animation: petalFall2 5.4s ease-in-out 1.1s infinite; }}
      .p3 {{ animation: petalFall1 5.0s ease-in-out 2.3s infinite; }}
      .p4 {{ animation: petalFall2 5.8s ease-in-out 0.6s infinite; }}
      @media (prefers-reduced-motion: reduce) {{
        .live-dot, .canopy-sway, .lantern-glow, .p1, .p2, .p3, .p4 {{ animation: none !important; }}
      }}
    </style>
  </defs>

  <!-- Outer Card -->
  <rect x="1" y="1" width="898" height="234" rx="10" fill="url(#heroBg)" stroke="{THEME['card_border']}" stroke-width="1"/>
  <rect x="1" y="1" width="898" height="234" rx="10" fill="url(#leftAura)"/>
  <rect x="1" y="1" width="898" height="234" rx="10" fill="url(#bonsaiAura)"/>

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

  <!-- Right Zone: Detailed 3x3 Pixel-Art Bonsai -->
  <g shape-rendering="crispEdges">
    {base_markup}
    <g{canopy_cls}>
      {canopy_markup}
    </g>
    {petals_markup}
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
