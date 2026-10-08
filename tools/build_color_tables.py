"""Build lossless, byte-expanded palette rows for the CPU color compositor.

The archived packed cells remain the independent reference. Identical source
rows share one dictionary entry, so expansion is slightly smaller than the
packed cells plus the two nibble-decode tables used by the original renderer.
"""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
COLOR = ROOT / 'game/v001/assets/bg_color'


def build(directory=COLOR):
    directory = Path(directory)
    packed = (directory / 'cells.bin').read_bytes()
    offsets = struct.unpack('<44H', (directory / 'offsets.bin').read_bytes())
    assert len(packed) % 8 == 0
    assert all(offset % 8 == 0 and offset <= len(packed) for offset in offsets)

    # Offset zero denotes an entirely transparent row and can skip a tile row.
    rows = [bytes(16)]
    row_ids = {rows[0]: 0}
    source_rows = []
    for start in range(0, len(packed), 8):
        row = bytearray()
        for value in packed[start:start + 8]:
            for palette in (value & 15, value >> 4):
                assert palette < 8 or palette == 15, palette
                row.append(0 if palette == 15 else 0x20 | palette << 2)
        row = bytes(row)
        if row not in row_ids:
            row_ids[row] = len(rows)
            rows.append(row)
        source_rows.append(row_ids[row] * 16)

    # The padding asset's old offset is exactly EOF. Give it an empty row.
    source_rows.append(0)
    encoded_rows = b''.join(rows)
    encoded_sources = struct.pack('<' + 'H' * len(source_rows), *source_rows)
    encoded_offsets = struct.pack('<44H', *(offset // 4 for offset in offsets))

    # Check every original cell, independently of the runtime address arithmetic.
    for index, value in enumerate(packed):
        base = source_rows[index // 8]
        for parity in (0, 1):
            palette = value >> (parity * 4) & 15
            expected = 0 if palette == 15 else 0x20 | palette << 2
            assert encoded_rows[base + (index % 8) * 2 + parity] == expected

    for name, data in (
        ('runtime_generated_rows.bin', encoded_rows),
        ('runtime_generated_sources.bin', encoded_sources),
        ('runtime_generated_offsets.bin', encoded_offsets),
    ):
        (directory / name).write_bytes(data)
    result = {
        'sourceRows': len(source_rows) - 1,
        'uniqueRows': len(rows),
        'runtimeBytes': len(encoded_rows) + len(encoded_sources) + len(encoded_offsets),
        'referenceCellsChecked': len(packed) * 2,
    }
    print('Color row dictionary:', result)
    return result


if __name__ == '__main__':
    build()
