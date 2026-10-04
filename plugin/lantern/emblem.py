"""Rasterize the Green Lantern emblem into quadrant block characters.

Each terminal cell holds 2x2 sub-pixels. A cell is about twice as tall as it
is wide, so one sub-pixel is ~1 unit wide and ~2 units... no: cell w:h = 1:2,
so a sub-pixel is 0.5w x 1w, i.e. twice as tall as wide. Circle maths below
works in those physical units so the ring comes out round, not oval.
"""
import math
import sys

QUAD = {  # (top-left, top-right, bottom-left, bottom-right) -> char
    (0, 0, 0, 0): " ", (1, 0, 0, 0): "▘", (0, 1, 0, 0): "▝", (0, 0, 1, 0): "▖",
    (0, 0, 0, 1): "▗", (1, 1, 0, 0): "▀", (0, 0, 1, 1): "▄", (1, 0, 1, 0): "▌",
    (0, 1, 0, 1): "▐", (1, 0, 0, 1): "▚", (0, 1, 1, 0): "▞", (1, 1, 1, 0): "▛",
    (1, 1, 0, 1): "▜", (1, 0, 1, 1): "▙", (0, 1, 1, 1): "▟", (1, 1, 1, 1): "█",
}


def emblem(rows, cols, inner=0.0, core=0.0, ring=0.42, bar_h=1, bar_inset=0):
    W, H = cols * 2, rows * 2
    cx, cy = W / 2, H / 2  # in sub-pixels
    # Physical size: sub-pixel width 1, height 2.
    R_out = (H / 2) * 2  # touches the bars
    R_in = R_out * (1 - ring)
    px = [[0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            dx = (x + 0.5 - cx) * 1.0
            dy = (y + 0.5 - cy) * 2.0
            d = math.hypot(dx, dy)
            if R_in <= d <= R_out:
                px[y][x] = 1
            if core and d <= R_in * core:
                px[y][x] = 1
            if (y < bar_h or y >= H - bar_h) and bar_inset <= x < W - bar_inset:
                px[y][x] = 1
    out = []
    for r in range(rows):
        line = ""
        for c in range(cols):
            q = (px[2 * r][2 * c], px[2 * r][2 * c + 1], px[2 * r + 1][2 * c], px[2 * r + 1][2 * c + 1])
            line += QUAD[q]
        out.append(line)
    return out


if __name__ == "__main__":
    for rows, cols in [(3, 12), (3, 14), (4, 16)]:
        for core in (0, 0.45):
            print(f"--- {rows}x{cols} core={core}")
            for l in emblem(rows, cols, core=core):
                print(repr(l)[1:-1].replace(" ", "·"))
