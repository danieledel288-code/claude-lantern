import { expect, test } from 'claude-code/testing'

import { WAVE_ROWS, brightness, waveCells } from './wave'
import type { Rgb } from './wave'

const GREEN: Rgb = [57, 255, 20]

test('wave frame packs one triplet per cell and moves over time', async () => {
  const columns = 20
  const bytes = Uint8Array.fromBase64(waveCells(columns, 0, GREEN))
  expect(bytes.length).toBe(columns * WAVE_ROWS * 3 * 4)
  expect(waveCells(columns, 0, GREEN)).not.toBe(waveCells(columns, 0.5, GREEN))
})

test('brightness stays within 0..1', async () => {
  for (let x = 0; x < 50; x++) {
    for (let y = 0; y < WAVE_ROWS; y++) {
      const v = brightness(x, y, x * 0.37)
      expect(v >= 0 && v <= 1).toBe(true)
    }
  }
})
