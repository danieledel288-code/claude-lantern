import type { EngineInterface, Register, Timer } from 'claude-code'

import { CYCLE, WAVE_ROWS, waveCells } from './wave'
import type { Rgb } from './wave'

// Claude Lantern's runtime lives in ~/.claude/lantern (statusline, presets,
// preset.py); `active` there names the current Lantern. Its `wave` colour
// turns the constructs on, and its spinnerVerbs rotate with them.
const MAX_COLUMNS = 56
const FRAME_MS = 33 // blits repaint the Raster in place, so ~30 fps is cheap
const COMMANDS = [
  { name: 'hal', preset: 'hal', description: 'Become Hal Jordan: classic ring, emerald' },
  { name: 'john', preset: 'john', description: 'Become John Stewart: solid constructs, turquoise' },
  { name: 'guy', preset: 'guy', description: 'Become Guy Gardner: the G ring, acid lime' },
  { name: 'lantern-off', preset: 'default', description: 'Take the ring off: plain Claude Code look' },
] as const

type Lantern = { colour: Rgb; verbs: string[] }

async function lanternDir($: EngineInterface): Promise<string | undefined> {
  const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
  return home ? `${home.replace(/\\/g, '/')}/.claude/lantern` : undefined
}

async function activeLantern($: EngineInterface): Promise<Lantern | undefined> {
  try {
    const dir = await lanternDir($)
    if (!dir) return undefined
    const name = (await $.fs.read(`${dir}/active`)).trim()
    const preset = JSON.parse(await $.fs.read(`${dir}/presets/${name}.json`))
    if (!Array.isArray(preset.wave) || preset.wave.length !== 3) return undefined
    const verbs = Array.isArray(preset.spinnerVerbs) ? preset.spinnerVerbs.filter((v: unknown) => typeof v === 'string') : []
    return { colour: preset.wave, verbs }
  } catch {
    return undefined
  }
}

/**
 * Switches Lantern by running the runtime's preset.py, or the plugin's
 * setup.py the first time (it installs the runtime and the statusline).
 * Uses the Python the statusline already runs with, when there is one.
 */
async function switchLantern($: EngineInterface, preset: string): Promise<string> {
  const dir = await lanternDir($)
  if (!dir) return 'Claude Lantern: could not find your home folder.'
  let python = 'python'
  try {
    const home = dir.slice(0, -'/.claude/lantern'.length)
    const settings = JSON.parse(await $.fs.read(`${home}/.claude/settings.json`))
    const match = /^"([^"]+)"/.exec(settings?.statusLine?.command ?? '')
    if (match && match[1].toLowerCase().includes('python')) python = match[1]
  } catch {
    // no settings yet: plain `python` it is
  }
  let installed = true
  try {
    await $.fs.read(`${dir}/preset.py`)
  } catch {
    installed = false
  }
  const argv = installed ? [python, `${dir}/preset.py`, preset] : [python, `${$.plugin.root}/setup.py`, '--plugin', preset]
  try {
    const { exitCode, stdout, stderr } = await $.process.run(argv, { timeoutMs: 30_000 })
    if (exitCode !== 0) return `Claude Lantern: switching failed.\n${stderr.trim() || stdout.trim()}`
    return (stdout.trim().split('\n')[0] ?? '') + (installed ? '' : '\nSet up Claude Lantern. Restart claude once for the colors and statusline.')
  } catch {
    return 'Claude Lantern needs Python 3 on your PATH (python or python3).'
  }
}

// Module state (a hot reload starts it over, which is fine for animation).
const state: {
  lantern?: Lantern
  ticker?: Timer
  band?: { requestId: string; columns: number }
  lastCycle: number
} = { lastCycle: -1 }

function stop() {
  state.ticker?.cancel()
  state.ticker = undefined
}

// Repaint the construct in place each frame; only re-render (for the spinner
// word) once per construct.
function start($: EngineInterface) {
  if (state.ticker) return
  state.ticker = $.clock.every(FRAME_MS, () => {
    const t = Date.now() / 1000
    const cycle = Math.floor(t / CYCLE)
    if (cycle !== state.lastCycle) {
      state.lastCycle = cycle
      $.ui.invalidate('ui.render')
    }
    const { band, lantern } = state
    if (band && lantern) {
      $.ui.blit({ requestId: band.requestId, key: 'construct', cells: waveCells(band.columns, t, lantern.colour) }).catch(() => {})
    }
  })
}

export const register: Register = on => {

  on('session.start', async ($, e, next) => {
    state.lantern = await activeLantern($)
    for (const c of COMMANDS) {
      await $.command.register({ name: c.name, description: c.description })
    }
    return next(e)
  })

  for (const c of COMMANDS) {
    on('command.run', { command: c.name }, async $ => {
      const text = await switchLantern($, c.preset)
      state.lantern = await activeLantern($)
      $.ui.invalidate('ui.render')
      return { text }
    })
  }

  on('prompt.submit', async ($, e, next) => {
    state.lantern = await activeLantern($)
    if (state.lantern) start($)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    stop()
    state.band = undefined
    return next(e)
  })

  // Claude Code samples one verb per turn; swap in a new one per construct.
  // Left alone while the engine shows its own message (compacting, ...).
  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    const { lantern } = state
    if (!lantern || lantern.verbs.length === 0 || e.props.message) return next(e)
    const word = lantern.verbs[Math.floor(Date.now() / 1000 / CYCLE) % lantern.verbs.length]
    return next({ ...e, props: { ...e.props, word } })
  })

  // The construct lives in the band above the prompt while Claude works.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { lantern } = state
    if (!lantern || !e.props.isWorking || e.props.hasSurvey || e.surface !== 'terminal') {
      state.band = undefined
      return next(e)
    }
    const columns = Math.max(8, Math.min(MAX_COLUMNS, e.props.bodyColumns - 4))
    state.band = { requestId: e.requestId, columns }
    start($)
    const { Raster } = $.ui.resolve(e)
    return <Raster key="construct" columns={columns} rows={WAVE_ROWS} cells={waveCells(columns, Date.now() / 1000, lantern.colour)} />
  })
}
