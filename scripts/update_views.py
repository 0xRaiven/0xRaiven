#!/usr/bin/env python3
"""Fetch latest Komarev profile view count and update assets/hero-card.svg & README.md."""

import os
import re
import urllib.request

USERNAME = os.environ.get("GH_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "0xraiven"
HERO_PATH = os.environ.get("HERO_PATH", "assets/hero-card.svg")
README_PATH = os.environ.get("README_PATH", "README.md")


def fetch_view_count(username):
    url = f"https://komarev.com/ghpvc/?username={username}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8")
    matches = re.findall(r">([0-9,]+)<", html)
    if not matches:
        return None
    return int(matches[-1].replace(",", ""))


def main():
    try:
        count_int = fetch_view_count(USERNAME)
        if count_int is None:
            print("No view count matched in Komarev response.")
            return

        formatted = f"{count_int:06,d}"
        print(f"Fetched count: {count_int} -> {formatted}")

        with open(HERO_PATH, "r", encoding="utf-8") as f:
            svg = f.read()

        lead_zeros = len(formatted) - len(str(count_int))
        pattern = r'(<text id="profile-views-count"[^>]*>).*?(</text>)'
        new_inner = (
            f'<tspan fill="#5C1029">{formatted[:lead_zeros]}</tspan>'
            f'<tspan fill="#E8E6E8">{formatted[lead_zeros:]}</tspan>'
        )
        new_svg = re.sub(pattern, rf"\g<1>{new_inner}\g<2>", svg)

        with open(HERO_PATH, "w", encoding="utf-8") as f:
            f.write(new_svg)
        print(f"Updated {HERO_PATH} successfully")

        if os.path.exists(README_PATH):
            with open(README_PATH, "r", encoding="utf-8") as f:
                readme = f.read()
            new_readme = re.sub(
                r"assets/hero-card\.svg(?:\?v=[^\s\"'>]+)?",
                f"assets/hero-card.svg?v={count_int}",
                readme,
            )
            with open(README_PATH, "w", encoding="utf-8") as f:
                f.write(new_readme)
            print(f"Updated {README_PATH} cache-buster query param successfully")
    except Exception as e:
        print(f"Update skipped or failed: {e}")


if __name__ == "__main__":
    main()
