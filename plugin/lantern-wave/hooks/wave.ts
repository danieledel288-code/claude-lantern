// Pure frame builder for the dot-wave Raster, kept apart from the hooks so
// it can be tested without a surface.

export const WAVE_ROWS = 3
const DEFAULT_BG = 0x01000000
// One small dot everywhere; the wave is carried by brightness alone, which
// reads finer than mixing dot sizes.
const DOT = 0x00b7 // ·

// Brightness 0..1 of one cell at time t (seconds): two sine waves crossing,
// a fast one travelling right and a slow swell, so the grid ripples.
export function brightness(x: number, y: number, t: number): number {
  const fast = Math.sin(x * 0.35 - t * 4 + y * 0.9)
  const swell = Math.sin(x * 0.12 + t * 1.7 - y * 0.5)
  return (fast + swell + 2) / 4
}

export type Rgb = [number, number, number]

// The preset's colour, dimmed toward black for the troughs of the wave.
function shade([r, g, b]: Rgb, v: number): number {
  const k = 0.16 + 0.84 * v
  return (Math.round(r * k) << 16) | (Math.round(g * k) << 8) | Math.round(b * k)
}

// RasterProps.cells: base64 of [codePoint, fg, bg] u32 triplets, row-major.
export function waveCells(columns: number, t: number, rgb: Rgb): string {
  const words = new Uint32Array(columns * WAVE_ROWS * 3)
  for (let y = 0; y < WAVE_ROWS; y++) {
    for (let x = 0; x < columns; x++) {
      const v = brightness(x, y, t)
      const i = (y * columns + x) * 3
      words[i] = DOT
      words[i + 1] = shade(rgb, v)
      words[i + 2] = DEFAULT_BG
    }
  }
  return new Uint8Array(words.buffer).toBase64()
}
