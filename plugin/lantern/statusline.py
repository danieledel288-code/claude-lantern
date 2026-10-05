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


BLANK = "\u2800"  # braille blank: looks like a space but is never trimmed


def ring_left(art, rows, color, reset):
    # The emblem sits on the left like a logo with one info row beside each
    # art row. Leading spaces in the art become braille blanks so a row never
    # starts with whitespace that could be trimmed. No terminal width needed.
    rows = list(rows) + [""] * (len(art) - len(rows))
    art_width = max(visible_width(a) for a in art)
    out = []
    for art_row, row in zip(art, rows):
        stripped = art_row.lstrip(" ")
        art_cell = BLANK * (len(art_row) - len(stripped)) + stripped
        pad = " " * (art_width - visible_width(art_row) + 3)
        out.append(f"{color}{art_cell}{reset}{pad}{row}")
    return "\n".join(out)


def spaced(name):
    # "HAL JORDAN" -> "H A L   J O R D A N": reads as a title, not a label.
    return "   ".join(" ".join(word) for word in name.split())


def with_right_text(block, texts, first_row=0):
    # Right-align short texts on the block's rows, starting at first_row and
    # never on the last row (Claude Code trims the right end of the final
    # status row). Needs COLUMNS, which Claude Code sets; skipped otherwise
    # or when a row has no room.
    try:
        cols = int(os.environ.get("COLUMNS", ""))
    except ValueError:
        return block
    lines = block.split("\n")
    for i, text in enumerate(texts):
        j = first_row + i
        if j >= len(lines) - 1:
            break
        end = cols - 4  # Claude Code indents the row; keep clear of the edge
        gap = end - visible_width(lines[j]) - visible_width(text)
        if gap < 3:
            return block
        lines[j] = f"{lines[j]}{' ' * gap}{text}"
    return "\n".join(lines)


def charge_bar(pct, width=10):
    filled = max(0, min(width, round(pct / 100 * width)))
    return "\u25b0" * filled + "\u25b1" * (width - filled)


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


def format_usage(labels, rate_limits, cost_usd, paint=None, bar_width=10):
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
            if paint:
                bar = f"{charge_bar(pct, bar_width)} " if bar_width else ""
                parts.append(paint(label, f"{bar}{pct:.0f}%"))
            else:
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
    dir_part_plain = dir_part
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
        dim = f"\033[{colors['separator']}m" if colors else ""

        def paint(label, value):
            return f"{dim}{label}{reset} {text}{value}{reset}"

        names = [labels.get("model", "").strip(" :") or "model", labels.get("dir", "").strip(" :") or "dir"]
        width = max(len(n) for n in names)
        # Narrow panes (split screen) cut off the bottom row, so shrink the
        # charge bars until the row fits: full, half, then percentages only.
        try:
            room = int(os.environ.get("COLUMNS", "")) - 6 - max(visible_width(a) for a in art) - 3
        except ValueError:
            room = None
        limits = with_cached_rate_limits(data.get("rate_limits"))
        for bar_width in (10, 5, 0):
            bars = format_usage(theme["usage"], limits, cost_usd, paint, bar_width)
            if room is None or visible_width("  ".join(bars)) <= room:
                break
        rows = [
            f"{text}{mood}{reset}",
            paint(names[0].ljust(width), model_name),
            paint(names[1].ljust(width), dir_part_plain),
            "  ".join(bars),
        ]
        line = ring_left(art, rows, text, reset)
        if theme.get("name"):
            label = [f"\033[1m{text}{spaced(theme['name'])}{reset}", f"{dim}GREEN LANTERN CORPS{reset}"]
            fitted = with_right_text(line, label, first_row=1)
            if fitted == line:
                # Spaced title didn't fit; try the plain name before giving up.
                label[0] = f"[1m{text}{theme['name']}{reset}"
                fitted = with_right_text(line, label, first_row=1)
            if fitted == line:
                fitted = with_right_text(line, label[:1], first_row=1)
            line = fitted
    print(line)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("claude")
