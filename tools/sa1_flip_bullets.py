"""反転する敵弾の原寸4bppと固定小数点ステップをROMへ保存する。"""
import struct
import numpy as np


def build(variants, dest):
    pixels = bytearray()
    rows = bytearray()
    pointers = []
    dimensions = bytearray()
    scales = bytearray()
    for asset in (6, 7, 8, 37):
        h, w = variants[asset, 0][1].shape
        dimensions += bytes((w, h))
        rows += struct.pack('<64H', *[y*((w+1)//2) for y in range(64)])
        for axis in (w, h):
            scales += struct.pack('<256H', *[axis*256//n if n else 0 for n in range(256)])
        for phase in range(3):
            pointers.append(len(pixels))
            source = variants[asset, phase][1]
            source = np.pad(source, ((0,0),(0,w&1)))
            pixels += (source[:,::2] | source[:,1::2]<<4).tobytes()
    assert len(pixels) == 18816
    (dest/'flip_pixels.bin').write_bytes(pixels)
    (dest/'flip_rows.bin').write_bytes(rows)
    (dest/'flip_dimensions.bin').write_bytes(dimensions)
    (dest/'flip_scales.bin').write_bytes(scales)
    (dest/'flip_sources.inc').write_text(''.join(f'  .faraddr flip_pixels+{p}\n' for p in pointers))


def transform(name, text):
    if name == 'renderer':
        text = '.import sa1_flip_bullet: far\n' + text
        text = text.replace('  bit #$30\n  beq :+\nunsupported_hflip:\n  bra unsupported_hflip\n:\n  and #3', '  bit #$30\n  beq :+\n  jsl sa1_flip_bullet\n  jmp skip\n:\n  and #3', 1)
    elif name == 'dirty':
        text = text.replace('  sta dirty_top\n  .ifdef SA1_PADDED', '  sta dirty_top\n  lda f:$430007,x\n  and #$30\n  beq :+\n  jmp dirty_untrimmed\n:\n  .ifdef SA1_PADDED', 1)
        text = text.replace('  .endif\n  lda dirty_left\n  bpl', '  .endif\ndirty_untrimmed:\n  lda dirty_left\n  bpl', 1)
    return text
