#!/usr/bin/env python3
"""CLI entrypoint for generating the 3D contribution graph and Pixel Bonsai hero card."""

import datetime
import os
import re
import sys

from github_client import calculate_stats, fetch_github_data
from render_contrib import render_contrib_svg
from render_hero import read_existing_views, render_hero_svg

USERNAME = os.environ.get("GH_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "0xraiven"
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "assets/contribution-3d.svg")
HERO_PATH = os.environ.get("HERO_PATH", "assets/hero-card.svg")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def _update_readme_cache_busters(readme_path="README.md"):
    if not os.path.exists(readme_path):
        return
    with open(readme_path, "r", encoding="utf-8") as rf:
        readme = rf.read()
    timestamp = int(datetime.datetime.now().timestamp())
    new_readme = re.sub(
        r"assets/contribution-3d\.svg(?:\?v=[^\s\"'>]+)?",
        f"assets/contribution-3d.svg?v={timestamp}",
        readme,
    )
    new_readme = re.sub(
        r"assets/hero-card\.svg(?:\?v=[^\s\"'>]+)?",
        f"assets/hero-card.svg?v={timestamp}",
        new_readme,
    )
    if new_readme != readme:
        with open(readme_path, "w", encoding="utf-8") as wf:
            wf.write(new_readme)
        print(f"Updated {readme_path} cache-buster query params to ?v={timestamp}")


def main():
    if not GITHUB_TOKEN:
        sys.exit("Error: GITHUB_TOKEN environment variable is required to fetch real GitHub data.")

    print(f"Fetching live GitHub contributions & metrics for {USERNAME} via GraphQL...")
    raw_data = fetch_github_data(GITHUB_TOKEN, USERNAME)
    print("Successfully fetched live GitHub data!")

    cal = raw_data["calendar"]
    stats = calculate_stats(cal, raw_data)

    contrib_svg = render_contrib_svg(cal, stats, USERNAME)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(contrib_svg)
    print(f"Generated 3D contribution graph at {OUTPUT_PATH}")

    existing_views = read_existing_views(HERO_PATH)
    hero_svg = render_hero_svg(stats, existing_views, USERNAME)
    os.makedirs(os.path.dirname(HERO_PATH), exist_ok=True)
    with open(HERO_PATH, "w", encoding="utf-8") as hf:
        hf.write(hero_svg)
    print(f"Generated Pixel Bonsai hero card at {HERO_PATH} (views={existing_views})")

    try:
        _update_readme_cache_busters()
    except Exception as e:
        print(f"README cache-buster update note: {e}")


if __name__ == "__main__":
    main()
