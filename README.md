# Claude Lantern

A Green Lantern theme for [Claude Code](https://code.claude.com). Pick your Lantern and the terminal changes to match:

- **Color theme**: spinner, mascot, prompt border and accents in your Lantern's color
- **Spinner words**: Hal is "Flying by the seat of my pants…", John is "Building it bolt by bolt…", Guy is "Out-yelling Hal…"
- **Statusline**: a 4-row HUD with the emblem in the corner. Plan usage reads as `ring power` (5-hour window) and `lantern battery` (weekly), counting down.
- **Dot wave**: an animated grid of dots above the spinner while Claude works
- **Welcome oath**: *In brightest day, in blackest night, no evil shall escape my sight.*

```
💥 full throttle, no fear              ▀▀▀▀▀██████▀▀▀▀▀
corps: Opus 5.5                            ▟▛    ▜▙
sector: my-project                         ▜▙    ▟▛
ring power 69%  │  lantern battery 94%  ▄▄▄▄▄██████▄▄▄▄▄
```

| Preset | Ring | Color |
|---|---|---|
| `hal` | the classic hollow ring | emerald with a turquoise edge |
| `john` | a solid core, because his constructs are never hollow | turquoise |
| `guy` | the G | acid lime |
| `default` | none: plain statusline, stock colors | |

## Install

Needs Python 3 and a recent Claude Code (custom themes and plugin hooks are newer features).

```sh
git clone <this repo> && cd claude-lantern
python install.py          # or: python install.py john
```

Then restart `claude`. Switch any time with `/preset hal`, `/preset john`, `/preset guy` or `/preset default`.

`install.py` backs up `~/.claude/settings.json` before touching it, and `python install.py --uninstall` restores that backup.

## What it changes

- `~/.claude/lantern/`: the statusline, the preset switcher, the presets and the wave plugin
- `~/.claude/themes/<lantern>.json`: the color themes
- `~/.claude/commands/preset.md`: the `/preset` command
- `~/.claude/settings.json`: `statusLine`, `theme`, `spinnerVerbs`, `companyAnnouncements`, and `env.CLAUDE_CODE_PLUGIN_DIRS` (to load the wave plugin)

## Make your own Lantern

Add an entry to `LANTERNS` in `lantern/build_presets.py` and run it. `lantern/emblem.py` rasterizes ring shapes into quarter-block characters if you want a new emblem.

The mascot color uses `clawd_body`, a theme token Claude Code doesn't document. If a future version renames it, the mascot just falls back to orange.

Not affiliated with DC or Anthropic.
