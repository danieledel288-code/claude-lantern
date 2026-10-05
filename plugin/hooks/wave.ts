// Pure frame builder for the construct animation, kept apart from the hooks
// so it can be tested without a surface.
//
// Like a Lantern building a construct: a beam fires from the left edge (the
// ring), traces a shape line by line, the shape holds and glows, then
// dissolves into sparks and the next one is built. Drawn in braille cells
// (2x4 sub-dots each), so lines are four times finer than one glyph per cell.

export const WAVE_ROWS = 3
const DEFAULT_BG = 0x01000000
const BRAILLE = 0x2800
const DOT_BITS = [
  [0x01, 0x02, 0x04, 0x40],
  [0x08, 0x10, 0x20, 0x80],
]

export type Rgb = [number, number, number]
type Seg = [number, number, number, number] // x0, y0, x1, y1 in shape units (0..1 tall)

export const CYCLE = 3.4 // seconds per construct (the spinner verb changes with it)
const BUILD = 0.45 // fraction of the cycle spent drawing
const DISSOLVE = 0.8 // fraction at which it starts breaking apart

function circle(cx: number, cy: number, r: number, n = 20): Seg[] {
  const out: Seg[] = []
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2
    const a1 = ((i + 1) / n) * Math.PI * 2
    out.push([cx + Math.cos(a0) * r, cy + Math.sin(a0) * r, cx + Math.cos(a1) * r, cy + Math.sin(a1) * r])
  }
  return out
}

function box(x0: number, y0: number, x1: number, y1: number): Seg[] {
  return [
    [x0, y0, x1, y0],
    [x1, y0, x1, y1],
    [x1, y1, x0, y1],
    [x0, y1, x0, y0],
  ]
}

