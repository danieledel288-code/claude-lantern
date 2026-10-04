#!/usr/bin/env python3
"""Claude Code statusline: mood, model, dir/git, plan usage.
Labels/colors come from the active preset (see preset.py and presets/).
Reads the session JSON Claude Code passes on stdin. Must never crash or
block — any error falls back to a minimal line so the bar never disappears.
"""
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

FALLBACK_THEME = {
    "colors": None,
    "moods": {
        "critical": "🥴 exhausted, /handoff soon",
        "warning": "😵 losing attention",
        "starting": "🐾 waking up",
        "blasting": "🔥 on fire",
        "busy": "😀 vibing",
        "working": "🙂 working",
        "idle": "💤 idle",
    },
    "usage": {"show_remaining": False, "five_hour": "5h", "seven_day": "wk", "cost_suffix": "session"},
    "labels": {"model": "", "dir": ""},
    "corner_art": None,
}


def load_theme():
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        name = open(os.path.join(here, "active"), encoding="utf-8").read().strip()
        with open(os.path.join(here, "presets", name + ".json"), encoding="utf-8") as f:
            theme = json.load(f)
        return {**FALLBACK_THEME, **theme}
    except Exception:
        return FALLBACK_THEME


ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def visible_width(text):
    # Terminal cells, not len(): emoji are 2 wide, and a VS16 (U+FE0F)
    # promotes the preceding narrow symbol (e.g. the warning sign) to 2.
    text = ANSI_RE.sub("", text)
    width = 0
    for i, ch in enumerate(text):
        if ch == "\ufe0f" or unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        elif i + 1 < len(text) and text[i + 1] == "\ufe0f":
            width += 2
        else:
            width += 1
    return width


def hud_with_art(segments, art, color, reset):
    # HUD layout: one segment per row on the left, art right-aligned on the
    # same rows. Every row starts with text, so nothing depends on leading
    # whitespace surviving. COLUMNS is set by Claude Code (stdout is a pipe,
    # so tput/get_terminal_size can't see the terminal). Returns None when
    # the terminal is too narrow, and the caller falls back to one line.
    try:
        cols = int(os.environ.get("COLUMNS", ""))
    except ValueError:
        return None
    # Blank rows start with a braille blank (U+2800), not a space, so the
    # row never begins with whitespace that could be trimmed.
    rows = list(segments) + ["⠀"] * (len(art) - len(segments))
    art_width = max(visible_width(a) for a in art)
    right_margin = 4  # Claude Code indents the row; leave room so it never wraps
    text_width = max(visible_width(r) for r in rows)
    art_col = cols - right_margin - art_width
    if art_col - text_width < 3:
        return None
    out = []
    for row, art_row in zip(rows, art):
        pad = " " * (art_col - visible_width(row))
        out.append(f"{color}{row}{pad}{art_row}{reset}")
    return "\n".join(out)


def safe_git_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=1,
        )
        if out.returncode == 0:
            branch = out.stdout.strip()
            if branch and branch != "HEAD":
                return branch
    except Exception:
        pass
    return None


def pet_mood(moods, cost_usd, duration_ms, lines_changed, context_pct):
    # Context fill takes priority over activity — a session losing coherence
    # matters more than how much work it's done.
    if isinstance(context_pct, (int, float)):
        if context_pct >= 90:
            return f"{moods['critical']} ({context_pct:.0f}%)"
        if context_pct >= 70:
            return f"{moods['warning']} ({context_pct:.0f}%)"

    # Otherwise: passive mood from this session's own activity so far.
    if duration_ms < 60_000 and cost_usd < 0.01 and lines_changed == 0:
        return moods["starting"]
    if lines_changed > 200 or cost_usd > 2:
        return moods["blasting"]
    if lines_changed > 50 or cost_usd > 0.5:
        return moods["busy"]
    if lines_changed > 0 or cost_usd > 0:
        return moods["working"]
    return moods["idle"]


RATE_CACHE = os.path.join(os.path.expanduser("~"), ".claude", "statusline_rate_limits.json")


