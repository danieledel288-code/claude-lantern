---
name: preset
description: Set up Claude Lantern or switch Lantern (hal, john, guy, or default). Use when the user runs /lantern:preset or asks to change their Green Lantern theme.
---

# Claude Lantern preset

Argument: `$ARGUMENTS` (a preset name: `hal`, `john`, `guy` or `default`; may be empty).

Run this command and show its output verbatim:

```
python "${CLAUDE_PLUGIN_ROOT}/setup.py" --plugin $ARGUMENTS
```

If `python` isn't found, run the same command with `python3`.

With no argument it sets up (or keeps) the current Lantern, defaulting to Hal, and prints the list of presets.

Then tell the user, in one line, that colors, the statusline and the construct animation change right away, and that the spinner words and the welcome oath change after restarting `claude`.