// Shapes in units where height is 1 and x runs 0..width (aspect from braille
// dots being square). Each is drawn in order, so the trace order is the
// segment order.
const SHAPES: ((w: number) => Seg[])[] = [
  // The emblem: top bar, ring, bottom bar.
  (w) => [[w / 2 - 1.1, 0.05, w / 2 + 1.1, 0.05], ...circle(w / 2, 0.5, 0.42), [w / 2 - 1.1, 0.95, w / 2 + 1.1, 0.95]],
  // A wireframe cube.
  (w) => {
    const c = w / 2
    return [
      ...box(c - 0.9, 0.3, c + 0.3, 0.95),
      ...box(c - 0.3, 0.05, c + 0.9, 0.7),
      [c - 0.9, 0.3, c - 0.3, 0.05],
      [c + 0.3, 0.3, c + 0.9, 0.05],
      [c + 0.3, 0.95, c + 0.9, 0.7],
      [c - 0.9, 0.95, c - 0.3, 0.7],
    ]
  },
  // A suspension bridge across the whole strip.
  (w) => {
    const segs: Seg[] = [[0.3, 0.8, w - 0.3, 0.8]]
    const span = w - 0.6
    const N = 24
    for (let i = 0; i < N; i++) {
      const x0 = 0.3 + (span * i) / N
      const x1 = 0.3 + (span * (i + 1)) / N
      const y = (x: number) => 0.15 + 0.55 * ((x - w / 2) / (span / 2)) ** 2
      segs.push([x0, y(x0), x1, y(x1)])
      if (i % 3 === 0) segs.push([x0, y(x0), x0, 0.8])
    }
    return segs
  },
  // A hammer.
  (w) => {
    const c = w / 2
    return [...box(c - 1.2, 0.1, c + 0.4, 0.45), ...box(c - 0.15, 0.45, c + 0.05, 0.95)]
  },
  // A car in profile: body line, cabin, two wheels.
  (w) => {
    const c = w / 2
    const body: [number, number][] = [
      [c - 1.4, 0.72], [c - 1.4, 0.5], [c - 0.7, 0.42], [c - 0.4, 0.1], [c + 0.45, 0.1],
      [c + 0.8, 0.42], [c + 1.4, 0.5], [c + 1.4, 0.72],
    ]
    const segs: Seg[] = []
    for (let i = 0; i < body.length - 1; i++) segs.push([...body[i], ...body[i + 1]] as Seg)
    segs.push([c - 1.4, 0.72, c - 1.0, 0.72], [c - 0.5, 0.72, c + 0.5, 0.72], [c + 1.0, 0.72, c + 1.4, 0.72])
    return [...segs, ...circle(c - 0.75, 0.75, 0.22, 14), ...circle(c + 0.75, 0.75, 0.22, 14)]
  },
  // The salute: a fist with the middle finger up.
  (w) => {
    const c = w / 2
    return [
      [c - 0.2, 0.45, c - 0.2, 0.17],
      ...circle(c, 0.17, 0.2, 12).slice(6),
      [c + 0.2, 0.17, c + 0.2, 0.45],
      // Folded knuckles either side of it.
      ...circle(c - 0.36, 0.45, 0.14, 10).slice(5),
      ...circle(c - 0.62, 0.48, 0.12, 10).slice(5),
      ...circle(c + 0.36, 0.45, 0.14, 10).slice(5),
      [c - 0.74, 0.48, c - 0.74, 0.95],
      [c - 0.74, 0.95, c + 0.5, 0.95],
      [c + 0.5, 0.95, c + 0.5, 0.45],
      // Thumb tucked across the front.
      [c - 0.7, 0.68, c + 0.15, 0.72],
    ]
  },
  // A fighter jet in profile: pointed nose, canopy, swept wing, tail fin,
  // and an exhaust trail behind it.
  (w) => {
    const c = w / 2
    const hull: [number, number][] = [
      [c + 1.6, 0.55], [c + 1.0, 0.42], [c + 0.6, 0.4], [c - 0.9, 0.42], [c - 1.15, 0.12],
      [c - 1.35, 0.12], [c - 1.3, 0.45], [c - 1.4, 0.55], [c - 1.3, 0.62], [c + 1.0, 0.66], [c + 1.6, 0.55],
    ]
    const segs: Seg[] = []
    for (let i = 0; i < hull.length - 1; i++) segs.push([...hull[i], ...hull[i + 1]] as Seg)
    return [
      ...segs,
      // canopy
      ...circle(c + 0.65, 0.42, 0.18, 12).slice(6),
      // swept wing under the hull
      [c + 0.3, 0.64, c - 0.5, 0.95], [c - 0.5, 0.95, c - 0.75, 0.95], [c - 0.75, 0.95, c - 0.45, 0.65],
      // exhaust trail
      [c - 1.55, 0.52, c - 2.3, 0.5], [c - 1.55, 0.6, c - 2.6, 0.62],
    ]
  },
  // A double-bit battle axe: two curved blades on a long haft.
  (w) => {
    const c = w / 2
    const blade = (dir: number): Seg[] => {
      const segs: Seg[] = []
      const N = 10
      for (let i = 0; i < N; i++) {
        const a0 = -0.9 + (1.8 * i) / N
        const a1 = -0.9 + (1.8 * (i + 1)) / N
        segs.push([c + dir * (0.25 + 0.5 * Math.cos(a0)), 0.42 + 0.42 * Math.sin(a0), c + dir * (0.25 + 0.5 * Math.cos(a1)), 0.42 + 0.42 * Math.sin(a1)])
      }
      segs.push([c + dir * 0.1, 0.3, c + dir * (0.25 + 0.5 * Math.cos(-0.9)), 0.42 + 0.42 * Math.sin(-0.9)])
      segs.push([c + dir * 0.1, 0.54, c + dir * (0.25 + 0.5 * Math.cos(0.9)), 0.42 + 0.42 * Math.sin(0.9)])
      return segs
    }
    return [
      // the haft runs the whole height, slightly tilted
      [c - 0.12, 0.02, c + 0.12, 0.98],
      [c + 0.04, 0.02, c + 0.28, 0.98],
      ...box(c - 0.12, 0.28, c + 0.14, 0.56),
      ...blade(1),
      ...blade(-1),
    ]
  },
  // A heater shield with the Lantern ring set in it.
  (w) => {
    const c = w / 2
    const side = (dir: number): Seg[] => {
      const segs: Seg[] = [[c + dir * 0.75, 0.05, c + dir * 0.75, 0.45]]
      const N = 8
      for (let i = 0; i < N; i++) {
        // curve from the side down to the point
        const u0 = i / N
        const u1 = (i + 1) / N
        const x = (u: number) => c + dir * 0.75 * (1 - u) ** 1.4
        const y = (u: number) => 0.45 + 0.52 * Math.sin((u * Math.PI) / 2)
        segs.push([x(u0), y(u0), x(u1), y(u1)])
      }
      return segs
    }
    return [[c - 0.75, 0.05, c + 0.75, 0.05], ...side(-1), ...side(1), ...circle(c, 0.42, 0.2, 14), [c - 0.4, 0.2, c + 0.4, 0.2], [c - 0.4, 0.64, c + 0.4, 0.64]]
  },
  // A longsword, lying flat: pommel, grip, crossguard, and a pointed blade
  // with a fuller down the middle.
  (w) => {
    const c = w / 2
    return [
      ...circle(c - 2.3, 0.5, 0.12, 10),
      ...box(c - 2.18, 0.42, c - 1.65, 0.58),
      ...box(c - 1.65, 0.12, c - 1.5, 0.88),
      [c - 1.5, 0.38, c + 1.9, 0.38],
      [c - 1.5, 0.62, c + 1.9, 0.62],
      [c + 1.9, 0.38, c + 2.4, 0.5],
      [c + 1.9, 0.62, c + 2.4, 0.5],
      [c - 1.4, 0.5, c + 1.7, 0.5],
    ]
  },
  // A bottle opener: handle, ring head, and the lip that catches the cap.
  (w) => {
    const c = w / 2
    return [
      ...box(c - 1.5, 0.38, c + 0.25, 0.62),
      ...circle(c + 0.65, 0.5, 0.45, 22),
      ...circle(c + 0.7, 0.5, 0.22, 14),
      [c + 0.48, 0.5, c + 0.92, 0.5],
    ]
  },
]