def with_cached_rate_limits(rate_limits):
    # rate_limits only arrives after a session's first API response, so a
    # fresh session would show "$0.00 spent". Remember the last real reading
    # and reuse it until each window's resets_at passes.
    if rate_limits:
        try:
            with open(RATE_CACHE, "w", encoding="utf-8") as f:
                json.dump(rate_limits, f)
        except Exception:
            pass
        return rate_limits
    try:
        with open(RATE_CACHE, encoding="utf-8") as f:
            cached = json.load(f)
    except Exception:
        return None
    now = time.time()
    fresh = {}
    for key, window in cached.items():
        resets_at = (window or {}).get("resets_at")
        if isinstance(resets_at, (int, float)) and resets_at > now:
            fresh[key] = window
    return fresh or None


def format_usage(labels, rate_limits, cost_usd):
    # Real plan-quota % (5h session window, 7-day window) when Claude Code
    # exposes it. Falls back to the notional $ cost figure on older Claude
    # Code versions or the known Max/OAuth bug where rate_limits is absent
    # (github.com/anthropics/claude-code/issues/40094).
    rate_limits = rate_limits or {}
    windows = [
        (labels["five_hour"], (rate_limits.get("five_hour") or {}).get("used_percentage")),
        (labels["seven_day"], (rate_limits.get("seven_day") or {}).get("used_percentage")),
    ]

    parts = []
    for label, used in windows:
        if isinstance(used, (int, float)):
            # Some themes show what's left (ring power) instead of what's used.
            pct = max(0, 100 - used) if labels["show_remaining"] else used
            parts.append(f"{label} {pct:.0f}%")

    if parts:
        return parts

    cost_part = "<$0.01" if 0 < cost_usd < 0.01 else f"${cost_usd:.2f}"
    return [f"{cost_part} {labels['cost_suffix']}"]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    model = data.get("model", {}) or {}
    model_name = model.get("display_name") or model.get("id") or "claude"

    workspace = data.get("workspace", {}) or {}
    cwd = workspace.get("current_dir") or data.get("cwd") or os.getcwd()
    dir_name = os.path.basename(os.path.normpath(cwd)) or cwd

    cost = data.get("cost", {}) or {}
    cost_usd = float(cost.get("total_cost_usd") or 0)
    duration_ms = float(cost.get("total_duration_ms") or 0)
    lines_added = int(cost.get("total_lines_added") or 0)
    lines_removed = int(cost.get("total_lines_removed") or 0)
    lines_changed = lines_added + lines_removed

    branch = safe_git_branch(cwd)
    dir_part = f"{dir_name} ({branch})" if branch else dir_name

    context_window = data.get("context_window") or {}
    context_pct = context_window.get("used_percentage")

    theme = load_theme()
    mood = pet_mood(theme["moods"], cost_usd, duration_ms, lines_changed, context_pct)

    usage_parts = format_usage(theme["usage"], with_cached_rate_limits(data.get("rate_limits")), cost_usd)
    usage_part = "  ".join(usage_parts)

    labels = theme["labels"]
    model_part = f"{labels.get('model', '')}{model_name}"
    dir_part = f"{labels.get('dir', '')}{dir_part}"

    colors = theme.get("colors")
    if colors:
        text, dim, reset = f"\033[{colors['text']}m", f"\033[{colors['separator']}m", "\033[0m"
        sep = f"{dim}  │  {text}"
        line = f"{text}{mood}{sep}{model_part}{sep}{dir_part}{sep}{usage_part}{reset}"
    else:
        text, reset, sep = "", "", "  │  "
        line = f"{mood}  │  {model_part}  │  {dir_part}  │  {usage_part}"

    art = theme.get("corner_art")
    if art:
        # Three compact rows: status, where/who, how much ring is left.
        rows = [mood, f"{model_part}{sep}{dir_part}", sep.join(usage_parts)]
        hud = hud_with_art(rows, art, text, reset)
        if hud:
            line = hud
    print(line)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("claude")
