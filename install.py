#!/usr/bin/env python3
"""Install (or remove) Claude Lantern for Claude Code.

    python install.py            install, then switch to Hal
    python install.py john       install, then switch to John (or guy, default)
    python install.py --uninstall

Installs into ~/.claude/lantern, adds the /preset command, and points
~/.claude/settings.json at the statusline and the lantern-wave plugin.
settings.json is backed up to settings.json.lantern-backup first, and
--uninstall restores that backup.
"""
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.join(os.path.expanduser("~"), ".claude")
TARGET = os.path.join(CLAUDE, "lantern")
PLUGIN = os.path.join(TARGET, "plugin", "lantern-wave")
SETTINGS = os.path.join(CLAUDE, "settings.json")
BACKUP = SETTINGS + ".lantern-backup"
COMMAND = os.path.join(CLAUDE, "commands", "preset.md")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_settings(settings):
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def install(preset):
    # Keep the user's active preset across reinstalls.
    active = os.path.join(TARGET, "active")
    kept = open(active, encoding="utf-8").read() if os.path.exists(active) else None

    if os.path.isdir(TARGET):
        shutil.rmtree(TARGET)
    shutil.copytree(os.path.join(REPO, "lantern"), TARGET,
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(REPO, "plugin", "lantern-wave"), PLUGIN,
                    ignore=shutil.ignore_patterns("types", "tsconfig.json"))
    if kept:
        with open(active, "w", encoding="utf-8") as f:
            f.write(kept)

    os.makedirs(os.path.dirname(COMMAND), exist_ok=True)
    shutil.copyfile(os.path.join(REPO, "commands", "preset.md"), COMMAND)

    if os.path.exists(SETTINGS) and not os.path.exists(BACKUP):
        shutil.copyfile(SETTINGS, BACKUP)
    settings = load_settings()
    python = sys.executable.replace("\\", "/")
    statusline = os.path.join(TARGET, "statusline.py").replace("\\", "/")
    settings["statusLine"] = {"type": "command", "command": f'"{python}" "{statusline}"', "padding": 0}

    env = settings.setdefault("env", {})
    dirs = [d for d in env.get("CLAUDE_CODE_PLUGIN_DIRS", "").split(os.pathsep) if d]
    plugin_dir = PLUGIN.replace("\\", "/")
    if plugin_dir not in dirs:
        dirs.append(plugin_dir)
    env["CLAUDE_CODE_PLUGIN_DIRS"] = os.pathsep.join(dirs)
    save_settings(settings)

    subprocess.run([sys.executable, os.path.join(TARGET, "preset.py"), kept.strip() if kept else preset], check=True)
    print(f"Installed to {TARGET}. Restart claude to load the plugin, colors and spinner words.")


def uninstall():
    if os.path.exists(BACKUP):
        shutil.move(BACKUP, SETTINGS)
        print("Restored settings.json from backup.")
    for path in (TARGET,):
        if os.path.isdir(path):
            shutil.rmtree(path)
    if os.path.exists(COMMAND):
        os.remove(COMMAND)
    themes = os.path.join(CLAUDE, "themes")
    for name in ("hal.json", "john.json", "guy.json"):
        p = os.path.join(themes, name)
        if os.path.exists(p):
            os.remove(p)
    print("Claude Lantern removed. Restart claude.")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "hal"
    uninstall() if arg == "--uninstall" else install(arg)
