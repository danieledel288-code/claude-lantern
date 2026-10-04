# /preset — Switch Claude Lantern preset

Swaps the color theme, statusline, spinner words, welcome oath and dot wave
between presets in `~/.claude/lantern/presets/` (`hal`, `john`, `guy`,
`default`).

## Instructions

Argument: `$ARGUMENTS` (a preset name, or empty).

- If empty, run `python "$HOME/.claude/lantern/preset.py" list` and show the
  output verbatim, then ask which one to switch to.
- Otherwise run `python "$HOME/.claude/lantern/preset.py" $ARGUMENTS` and show
  its output verbatim.

Mention that spinner words and the welcome oath change after restarting
`claude`; colors, statusline and the wave change right away.
