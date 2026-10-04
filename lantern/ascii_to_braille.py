"""Shrink a big density ASCII drawing (like an image-to-ASCII export) into a
small braille drawing that fits beside the statusline.

    python ascii_to_braille.py ring.txt 4        # 4 terminal rows tall

Each braille cell is 2x4 dots, the finest detail a terminal can show. An
ASCII character is about twice as tall as it is wide, which the resampling
accounts for so the result keeps its proportions.
"""
import sys

# Darkest to brightest, the usual image-to-ASCII ramp.
DENSITY = {" ": 0.0, "-": 0.0, ".": 0.05, ":": 0.1, "=": 0.35, "+": 0.5, "*": 0.7, "#": 0.85, "%": 1.0, "@": 1.0}
DOT_BITS = [[0x01, 0x02, 0x04, 0x40], [0x08, 0x10, 0x20, 0x80]]


def load(path):
    rows = [line.rstrip("\n") for line in open(path, encoding="utf-8")]
    grid = [[DENSITY.get(ch, 0.5) for ch in row] for row in rows]
    # Crop to the drawing's bounding box.
    lit = [(y, x) for y, row in enumerate(grid) for x, v in enumerate(row) if v > 0.2]
    y0, y1 = min(y for y, _ in lit), max(y for y, _ in lit)
    x0, x1 = min(x for _, x in lit), max(x for _, x in lit)
    return [row[x0:x1 + 1] for row in grid[y0:y1 + 1]]


def to_braille(grid, rows, threshold=0.42):
    src_h, src_w = len(grid), len(grid[0])
    dots_h = rows * 4
    # Source chars are ~1 wide x 2 tall; braille dots are square.
    dots_w = round(dots_h * src_w / (src_h * 2))
    cols = (dots_w + 1) // 2

    def sample(dx, dy):
        # Average the source block that maps onto this dot.
        ya, yb = int(dy * src_h / dots_h), max(int((dy + 1) * src_h / dots_h), int(dy * src_h / dots_h) + 1)
        xa, xb = int(dx * src_w / dots_w), max(int((dx + 1) * src_w / dots_w), int(dx * src_w / dots_w) + 1)
        block = [grid[y][x] for y in range(ya, min(yb, src_h)) for x in range(xa, min(xb, src_w)) if x < len(grid[y])]
        return sum(block) / len(block) if block else 0

    out = []
    for r in range(rows):
        line = ""
        for c in range(cols):
            bits = 0
            for sx in range(2):
                for sy in range(4):
                    if c * 2 + sx < dots_w and sample(c * 2 + sx, r * 4 + sy) > threshold:
                        bits |= DOT_BITS[sx][sy]
            line += chr(0x2800 + bits)
        out.append(line)
    return out


if __name__ == "__main__":
    path, rows = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.42
    sys.stdout.reconfigure(encoding="utf-8")
    for line in to_braille(load(path), rows, threshold):
        print(line)


RAMP = " .:-=+*#%"


def to_ascii(grid, rows):
    """Same shrink, but keeping ASCII characters (one per cell)."""
    src_h, src_w = len(grid), len(grid[0])
    cols = round(rows * src_w / src_h)  # both are ~1:2 cells, so same aspect
    out = []
    for r in range(rows):
        line = ""
        for c in range(cols):
            ya, yb = int(r * src_h / rows), max(int((r + 1) * src_h / rows), int(r * src_h / rows) + 1)
            xa, xb = int(c * src_w / cols), max(int((c + 1) * src_w / cols), int(c * src_w / cols) + 1)
            block = [grid[y][x] for y in range(ya, yb) for x in range(xa, xb) if x < len(grid[y])]
            v = sum(block) / len(block) if block else 0
            line += RAMP[min(len(RAMP) - 1, int(v * len(RAMP)))]
        out.append(line)
    return out
