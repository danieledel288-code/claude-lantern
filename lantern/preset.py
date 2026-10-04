#!/usr/bin/env python3
"""Switch Claude Code themes. Usage: theme.py [list | <name>]

A preset lives in presets/<name>.json next to this file. Switching writes
the name to ./active (read by statusline.py and the lantern-wave plugin), syncs its
spinnerVerbs into ~/.claude/settings.json (null = Claude Code defaults), and
sets settings "theme" to its cliTheme. Custom CLI color themes in cc-themes/
are copied into ~/.claude/themes/ so Claude Code can find them.
"""
import json
import os
import shutil
import sys

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
THEMES_DIR = os.path.join(HERE, "presets")
ACTIVE_FILE = os.path.join(HERE, "active")
SETTINGS = os.path.join(HOME, ".claude", "settings.json")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def available():
    return sorted(f[:-5] for f in os.listdir(THEMES_DIR) if f.endswith(".json"))


def active():
    try:
        return open(ACTIVE_FILE, encoding="utf-8").read().strip() or "default"
    except OSError:
        return "default"


def install_cc_themes():
    src = os.path.join(HERE, "cc-themes")
    dst = os.path.join(HOME, ".claude", "themes")
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        if f.endswith(".json"):
            shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))


def list_themes():
    current = active()
    for name in available():
        with open(os.path.join(THEMES_DIR, name + ".json"), encoding="utf-8") as f:
            desc = json.load(f).get("description", "")
        marker = "*" if name == current else " "
        print(f"{marker} {name:<16} {desc}")


def set_theme(name):
    if name not in available():
        print(f"No theme '{name}'. Available: {', '.join(available())}")
        sys.exit(1)
    with open(os.path.join(THEMES_DIR, name + ".json"), encoding="utf-8") as f:
        theme = json.load(f)

    with open(SETTINGS, encoding="utf-8") as f:
        settings = json.load(f)
    verbs = theme.get("spinnerVerbs")
    if verbs:
        settings["spinnerVerbs"] = {"mode": "replace", "verbs": verbs}
    else:
        settings.pop("spinnerVerbs", None)
    # Startup text on the welcome screen (the Lantern oath); removed for
    # presets without one.
    if theme.get("announcement"):
        settings["companyAnnouncements"] = [theme["announcement"]]
    else:
        settings.pop("companyAnnouncements", None)
    if theme.get("cliTheme"):
        install_cc_themes()
        settings["theme"] = theme["cliTheme"]
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
        f.write(name)
    print(f"Theme set to '{name}'. Colors + statusline update now; spinner verbs apply in the next session.")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "list"
    list_themes() if arg == "list" else set_theme(arg)
