"""3D isometric GitHub contribution graph & developer metrics SVG renderer."""

import math

from theme import CLAUDE_SANS_FONT, CLAUDE_SERIF_FONT, THEME


def render_contrib_svg(calendar, stats, username):
    """Render the 900x570 3D isometric contribution graph SVG."""
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
                level, h = 0, 4
            elif count <= 2:
                level, h = 1, 10
            elif count <= 5:
                level, h = 2, 18
            elif count <= 9:
                level, h = 3, 28
            else:
                level = 4
                h = min(48, 28 + (count - 9) * 2.5)

            colors = THEME["cubes"][level]
            bx = origin_x + w_idx * dx_w - d_idx * dx_d
            by = origin_y + w_idx * dy_w + d_idx * dy_d

            t_pt = (bx, by - h)
            r_pt = (bx + dx_w, by + dy_w - h)
            b_pt = (bx + dx_w - dx_d, by + dy_w + dy_d - h)
            l_pt = (bx - dx_d, by + dy_d - h)

            b_base = (bx + dx_w - dx_d, by + dy_w + dy_d)
            l_base = (bx - dx_d, by + dy_d)
            r_base = (bx + dx_w, by + dy_w)

            cubes_svg.append(
                f'<polygon points="{l_pt[0]:.1f},{l_pt[1]:.1f} {b_pt[0]:.1f},{b_pt[1]:.1f} {b_base[0]:.1f},{b_base[1]:.1f} {l_base[0]:.1f},{l_base[1]:.1f}" '
                f'fill="{colors["left"]}" stroke="{colors["stroke"]}" stroke-width="0.4"/>'
                f'<polygon points="{r_pt[0]:.1f},{r_pt[1]:.1f} {b_pt[0]:.1f},{b_pt[1]:.1f} {b_base[0]:.1f},{b_base[1]:.1f} {r_base[0]:.1f},{r_base[1]:.1f}" '
                f'fill="{colors["right"]}" stroke="{colors["stroke"]}" stroke-width="0.4"/>'
                f'<polygon points="{t_pt[0]:.1f},{t_pt[1]:.1f} {r_pt[0]:.1f},{r_pt[1]:.1f} {b_pt[0]:.1f},{b_pt[1]:.1f} {l_pt[0]:.1f},{l_pt[1]:.1f}" '
                f'fill="{colors["top"]}" stroke="{colors["stroke"]}" stroke-width="0.5"/>'
            )

    cubes_markup = "\n    ".join(cubes_svg)

    total_fmt = f"{stats['total']:,}"
    avg_fmt = f"{stats['average']:.2f}"
    commits_fmt = f"{stats['commits']:,}"
    prs_fmt = f"{stats['prs']:,}"
    issues_fmt = f"{stats['issues']:,}"
    repos_fmt = f"{stats['repos']:,}"

    circ_r = 25
    circumference = 2 * math.pi * circ_r
    score_clamped = min(1.0, max(0.08, stats["rank_score"]))
    dash_offset = circumference * (1.0 - score_clamped)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}" fill="none" role="img" aria-label="{username} — 3D Isometric Contribution Graph &amp; Developer Metrics">
  <title>{username} — 3D Isometric Contribution Graph &amp; Developer Metrics</title>
  <defs>
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{THEME['card_bg_start']}"/>
      <stop offset="50%" stop-color="{THEME['card_bg_mid']}"/>
      <stop offset="100%" stop-color="{THEME['card_bg_end']}"/>
    </linearGradient>
    <radialGradient id="wineAura" cx="35%" cy="45%" r="55%">
      <stop offset="0%" stop-color="{THEME['wine_glow']}" stop-opacity="0.16"/>
      <stop offset="50%" stop-color="{THEME['wine_primary']}" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="{THEME['card_bg_start']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="panelBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#15141D"/>
      <stop offset="100%" stop-color="#0E0D13"/>
    </linearGradient>
    <filter id="accentGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <style>
      .claude-serif {{ font-family: {CLAUDE_SERIF_FONT}; }}
      .claude-sans {{ font-family: {CLAUDE_SANS_FONT}; }}
      .card-header {{ font-family: {CLAUDE_SANS_FONT}; font-size: 11px; font-weight: 600; letter-spacing: 0.4px; fill: {THEME['wine_glow']}; }}
      .metric-val {{ font-family: {CLAUDE_SERIF_FONT}; font-size: 24px; font-weight: 700; fill: {THEME['text_main']}; }}
      .metric-val-sm {{ font-family: {CLAUDE_SERIF_FONT}; font-size: 21px; font-weight: 700; fill: {THEME['text_main']}; }}
      .metric-val-wine {{ font-family: {CLAUDE_SERIF_FONT}; font-size: 24px; font-weight: 700; fill: {THEME['wine_glow']}; }}
      .metric-lbl {{ font-family: {CLAUDE_SANS_FONT}; font-size: 11px; font-weight: 600; fill: {THEME['text_main']}; }}
      .metric-tag {{ font-family: {CLAUDE_SANS_FONT}; font-size: 10.5px; font-weight: 600; letter-spacing: 0.3px; fill: {THEME['wine_glow']}; }}
      .metric-sub {{ font-family: {CLAUDE_SANS_FONT}; font-size: 10px; fill: {THEME['text_muted']}; }}
      .avg-text {{ font-family: {CLAUDE_SANS_FONT}; font-size: 11px; fill: {THEME['text_muted']}; }}
    </style>
  </defs>

  <!-- Container Base -->
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="10" fill="url(#cardBg)"/>
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="10" fill="url(#wineAura)"/>

  <!-- Integrated Top-Left Title -->
  <g transform="translate(28, 28)">
    <text x="0" y="24" class="claude-serif" font-size="28" font-weight="700" fill="{THEME['text_main']}">Contribution Graph</text>
    <text x="0" y="45" class="claude-sans" font-size="12" fill="{THEME['text_muted']}">
      <tspan fill="{THEME['wine_glow']}" font-weight="600">{total_fmt}</tspan> contributions · {stats['total_range']}
    </text>
  </g>

  <!-- 3D Isometric Contribution Graph -->
  <g id="isometric-grid">
    {cubes_markup}
  </g>

  <!-- Top-Right: Contributions Card -->
  <g transform="translate(502, 24)">
    <rect width="374" height="120" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">Contributions</text>

    <g transform="translate(22, 40)">
      <text x="0" y="20" class="metric-val">{total_fmt}</text>
      <text x="0" y="37" class="metric-lbl">Total</text>
      <text x="0" y="52" class="metric-sub">{stats['total_range']}</text>
    </g>
    <g transform="translate(160, 40)">
      <text x="0" y="20" class="metric-val">{stats['this_week']}</text>
      <text x="0" y="37" class="metric-lbl">This week</text>
      <text x="0" y="52" class="metric-sub">{stats['this_week_range']}</text>
    </g>
    <g transform="translate(284, 40)">
      <text x="0" y="20" class="metric-val">{stats['best_day']}</text>
      <text x="0" y="37" class="metric-lbl">Best day</text>
      <text x="0" y="52" class="metric-sub">{stats['best_day_date']}</text>
    </g>

    <text x="374" y="138" text-anchor="end" class="avg-text">
      Average: <tspan fill="{THEME['wine_glow']}" font-weight="700">{avg_fmt}</tspan> / day
    </text>
  </g>

  <!-- Bottom-Left: Streaks Card -->
  <g transform="translate(24, 346)">
    <rect width="264" height="100" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>
    <circle cx="16" cy="18" r="3" fill="{THEME['wine_glow']}"/>
    <text x="26" y="22" class="card-header">Streaks</text>

    <g transform="translate(22, 38)">
      <text x="0" y="20" class="metric-val-wine">{stats['longest_streak']} <tspan class="claude-sans" fill="{THEME['text_main']}" font-size="12" font-weight="600">days</tspan></text>
      <text x="0" y="36" class="metric-lbl">Longest</text>
      <text x="0" y="50" class="metric-sub">{stats['longest_range']}</text>
    </g>
    <g transform="translate(144, 38)">
      <text x="0" y="20" class="metric-val-wine">{stats['current_streak']} <tspan class="claude-sans" fill="{THEME['text_main']}" font-size="12" font-weight="600">days</tspan></text>
      <text x="0" y="36" class="metric-lbl">Current</text>
      <text x="0" y="50" class="metric-sub">{stats['curr_range']}</text>
    </g>
  </g>

  <!-- Bottom Bar: Developer Stats & Rank -->
  <g transform="translate(24, 458)">
    <rect width="852" height="94" rx="6" fill="url(#panelBg)" stroke="{THEME['panel_border']}" stroke-width="1"/>

    <g transform="translate(20, 16)">
      <circle cx="31" cy="31" r="{circ_r}" fill="none" stroke="#221D27" stroke-width="3.5"/>
      <circle cx="31" cy="31" r="{circ_r}" fill="none" stroke="{THEME['wine_glow']}" stroke-width="3.5"
              stroke-linecap="round" stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{dash_offset:.1f}"
              transform="rotate(-90 31 31)" filter="url(#accentGlow)"/>
      <text x="31" y="38" text-anchor="middle" class="claude-serif" font-size="21" font-weight="700" fill="{THEME['text_main']}">{stats['rank']}</text>
      <g transform="translate(70, 14)">
        <text x="0" y="10" class="metric-tag">Developer Rank</text>
        <text x="0" y="24" class="metric-sub">Percentile Grade</text>
        <text x="0" y="38" class="claude-sans" font-size="11" font-weight="600" fill="{THEME['text_main']}">Tier: <tspan fill="{THEME['wine_glow']}">{stats['rank']}</tspan></text>
      </g>
    </g>

    <line x1="210" y1="18" x2="210" y2="76" stroke="#211C24" stroke-width="1"/>
    <g transform="translate(230, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Total Commits</text>
      <text x="12" y="33" class="metric-val-sm">{commits_fmt}</text>
      <text x="12" y="47" class="metric-sub">Code activity</text>
    </g>

    <line x1="376" y1="18" x2="376" y2="76" stroke="#211C24" stroke-width="1"/>
    <g transform="translate(396, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Pull Requests</text>
      <text x="12" y="33" class="metric-val-sm">{prs_fmt}</text>
      <text x="12" y="47" class="metric-sub">Merged &amp; authored</text>
    </g>

    <line x1="538" y1="18" x2="538" y2="76" stroke="#211C24" stroke-width="1"/>
    <g transform="translate(558, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Code Issues</text>
      <text x="12" y="33" class="metric-val-sm">{issues_fmt}</text>
      <text x="12" y="47" class="metric-sub">Reported &amp; tracked</text>
    </g>

    <line x1="696" y1="18" x2="696" y2="76" stroke="#211C24" stroke-width="1"/>
    <g transform="translate(716, 22)">
      <circle cx="3" cy="7" r="3" fill="{THEME['wine_glow']}"/>
      <text x="12" y="10" class="metric-tag">Contributed To</text>
      <text x="12" y="33" class="metric-val-sm">{repos_fmt} <tspan class="claude-sans" font-size="12" font-weight="500" fill="{THEME['text_muted']}">repos</tspan></text>
      <text x="12" y="47" class="metric-sub">Open-source impact</text>
    </g>
  </g>
</svg>"""
