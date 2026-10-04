#!/usr/bin/env python3
"""Set up Claude Lantern, switch presets, or remove it.

    setup.py --plugin [preset]     used by the plugin's /lantern:preset skill
    setup.py --manual [preset]     used by the repo's install.py
    setup.py --manual --uninstall

Plugins can't set the statusline, spinner words or welcome text, so this
copies the runtime (statusline + presets) to ~/.claude/lantern, where it
survives plugin updates, and writes those settings. In plugin mode the
color themes and the construct animation come from the plugin itself; in
manual mode they're installed here too.

settings.json is backed up to settings.json.lantern-backup on first run, and
--uninstall restores it.
"""
import json
import os
import shutil
import subprocess
import sys

PLUGIN = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.join(os.path.expanduser("~"), ".claude")
TARGET = os.path.join(CLAUDE, "lantern")
SETTINGS = os.path.join(CLAUDE, "settings.json")
BACKUP = SETTINGS + ".lantern-backup"
# Manual mode loads a copy of this plugin directory as a --plugin-dir.
MANUAL_PLUGIN = os.path.join(TARGET, "plugin")
LEGACY_PLUGIN = os.path.join(TARGET, "plugin", "lantern-wave")
COMMAND = os.path.join(CLAUDE, "commands", "preset.md")


def fwd(path):
    return path.replace("\\", "/")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_settings(settings):
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def plugin_dirs(settings):
    env = settings.get("env", {})
    return [d for d in env.get("CLAUDE_CODE_PLUGIN_DIRS", "").split(os.pathsep) if d]


def set_plugin_dirs(settings, dirs):
    env = settings.setdefault("env", {})
    if dirs:
        env["CLAUDE_CODE_PLUGIN_DIRS"] = os.pathsep.join(dirs)
    else:
        env.pop("CLAUDE_CODE_PLUGIN_DIRS", None)
        if not env:
            settings.pop("env", None)


def install(mode, preset):
    active_file = os.path.join(TARGET, "active")
    kept = open(active_file, encoding="utf-8").read().strip() if os.path.exists(active_file) else None

    # Fresh copy of the runtime, keeping the user's active preset.
    if os.path.isdir(TARGET):
        shutil.rmtree(TARGET)
    shutil.copytree(os.path.join(PLUGIN, "lantern"), TARGET, ignore=shutil.ignore_patterns("__pycache__"))
    with open(os.path.join(TARGET, "mode"), "w", encoding="utf-8") as f:
        f.write(mode)

    if os.path.exists(SETTINGS) and not os.path.exists(BACKUP):
        shutil.copyfile(SETTINGS, BACKUP)
    settings = load_settings()
    statusline = fwd(os.path.join(TARGET, "statusline.py"))
    settings["statusLine"] = {"type": "command", "command": f'"{fwd(sys.executable)}" "{statusline}"', "padding": 0}

    ours = {fwd(MANUAL_PLUGIN), fwd(LEGACY_PLUGIN)}
    dirs = [d for d in plugin_dirs(settings) if fwd(d) not in ours]
    if mode == "manual":
        shutil.copytree(PLUGIN, MANUAL_PLUGIN, ignore=shutil.ignore_patterns("__pycache__", "lantern", "setup.py", "skills", "tsconfig.json", "types"))
        dirs.append(fwd(MANUAL_PLUGIN))
        os.makedirs(os.path.dirname(COMMAND), exist_ok=True)
        repo_command = os.path.join(os.path.dirname(PLUGIN), "commands", "preset.md")
        if os.path.exists(repo_command):
            shutil.copyfile(repo_command, COMMAND)
    # In plugin mode the plugin provides the animation; drop any manual copy
    # so it isn't loaded twice.
    set_plugin_dirs(settings, dirs)
    save_settings(settings)

    choice = preset or kept or "hal"
    subprocess.run([sys.executable, os.path.join(TARGET, "preset.py"), choice], check=True)
    subprocess.run([sys.executable, os.path.join(TARGET, "preset.py"), "list"])


def uninstall():
    if os.path.exists(BACKUP):
        shutil.move(BACKUP, SETTINGS)
        print("Restored settings.json from backup.")
    if os.path.isdir(TARGET):
        shutil.rmtree(TARGET)
    if os.path.exists(COMMAND):
        os.remove(COMMAND)
    for name in ("hal.json", "john.json", "guy.json"):
        p = os.path.join(CLAUDE, "themes", name)
        if os.path.exists(p):
            os.remove(p)
    print("Claude Lantern removed. Restart claude. (Plugin users: also run /plugin uninstall lantern.)")


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = "plugin" if "--plugin" in args else "manual"
    rest = [a for a in args if not a.startswith("--")]
    if "--uninstall" in args:
        uninstall()
    else:
        install(mode, rest[0] if rest else None)
