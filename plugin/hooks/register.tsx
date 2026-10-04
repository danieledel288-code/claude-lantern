import type { EngineInterface, Register, Timer } from 'claude-code'

import { CYCLE, WAVE_ROWS, waveCells } from './wave'
import type { Rgb } from './wave'

// ~/.claude/lantern/active is written by preset.py (the /preset command). A
// preset that has a `wave` colour (hal, john, guy) turns the constructs on in
// it, and its spinnerVerbs rotate with them.
const MAX_COLUMNS = 48
const FRAME_MS = 100 // invalidate is capped at ten redraws a second
const IDLE_TICKS = 30 // stop animating once no spinner has drawn for ~3s

type Lantern = { colour: Rgb; verbs: string[] }

async function activeLantern($: EngineInterface): Promise<Lantern | undefined> {
  try {
    const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
    if (!home) return undefined
    const dir = `${home.replace(/\\/g, '/')}/.claude/lantern`
    const name = (await $.fs.read(`${dir}/active`)).trim()
    const preset = JSON.parse(await $.fs.read(`${dir}/presets/${name}.json`))
    if (!Array.isArray(preset.wave) || preset.wave.length !== 3) return undefined
    const verbs = Array.isArray(preset.spinnerVerbs) ? preset.spinnerVerbs.filter((v: unknown) => typeof v === 'string') : []
    return { colour: preset.wave, verbs }
  } catch {
    return undefined
  }
}

export const register: Register = on => {
  let lantern: Lantern | undefined
  let ticker: Timer | undefined
  let ticksSinceDraw = 0

  const stop = () => {
    ticker?.cancel()
    ticker = undefined
  }

  on('session.start', async ($, e, next) => {
    lantern = await activeLantern($)
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    lantern = await activeLantern($)
    if (lantern && !ticker) {
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
    if (!lantern || e.surface !== 'terminal') return next(e)

    ticksSinceDraw = 0
    const t = (await $.clock.now()) / 1000

    // Claude Code samples one verb per turn; swap in a new one each time a
    // new construct starts building. Left alone while the engine shows its
    // own message (compacting, retrying, ...).
    const { verbs } = lantern
    const spinner =
      verbs.length > 0 && !e.props.message
        ? await next({ ...e, props: { ...e.props, word: verbs[Math.floor(t / CYCLE) % verbs.length] } })
        : await next(e)

    const { Box, Raster } = $.ui.resolve(e)
    const columns = Math.max(8, Math.min(MAX_COLUMNS, (e.viewport?.columns ?? 40) - 4))

    return (
      <Box flexDirection="column">
        <Raster key="wave" columns={columns} rows={WAVE_ROWS} cells={waveCells(columns, t, lantern.colour)} />
        {spinner}
      </Box>
    )
  })
}
