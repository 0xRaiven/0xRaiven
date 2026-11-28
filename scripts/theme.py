"""Shared 0xraiven color palette and Claude-inspired typography stacks."""

CLAUDE_SERIF_FONT = (
    "'Copernicus', 'Tiempos Text', 'Charter', 'Iowan Old Style', Georgia, 'Times New Roman', serif"
)
CLAUDE_SANS_FONT = (
    "'Anthropic Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)

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
    ],
}