/** A cheap per-dot hash in 0..1, stable across frames, for sparkle/dissolve. */
function hash(x: number, y: number, s: number): number {
  const v = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453
  return v - Math.floor(v)
}

/**
 * The lit dots for one frame: Map of "x,y" -> intensity 0..1, in sub-dot
 * coordinates (width = columns * 2, height = WAVE_ROWS * 4).
 */
export function constructFrame(columns: number, t: number): Map<string, number> {
  const W = columns * 2
  const H = WAVE_ROWS * 4
  const unit = H - 1 // shape units -> dots
  const shapeWidth = W / unit
  const cycle = Math.floor(t / CYCLE)
  const phase = (t % CYCLE) / CYCLE
  const segs = SHAPES[cycle % SHAPES.length](shapeWidth)

  const lengths = segs.map(([x0, y0, x1, y1]) => Math.hypot(x1 - x0, y1 - y0))
  const total = lengths.reduce((a, b) => a + b, 0)
  const built = Math.min(1, phase / BUILD) * total

  const lit = new Map<string, number>()
  const put = (x: number, y: number, v: number) => {
    const xi = Math.round(x)
    const yi = Math.round(y)
    if (xi < 0 || yi < 0 || xi >= W || yi >= H) return
    const key = `${xi},${yi}`
    lit.set(key, Math.max(lit.get(key) ?? 0, v))
  }

  // Trace the shape up to `built` length; remember the pen tip.
  let run = 0
  let tip: [number, number] | null = null
  for (let i = 0; i < segs.length && run < built; i++) {
    const [x0, y0, x1, y1] = segs[i]
    const len = lengths[i]
    const f = Math.min(1, (built - run) / len)
    const steps = Math.max(1, Math.ceil(len * unit * f * 2))
    for (let s = 0; s <= steps; s++) {
      const u = (s / steps) * f
      put((x0 + (x1 - x0) * u) * unit, (y0 + (y1 - y0) * u) * unit, 0.85)
    }
    tip = [(x0 + (x1 - x0) * f) * unit, (y0 + (y1 - y0) * f) * unit]
    run += len
  }

  // While building: the beam from the ring (left edge) to the pen tip.
  if (phase < BUILD && tip) {
    const [tx, ty] = tip
    const steps = Math.ceil(Math.hypot(tx, ty - H / 2) * 1.2)
    for (let s = 0; s <= steps; s++) {
      const u = s / steps
      if (hash(s, cycle, t * 20) > 0.35) put(tx * u, H / 2 + (ty - H / 2) * u, 1)
    }
    put(tx, ty, 1)
  }

  // Dissolve: dots drop out at random and drift upward as sparks.
  if (phase > DISSOLVE) {
    const q = (phase - DISSOLVE) / (1 - DISSOLVE)
    const out = new Map<string, number>()
    for (const [key, v] of lit) {
      const [x, y] = key.split(',').map(Number)
      const h = hash(x, y, cycle)
      if (h > q) {
        const rise = q * 6 * h
        const k = `${x},${Math.round(y - rise)}`
        if (y - rise >= 0) out.set(k, v * (1 - q * 0.6))
      }
    }
    return out
  }
  return lit
}

function shade([r, g, b]: Rgb, v: number): number {
  // Brightest dots lift toward white, like the hot core of a construct.
  const white = Math.max(0, v - 0.85) * 4
  const k = 0.3 + 0.7 * v
  const mix = (c: number) => Math.min(255, Math.round(c * k + (255 - c * k) * white * 0.5))
  return (mix(r) << 16) | (mix(g) << 8) | mix(b)
}

// RasterProps.cells: base64 of [codePoint, fg, bg] u32 triplets, row-major.
export function waveCells(columns: number, t: number, rgb: Rgb): string {
  const lit = constructFrame(columns, t)
  const words = new Uint32Array(columns * WAVE_ROWS * 3)
  for (let row = 0; row < WAVE_ROWS; row++) {
    for (let col = 0; col < columns; col++) {
      let bits = 0
      let peak = 0
      for (let sx = 0; sx < 2; sx++) {
        for (let sy = 0; sy < 4; sy++) {
          const v = lit.get(`${col * 2 + sx},${row * 4 + sy}`)
          if (v) {
            bits |= DOT_BITS[sx][sy]
            peak = Math.max(peak, v)
          }
        }
      }
      const i = (row * columns + col) * 3
      words[i] = BRAILLE + bits
      words[i + 1] = shade(rgb, peak)
      words[i + 2] = DEFAULT_BG
    }
  }
  return new Uint8Array(words.buffer).toBase64()
}
