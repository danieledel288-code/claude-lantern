import type { EngineInterface, Register, Timer } from 'claude-code'

import { WAVE_ROWS, waveCells } from './wave'
import type { Rgb } from './wave'

// ~/.claude/lantern/active is written by preset.py (the /preset command). A
// preset that has a `wave` colour (hal, john, guy) turns the wave on in it.
const MAX_COLUMNS = 48
const FRAME_MS = 100 // invalidate is capped at ten redraws a second
const IDLE_TICKS = 30 // stop animating once no spinner has drawn for ~3s

async function activeWaveColour($: EngineInterface): Promise<Rgb | undefined> {
  try {
    const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
    if (!home) return undefined
    const dir = `${home.replace(/\\/g, '/')}/.claude/lantern`
    const name = (await $.fs.read(`${dir}/active`)).trim()
    const preset = JSON.parse(await $.fs.read(`${dir}/presets/${name}.json`))
    return Array.isArray(preset.wave) && preset.wave.length === 3 ? preset.wave : undefined
  } catch {
    return undefined
  }
}

export const register: Register = on => {
  let colour: Rgb | undefined
  let ticker: Timer | undefined
  let ticksSinceDraw = 0

  const stop = () => {
    ticker?.cancel()
    ticker = undefined
  }

  on('session.start', async ($, e, next) => {
    colour = await activeWaveColour($)
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    colour = await activeWaveColour($)
    if (colour && !ticker) {
      ticksSinceDraw = 0
      ticker = $.clock.every(FRAME_MS, () => {
        // turn.complete doesn't fire on an interrupt, so also stop once the
        // spinner has been gone for a while.
        if (++ticksSinceDraw > IDLE_TICKS) stop()
        else $.ui.invalidate('ui.render')
      })
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    stop()
    return next(e)
  })

  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    const spinner = await next(e)
    if (!colour || e.surface !== 'terminal') return spinner

    ticksSinceDraw = 0
    const { Box, Raster } = $.ui.resolve(e)
    const columns = Math.max(8, Math.min(MAX_COLUMNS, (e.viewport?.columns ?? 40) - 4))
    const t = (await $.clock.now()) / 1000

    return (
      <Box flexDirection="column">
        <Raster key="wave" columns={columns} rows={WAVE_ROWS} cells={waveCells(columns, t, colour)} />
        {spinner}
      </Box>
    )
  })
}
