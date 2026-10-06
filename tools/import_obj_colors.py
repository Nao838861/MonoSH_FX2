"""NES CHRの色番号を復元し、通常ビルド用の固定OBJ原画を作る（再取込専用）。"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from build_game import GAME

POSES = [0, 10, 11, 12, 13, 14, 15, 16, 4, 5, 6, 7, 8, 9, 1, 2, 3]
BASES = [1, 0, 8, 0x10, 0x18, 0x80, 0x88, 0x90, 0x11, 0x71, 0xd1,
         0x19, 0x59, 0x99, 9, 0x81, 0x89]
IDS = [9, *range(15, 31)]
UPPER = [0, 1, 2, 3]
LOWER = [0, 4, 5, 6]
# RGB5。上半身は濃紺・肌/金・赤、下半身は水色・白・青。
PALETTE = [[0, 0, 0], [2, 4, 14], [31, 20, 2], [31, 3, 3],
           [8, 20, 31], [31, 31, 31], [2, 10, 25], [31, 12, 0],
           [31, 28, 2]] + [[0, 0, 0]] * 7

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nes-root', type=Path, required=True)
    args = parser.parse_args()
    dest = GAME / 'assets/obj_color'
    dest.mkdir(exist_ok=True)
    sources = {name: (args.nes_root / 'res' / name).read_bytes()
               for name in ('sprite.chr', 'sprite2.chr')}
    rgb = [c * 8 + (c >> 2) for color in PALETTE for c in color]
    def save(asset, pixels):
        image = Image.new('P', (len(pixels[0]), len(pixels)))
        image.putpalette(rgb + [0] * (768 - len(rgb)))
        image.putdata([c for row in pixels for c in row])
        image.save(dest / f'{asset:02d}.png', transparency=0)
        legacy = Image.open(GAME / 'assets' / f'{asset:02d}.png').convert('RGBA')
        assert image.size == legacy.size
        assert [c != 0 for c in image.getdata()] == [p[3] >= 128 for p in legacy.getdata()], asset
    for pose, base, asset in zip(POSES, BASES, IDS):
        data = sources['sprite2.chr' if pose >= 10 else 'sprite.chr']
        pixels = []
        for y in range(48):
            palette = UPPER if 4 <= pose < 9 or y < 32 else LOWER
            row = []
            for x in range(32):
                tile = ((base + (y // 16) * 0x20 + (x // 8) * 2) & 0xfe) + (y % 16) // 8
                offset = tile * 16 + y % 8
                bit = 7 - x % 8
                color = ((data[offset] >> bit) & 1) | (((data[offset + 8] >> bit) & 1) << 1)
                row.append(palette[color])
            pixels.append(row)
        if pose in (6, 7, 8):
            shift = 8 if pose == 6 else 16
            pixels = [[0] * 32 for _ in range(shift)] + pixels[:32] + [[0] * 32 for _ in range(16 - shift)]
        save(asset, pixels)
    # 既存の菱形の輪郭を保持する。縮小・当たり判定の変更はしない。
    save(10, [[0 if (d := abs(x - 7) + abs(y - 7)) > 5 else
               (5 if d <= 1 else 8 if d <= 3 else 7) for x in range(16)] for y in range(16)])
    (dest / 'palette.json').write_text(json.dumps({'rgb5': PALETTE}, indent=2) + '\n', encoding='utf-8')
    provenance = {'sourceSha256': {n: hashlib.sha256(d).hexdigest() for n, d in sources.items()},
                  'poses': POSES, 'bases': BASES, 'assets': IDS, 'upperIndices': UPPER,
                  'lowerIndices': LOWER, 'paletteRuleReference': 'MSXSH/tools/generate_player_assets.py',
                  'paletteRule': 'upper for original poses 4..8 or source y<32; otherwise lower',
                  'bulletRule': 'same diamond alpha, orange edge/yellow body/white core',
                  'sourceImageSha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.glob('*.png'))}}
    (dest / 'source.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print('Imported 17 color player poses + bullet; all original alpha masks match')

if __name__ == '__main__':
    main()
