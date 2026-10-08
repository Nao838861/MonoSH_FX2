"""Losslessly expand the archived palette cells into unused GSU table ROM.

The GSU color pass reads bank $5E only. Existing UV tables, dimensions and
row-margin tables below $B858 remain unchanged; no drawing asset is replaced.
"""
from pathlib import Path
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'game/v001'
CELL_BASE = 0xC000
BASE_MAP = 0xEC00


def build(scale, game=GAME):
    game = Path(game)
    assert len(scale) == 65536
    original_prefix = bytes(scale[:CELL_BASE])
    packed = (game / 'assets/bg_color/cells.bin').read_bytes()
    offsets = struct.unpack('<44H', (game / 'assets/bg_color/offsets.bin').read_bytes())
    cells = bytearray(44 * 256)  # zero is the transparent sentinel
    checked = 0
    for asset, offset in enumerate(offsets):
        width, height = Image.open(game / 'assets' / f'{asset:02d}.png').size
        assert 0 < width <= 128 and 0 < height <= 128
        rows = (height + 7) // 8
        # Asset 43 is the blank/padding asset whose archived offset is EOF.
        if offset == len(packed):
            continue
        for cell in range(rows * 16):
            palette = packed[offset + cell // 2] >> ((cell & 1) * 4) & 15
            assert palette < 8 or palette == 15
            cells[asset * 256 + cell] = 0 if palette == 15 else 0x20 | palette << 2
            checked += 1
    scale[CELL_BASE:BASE_MAP] = cells
    scale[BASE_MAP:BASE_MAP + 768] = bytes(
        0x20 | ((x * 24 + y) >> 8) for y in range(24) for x in range(32)
    )
    assert bytes(scale[:CELL_BASE]) == original_prefix
    result = {'referenceCellsChecked': checked, 'cellBase': CELL_BASE,
              'baseMap': BASE_MAP, 'bytes': len(cells) + 768}
    print('GSU color tables:', result)
    return result


if __name__ == '__main__':
    path = GAME / 'assets/scale5e.bin'
    scale = bytearray(path.read_bytes())
    build(scale)
    path.write_bytes(scale)
