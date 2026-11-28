"""Commit-driven 2x2 pixel-art Wine-Blossom Bonsai hero card SVG renderer."""

import os
import re

from pixel_canvas import PixelCanvas, px_rect
from theme import CLAUDE_SANS_FONT, CLAUDE_SERIF_FONT, THEME


def read_existing_views(hero_path):
    """Preserve existing profile view count across daily contribution graph rebuilds."""
    for path in (hero_path, "assets/profile-views.svg"):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                m = re.search(r'id="profile-views-count"[^>]*>(.*?)</text>', content)
                if m:
                    digits = re.sub(r"<[^>]+>", "", m.group(1)).replace(",", "").strip()
                    if digits.isdigit() and 0 < int(digits) < 100_000_000:
                        return int(digits)
        except Exception:
            pass
    return 367


def _growth_stage(commits):
    if commits < 100:
        return 1, "I", commits / 100.0
    if commits < 400:
        return 2, "II", (commits - 100) / 300.0
    if commits < 800:
        return 3, "III", (commits - 400) / 400.0
    if commits < 1500:
        return 4, "IV", (commits - 800) / 700.0
    return 5, "V", 1.0


def _draw_sky_and_ground(base, rank, repos, this_week):
    for sx, sy, sc in [
        (248, 17, "#2A2230"), (272, 13, "#3D1624"), (304, 15, "#2A2230"),
        (378, 14, "#3D1624"), (258, 34, "#231B29"), (424, 42, "#2A2230"),
        (244, 48, "#2A2230"), (402, 58, "#231B29"), (292, 26, "#231B29"),
    ]:
        base.put(sx, sy, sc)

    if rank in ("A-", "A", "A+", "S"):
        for mx, my, mc in [
            (416, 15, "#4E4359"), (417, 15, "#6E5F7D"),
            (414, 16, "#5E516B"), (415, 16, "#8E8A90"),
            (413, 17, "#6E5F7D"), (414, 17, "#A8A2AC"),
            (413, 18, "#6E5F7D"), (414, 18, "#8E8A90"),
            (413, 19, "#6E5F7D"), (414, 19, "#A8A2AC"),
            (414, 20, "#5E516B"), (415, 20, "#8E8A90"),
            (416, 21, "#4E4359"), (417, 21, "#6E5F7D"),
        ]:
            base.put(mx, my, mc)

    for gx in range(244, 426):
        if gx % 3 != 0 or (295 <= gx <= 375):
            base.put(gx, 102, "#1C1722")
        if 302 <= gx <= 366:
            base.put(gx, 103, "#120F17")

    sprouts = min(5, max(1, repos // 3))
    for i, sx in enumerate([254, 268, 281, 291, 374][:sprouts]):
        base.hline(sx, sx + 4, 101, "#241E29")
        base.hline(sx + 1, sx + 3, 100, "#3D3445")
        base.put(sx + 1, 100, "#52465C")
        if i % 2 == 0:
            base.put(sx + 2, 99, "#5C1029")
            base.put(sx + 2, 98, "#8B1E3F")
            base.put(sx + 3, 97, "#B8325A")

    fallen = [
        (316, 86, "#FF5C8D"), (342, 87, "#B8325A"), (355, 86, "#FFA3BF"),
        (296, 101, "#B8325A"), (320, 102, "#FF5C8D"), (348, 101, "#D9366B"),
        (376, 101, "#FF5C8D"), (276, 101, "#8B1E3F"), (362, 89, "#FF5C8D"),
    ]
    for fx, fy, fc in fallen[:min(len(fallen), max(3, this_week // 4 + 3))]:
        base.put(fx, fy, fc)


def _draw_pot_and_lantern(base, stage):
    for gx in range(298, 371):
        col = "#9C254B" if 304 <= gx <= 324 else ("#7D1B3B" if gx < 354 else "#5C1029")
        base.put(gx, 89, col)
    base.hline(299, 369, 90, "#420B1D")

    for gy in range(91, 99):
        for gx in range(301, 368):
            if 310 <= gx <= 358 and 92 <= gy <= 97:
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

    for fx in (306, 307, 308, 359, 360, 361):
        base.put(fx, 100, "#360817")
    for fx in (307, 308, 359, 360):
        base.put(fx, 101, "#24050F")

    for gx in range(302, 367):
        base.put(gx, 88, "#231B2A" if gx % 2 == 0 else "#1B1521")
    for gx in range(308, 361):
        base.put(gx, 87, "#2F2438" if (gx * 3) % 5 else "#4A182D")
    for gx in range(316, 352):
        base.put(gx, 86, "#392A42" if gx % 3 else "#5C1029")
    for mx in (305, 313, 349, 359, 363):
        base.put(mx, 87, "#5C1029")
        base.put(mx, 86, "#8B1E3F")
        if mx in (313, 359):
            base.put(mx + 1, 85, "#B8325A")

    if stage < 3:
        return []

    base.hline(387, 394, 101, "#2A2330")
    base.hline(388, 393, 100, "#3D3445")
    for gy in range(93, 100):
        base.put(390, gy, "#4E4359")
        base.put(391, gy, "#342C3D")
    base.hline(387, 394, 92, "#4E4359")
    for gy in (89, 90, 91):
        base.put(387, gy, "#3D3445")
        base.put(394, gy, "#2D2536")
    base.hline(384, 397, 88, "#5E516B")
    base.hline(386, 395, 87, "#4E4359")
    base.hline(388, 393, 86, "#6D5E7D")
    base.hline(390, 391, 85, "#8E8A90")
    base.put(390, 84, "#A8A2AC")

    return [
        px_rect(388 * 2, 90 * 2, "#B8325A", "lantern-glow"),
        px_rect(389 * 2, 90 * 2, "#FF5C8D", "lantern-glow"),
        px_rect(390 * 2, 90 * 2, "#FFE0EA", "lantern-glow"),
        px_rect(391 * 2, 90 * 2, "#FF5C8D", "lantern-glow"),
        px_rect(392 * 2, 90 * 2, "#B8325A", "lantern-glow"),
        px_rect(393 * 2, 90 * 2, "#8B1E3F", "lantern-glow"),
        px_rect(390 * 2, 89 * 2, "#FFA3BF", "lantern-glow"),
        px_rect(391 * 2, 89 * 2, "#FF5C8D", "lantern-glow"),
    ]


def _draw_bonsai_wood(base, stage, sub_prog):
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
                    col = b0
                else:
                    col = b2 if ox < w / 2 else b1
                base.put(cx + ox, cy, col)

    if stage == 1:
        draw_wood(333, 86, 334, 81, 2, 1)
        return
    if stage == 2:
        draw_wood(331, 86, 334, 79, 4, 2)
        draw_wood(334, 79, 326, 72, 2, 1)
        return

    draw_wood(320, 87, 331, 84, 2, 3)
    draw_wood(326, 87, 333, 83, 2, 4)
    draw_wood(346, 87, 337, 84, 2, 3)
    draw_wood(341, 87, 335, 83, 2, 3)
    base.put(329, 85, "#5C1029")
    base.put(330, 84, "#8B1E3F")
    base.put(339, 85, "#5C1029")

    draw_wood(331, 85, 337, 76, 8, 6)
    draw_wood(337, 76, 321, 64, 6, 5)
    draw_wood(321, 64, 326, 52, 5, 3)
    draw_wood(326, 52, 334, 41, 3, 2)

    draw_wood(322, 65, 304, 62, 4, 3)
    draw_wood(304, 62, 286, 55, 3, 2)
    draw_wood(286, 55, 274, 52, 2, 1)
    draw_wood(300, 60, 294, 54, 2, 1)
    draw_wood(323, 55, 310, 49, 3, 2)
    draw_wood(310, 49, 302, 44, 2, 1)

    if stage >= 4:
        draw_wood(336, 72, 354, 63, 4, 3)
        draw_wood(354, 63, 372, 55, 3, 2)
        draw_wood(372, 55, 384, 50, 2, 1, jin=True)
        draw_wood(358, 61, 364, 53, 2, 1)
        draw_wood(331, 46, 344, 40, 2, 1)
        draw_wood(326, 49, 318, 43, 2, 1)
        if sub_prog >= 0.35:
            draw_wood(342, 67, 348, 57, 2, 1)
        if sub_prog >= 0.7:
            draw_wood(290, 58, 280, 62, 2, 1)

    if stage >= 5:
        draw_wood(382, 51, 394, 46, 2, 1)
        draw_wood(274, 52, 262, 48, 2, 1)


def _draw_canopy(canopy, stage, sub_prog, this_week):
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
        add_lobe(276, 52, 18, 7)
        add_lobe(292, 50, 14, 6)
        add_lobe(306, 42, 16, 7)
        add_lobe(324, 34, 18, 8)
        add_lobe(338, 32, 20, 8)
        add_lobe(350, 37, 14, 6)
        add_lobe(354, 48, 16, 7)
        add_lobe(374, 52, 18, 7)
        add_lobe(388, 50, 12, 5)

        if stage >= 5 or sub_prog >= 0.45:
            add_lobe(264, 55, 11, 5)
        if stage >= 5 or sub_prog >= 0.75:
            add_lobe(394, 46, 12, 5)

        tendrils = [(270, 59), (282, 59), (302, 49), (336, 40), (370, 59), (382, 57)]
        for tx, ty in tendrils[:3 + int(sub_prog * 3)]:
            canopy.put(tx, ty, "#8B1E3F")
            canopy.put(tx, ty + 1, "#D9366B")
            canopy.put(tx, ty + 2, "#FF7AA3")

        floret_pts = [
            (334, 28, True), (322, 31, True), (346, 33, False), (276, 48, True),
            (304, 39, True), (374, 48, True), (354, 44, False), (290, 47, False),
            (386, 47, True), (330, 36, False),
        ]
        for fx, fy, br in floret_pts[:min(len(floret_pts), max(4, this_week // 3 + 4))]:
            add_floret(fx, fy, br)


def render_hero_svg(stats, views_count, username):
    """Render 900x236 Hero Card SVG with a high-detail 2x2 pixel-art Wine-Blossom Bonsai & minimal inline view count."""
    commits = stats["commits"]
    this_week = stats["this_week"]
    streak = stats["current_streak"]
    best_day = stats["best_day"]

    stage, stage_roman, sub_prog = _growth_stage(commits)

    base = PixelCanvas(size=2)
    canopy = PixelCanvas(size=2)

    _draw_sky_and_ground(base, stats["rank"], stats["repos"], this_week)
    lantern_fx = _draw_pot_and_lantern(base, stage)
    _draw_bonsai_wood(base, stage, sub_prog)
    _draw_canopy(canopy, stage, sub_prog, this_week)

    petals_markup = ""
    if streak > 0:
        petals = [
            (552, 118, "#FF5C8D", "p1"), (612, 98, "#B8325A", "p2"),
            (668, 84, "#FFE0EA", "p3"), (748, 114, "#FF5C8D", "p4"),
            (708, 102, "#B8325A", "p1"), (584, 122, "#FF7AA3", "p3"),
            (768, 110, "#B8325A", "p2"), (644, 92, "#FF5C8D", "p4"),
            (536, 116, "#B8325A", "p1"), (732, 96, "#FFE0EA", "p3"),
        ]
        petals_markup = "\n    ".join(px_rect(x, y, c, cls, size=2) for x, y, c, cls in petals)

    fireflies_markup = ""
    if streak >= 7 or best_day >= 20:
        flies = [
            (516, 92, "#FFE0EA", "ff1"), (640, 48, "#FFA3BF", "ff2"),
            (796, 86, "#FFE0EA", "ff1"), (716, 60, "#FFA3BF", "ff2"),
        ]
        fireflies_markup = "\n    ".join(px_rect(x, y, c, cls, size=2) for x, y, c, cls in flies)

    formatted_views = f"{views_count:06,d}"
    lead_zeros = len(formatted_views) - len(str(views_count))
    views_inner = f'<tspan fill="#5C1029">{formatted_views[:lead_zeros]}</tspan><tspan fill="#E8E6E8">{formatted_views[lead_zeros:]}</tspan>'
    canopy_cls = ' class="canopy-sway"' if streak > 0 else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 236" width="900" height="236" fill="none" role="img" aria-label="{username} — Hero Card &amp; Profile Telemetry">
  <title>{username} — Pixel Wine-Blossom Bonsai &amp; Profile Telemetry</title>
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
      .claude-serif {{ font-family: {CLAUDE_SERIF_FONT}; }}
      .claude-sans {{ font-family: {CLAUDE_SANS_FONT}; }}
      @keyframes liveBreath {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
      @keyframes canopySway {{ 0%, 100% {{ transform: translateX(0px); }} 50% {{ transform: translateX(2px); }} }}
      @keyframes lanternFlicker {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.55; }} }}
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

  <!-- Minimal Inline Profile Views Indicator -->
  <g transform="translate(868, 32)">
    <circle cx="-94" cy="-4" r="2.6" fill="{THEME['wine_glow']}" class="live-dot"/>
    <text id="profile-views-count" x="-36" y="0" text-anchor="end" class="claude-serif" font-size="13" font-weight="700" font-variant-numeric="tabular-nums">{views_inner}</text>
    <text x="0" y="0" text-anchor="end" class="claude-sans" font-size="11.5" fill="{THEME['text_muted']}">views</text>
  </g>

  <!-- Left Zone: Minimal Username & Contact -->
  <g transform="translate(44, 82)">
    <text x="0" y="28" class="claude-serif" font-size="44" font-weight="700" fill="{THEME['text_main']}">{username} <tspan class="claude-sans" font-size="14" font-weight="500" fill="{THEME['wine_glow']}">/ r41n</tspan></text>
    <line x1="0" y1="46" x2="260" y2="46" stroke="url(#accentRule)" stroke-width="1.5"/>
    <text x="0" y="74" class="claude-sans" font-size="12.5" fill="{THEME['text_muted']}">0xraiven@proton.me <tspan fill="#3D3545"> · </tspan> github.com/0xraiven</text>
  </g>

  <!-- Subtle Vertical Divider -->
  <line x1="458" y1="22" x2="458" y2="214" stroke="url(#vDivider)" stroke-width="1"/>

  <!-- Right Zone: High-Detail 2x2 Pixel-Art Bonsai -->
  <g shape-rendering="crispEdges">
    {base.to_svg()}
    {"\n    ".join(lantern_fx)}
    <g{canopy_cls}>
      {canopy.to_svg()}
    </g>
    {petals_markup}
    {fireflies_markup}
  </g>

  <text x="868" y="220" text-anchor="end" class="claude-sans" font-size="10" font-weight="500" fill="{THEME['text_dim']}">Stage {stage_roman} · {commits:,} commits</text>
</svg>"""
