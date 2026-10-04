// Pure frame builder for the dot-wave Raster, kept apart from the hooks so
// it can be tested without a surface.
//
// Each terminal cell is a braille character: 2x4 sub-dots, so the ripple is
// drawn at four times the vertical and twice the horizontal resolution of
// one-glyph-per-cell. Dots switch on where the energy field is strong
// (ordered dithering for the in-between), and the cell's colour follows the
// field too, so the ripple has both shape and glow.

export const WAVE_ROWS = 3
const DEFAULT_BG = 0x01000000
const BRAILLE = 0x2800
// Braille dot bits by sub-position [column][row].
const DOT_BITS = [
  [0x01, 0x02, 0x04, 0x40],
  [0x08, 0x10, 0x20, 0x80],
]
// 2x4 ordered-dither thresholds, so mid-strength areas get an even scatter of
// dots instead of a hard edge.
const DITHER = [
  [0.1, 0.6, 0.35, 0.85],
  [0.75, 0.25, 0.95, 0.45],
]

export type Rgb = [number, number, number]

/**
 * Field strength 0..1 at sub-dot (x, y) and time t (seconds): rings of
 * energy pulsing out from the centre (like a ring charging), crossed by a
 * slow travelling swell so it never looks like a static loop.
 */
export function brightness(x: number, y: number, t: number, width = 96, height = WAVE_ROWS * 4): number {
  const dx = x - width / 2
  const dy = (y - height / 2) * 1.6
  const dist = Math.hypot(dx, dy)
  const pulse = Math.sin(dist * 0.32 - t * 6)
  const swell = Math.sin(x * 0.07 + t * 1.3)
  const fade = 1 - Math.min(1, dist / (width * 0.62))
  const v = ((pulse + 1) / 2) * (0.55 + 0.45 * fade) + 0.18 * swell
  return Math.max(0, Math.min(1, v))
}

function shade([r, g, b]: Rgb, v: number): number {
  const k = 0.25 + 0.75 * v
  return (Math.round(r * k) << 16) | (Math.round(g * k) << 8) | Math.round(b * k)
}

// RasterProps.cells: base64 of [codePoint, fg, bg] u32 triplets, row-major.
export function waveCells(columns: number, t: number, rgb: Rgb): string {
  const words = new Uint32Array(columns * WAVE_ROWS * 3)
  const width = columns * 2
  const height = WAVE_ROWS * 4
  for (let row = 0; row < WAVE_ROWS; row++) {
    for (let col = 0; col < columns; col++) {
      let bits = 0
      let total = 0
      for (let sx = 0; sx < 2; sx++) {
        for (let sy = 0; sy < 4; sy++) {
          const v = brightness(col * 2 + sx, row * 4 + sy, t, width, height)
          total += v
          if (v > DITHER[sx][sy]) bits |= DOT_BITS[sx][sy]
        }
      }
      const i = (row * columns + col) * 3
      words[i] = BRAILLE + bits
      words[i + 1] = shade(rgb, total / 8)
      words[i + 2] = DEFAULT_BG
    }
  }
  return new Uint8Array(words.buffer).toBase64()
}
