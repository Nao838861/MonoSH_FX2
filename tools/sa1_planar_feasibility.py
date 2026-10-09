"""キャラクタ変換を省く直接planar描画が8MiBへ収まるか、元画素のまま測る。"""
import json
import struct
import numpy as np
from build_sa1_probe import assets, BUILD
from sa1_patterns import dimensions


def kernel(row, phase):
    p = np.pad(row, (phase, (-len(row)-phase) % 8))
    groups = []
    for x in range(0, len(p), 8):
        g = p[x:x+8]
        if not g.any():
            continue
        mask = sum((0 if int(c) else 0x101) << (7-i) for i, c in enumerate(g))
        vals = [sum(((int(c) >> b) & 1) << (7-i) for i, c in enumerate(g)) for b in range(4)]
        groups.append((x//8*32, mask, vals[0] | vals[1] << 8, vals[2] | vals[3] << 8))
    origin = groups[0][0] if groups else 0
    code = bytearray()
    acc = None
    for offset, mask, a, b in groups:
        for plane, value in ((0, a), (16, b)):
            off = struct.pack('<H', offset-origin+plane)
            if mask:
                code += b'\xbd'+off+b'\x29'+struct.pack('<H', mask)
                if value:
                    code += b'\x09'+struct.pack('<H', value)
                acc = None
            elif acc != value:
                code += b'\xa9'+struct.pack('<H', value)
                acc = value
            code += b'\x9d'+off
    return bytes(code+b'\x6b')


def main():
    variants = assets()
    codes = set()
    rows = set()
    row_entries = 0
    rowmaps = 0
    for asset, sizes in sorted(dimensions().items()):
        ah, aw = variants[asset, 0][1].shape
        for width in sorted({w for w, h in sizes}):
            heights = [h for w, h in sizes if w == width]
            source_rows = set()
            for height in heights:
                source_rows.update(((np.arange(height)*(ah*256//height)) >> 8).tolist())
                rowmaps += height
            for color_phase in range(3 if (asset, 1) in variants else 1):
                pixels = variants[asset, color_phase][1]
                xs = (np.arange(width)*(aw*256//width)) >> 8
                for y in sorted(source_rows):
                    row = pixels[y, xs]
                    for phase in range(8):
                        key = row.tobytes(), phase
                        row_entries += 1
                        if key not in rows:
                            rows.add(key)
                            codes.add(kernel(row, phase))
        print(asset, len(codes), sum(map(len, codes)), flush=True)
    data = {'uniqueRows': len(rows), 'uniqueKernels': len(codes),
            'nativeCodeBytes': sum(map(len, codes)), 'maxKernelBytes': max(map(len, codes)),
            'rowDescriptorsUpperBytes': row_entries*5, 'heightRowMapsBytes': rowmaps,
            'geometryPatterns': sum(map(len, dimensions().values()))}
    (BUILD/'planar_feasibility.json').write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps(data))


if __name__ == '__main__':
    main()
