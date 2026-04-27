#!/usr/bin/env python3
"""
update_theme.py — Daily theme rotation for schaefer.io

Reads theme.json (the curated variation space) and theme-history.json (recent
selections). Asks Claude to pick today's palette + font pairing, avoiding
recent repeats. Writes the result to theme.css and appends to history.

Designed to be idempotent and safe: if the API call fails, the script exits
non-zero without modifying any files.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).resolve().parent.parent
THEME_JSON = REPO_ROOT / "theme.json"
THEME_CSS = REPO_ROOT / "theme.css"
HISTORY_JSON = REPO_ROOT / "theme-history.json"

# How many recent selections to avoid repeating
HISTORY_LOOKBACK = 5

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 400


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open() as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    with path.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def build_prompt(theme_data: dict, history: list[dict]) -> str:
    palette_names = [p["name"] for p in theme_data["palettes"]]
    font_names = [f["name"] for f in theme_data["fonts"]]

    recent = history[-HISTORY_LOOKBACK:] if history else []
    recent_lines = (
        "\n".join(
            f"  - {h['date']}: palette={h['palette']}, font={h['font']}"
            for h in recent
        )
        or "  (none yet)"
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d (%A)")

    return f"""You are picking the daily aesthetic theme for a minimalist personal website.

Today is {today}.

Available palettes: {", ".join(palette_names)}
Available fonts: {", ".join(font_names)}

Recent selections (most recent last):
{recent_lines}

Pick ONE palette and ONE font for today. Rules:
- Do NOT pick the same palette as any of the last {HISTORY_LOOKBACK} days.
- Do NOT pick the same font as the last 2 days.
- Vary the mood: don't pick three dark palettes in a row, alternate light/dark when reasonable.
- Aim for combinations that feel coherent (e.g., serif fonts pair well with warm paper-like palettes).

Respond with ONLY a JSON object on a single line, no markdown, no commentary:
{{"palette": "<palette_name>", "font": "<font_name>", "reasoning": "<one short sentence>"}}"""


def call_claude(prompt: str) -> dict:
    client = anthropic.Anthropic()  # Reads ANTHROPIC_API_KEY from env
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        block.text for block in message.content if block.type == "text"
    ).strip()

    # Strip code fences if Claude added them despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    return json.loads(text)


def render_css(palette: dict, font: dict, palette_name: str, font_name: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    import_line = (
        f"@import url('{font['import_url']}');\n\n" if font.get("import_url") else ""
    )
    return f"""/*
 * theme.css — auto-rotated daily by .github/workflows/daily-theme.yml
 * Theme: "{palette_name}" + "{font_name}"
 * Last updated: {today} UTC
 *
 * This file is overwritten by the automated daily theme rotation.
 * To change which themes are eligible, edit theme.json (not this file).
 */

{import_line}:root {{
    /* Typography */
    --font-heading: {font['heading_stack']};
    --font-body: {font['body_stack']};

    /* Page */
    --color-page-bg: {palette['page_bg']};
    --color-text: {palette['text']};

    /* Card */
    --color-card-bg: {palette['card_bg']};
    --color-card-border: {palette['card_border']};
    --color-card-shadow: {palette['card_shadow']};

    /* Avatar */
    --color-avatar-bg: {palette['avatar_bg']};
    --color-avatar-bg-hover: {palette['avatar_bg_hover']};
    --color-avatar-border: {palette['avatar_border']};
    --color-avatar-border-hover: {palette['avatar_border_hover']};

    /* Text hierarchy */
    --color-heading: {palette['heading']};
    --color-subtitle: {palette['subtitle']};
    --color-body: {palette['body']};
    --color-muted: {palette['muted']};

    /* Links */
    --color-link: {palette['link']};
    --color-link-hover: {palette['link_hover']};
    --color-link-border: {palette['link_border']};
    --color-link-border-hover: {palette['link_border_hover']};
    --color-link-bg-hover: {palette['link_bg_hover']};

    /* Decorative */
    --color-floating: {palette['floating']};
}}
"""


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    theme_data = load_json(THEME_JSON, default=None)
    if theme_data is None:
        print(f"ERROR: {THEME_JSON} not found", file=sys.stderr)
        return 1

    history = load_json(HISTORY_JSON, default=[])

    prompt = build_prompt(theme_data, history)
    print("Calling Claude...")
    try:
        choice = call_claude(prompt)
    except Exception as e:
        print(f"ERROR calling Claude: {e}", file=sys.stderr)
        return 1

    palette_name = choice.get("palette")
    font_name = choice.get("font")
    reasoning = choice.get("reasoning", "")

    palette = next(
        (p for p in theme_data["palettes"] if p["name"] == palette_name), None
    )
    font = next((f for f in theme_data["fonts"] if f["name"] == font_name), None)

    if palette is None or font is None:
        print(
            f"ERROR: Claude returned unknown palette={palette_name} or font={font_name}",
            file=sys.stderr,
        )
        return 1

    css = render_css(palette, font, palette_name, font_name)
    THEME_CSS.write_text(css)

    history.append(
        {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "palette": palette_name,
            "font": font_name,
            "reasoning": reasoning,
        }
    )
    # Keep history bounded so the file doesn't grow forever
    history = history[-100:]
    save_json(HISTORY_JSON, history)

    print(f"Updated theme.css: palette={palette_name}, font={font_name}")
    print(f"Reasoning: {reasoning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
