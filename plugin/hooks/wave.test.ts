import { expect, test } from 'claude-code/testing'

import { WAVE_ROWS, constructFrame, waveCells } from './wave'
import type { Rgb } from './wave'

const GREEN: Rgb = [57, 255, 20]

test('frame packs one triplet per cell and animates over time', async () => {
  const columns = 20
  const bytes = Uint8Array.fromBase64(waveCells(columns, 0.5, GREEN))
  expect(bytes.length).toBe(columns * WAVE_ROWS * 3 * 4)
  expect(waveCells(columns, 0.5, GREEN)).not.toBe(waveCells(columns, 1.2, GREEN))
})

test('a construct is built, held, and stays inside the strip', async () => {
  const columns = 48
  const building = constructFrame(columns, 0.4).size
  const held = constructFrame(columns, 2.0).size
  expect(held > building).toBe(true)
  for (const key of constructFrame(columns, 2.0).keys()) {
    const [x, y] = key.split(',').map(Number)
    expect(x >= 0 && x < columns * 2 && y >= 0 && y < WAVE_ROWS * 4).toBe(true)
  }
})
