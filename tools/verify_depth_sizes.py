"""実ROMの奥行き寸法、接地データの保持、段階の分散を検査する。"""
import csv
import hashlib
import json
import re
import argparse
import gzip
import struct
from pathlib import Path
from smooth_depth import TABLES, parse_table
from build_game import GAME, BUILD


def metrics(pairs):
    runs = []
    start = 0
    for i in range(1, len(pairs)+1):
        if i == len(pairs) or pairs[i] != pairs[start]:
            runs.append(i-start)
            start = i
    return {'uniqueSizes': len(set(pairs)), 'longestHold': max(runs),
            'changeEvents': sum(a != b for a, b in zip(pairs, pairs[1:])),
            'sizeJerk': sum((a-2*b+c)**2 for axis in (0, 1)
                            for a, b, c in zip([p[axis] for p in pairs],
                                              [p[axis] for p in pairs[1:]],
                                              [p[axis] for p in pairs[2:]]))}


def replay_previews(directory, cases, output):
    """独立照合を通ったMesenのFBから、旧寸法／新寸法の比較GIFを作る。"""
    from PIL import Image, ImageDraw
    records = [json.loads(line) for line in (directory/'replay.jsonl').read_text().splitlines()]
    selected = {}
    for row in records:
        if row['kind'] == 'gsu' and row['repeatIndex'] == 2:
            path = directory/f"frame{row['image']:05d}.bin"
            if path.exists():
                selected.setdefault(row['scene'], path)
    palettes = ((65, 35, 85), (240, 240, 240), (150, 150, 150), (40, 35, 45))
    animations = {}
    for i, case in enumerate(cases, 1):
        _, asset, z = case['name'].split('_')
        raw = selected[i].read_bytes()
        frame = Image.new('RGB', (256, 192))
        pixels = frame.load()
        for y in range(192):
            for x in range(256):
                addr = ((x//8)*24+y//8)*16+(y&7)*2
                bit = 7-(x&7)
                color = ((raw[addr]>>bit)&1) | (((raw[addr+1]>>bit)&1)<<1)
                pixels[x, y] = palettes[color]
        draw = ImageDraw.Draw(frame)
        draw.text((8, 0), 'OLD', fill='white')
        draw.text((136, 0), 'NEW', fill='white')
        draw.text((93, 0), 'Z='+z, fill='white')
        frame = frame.resize((512, 384), Image.Resampling.NEAREST)
        animations.setdefault(asset, []).append(frame)
    for asset, frames in animations.items():
        frames[0].save(output/f'depth_{asset}.gif', save_all=True, append_images=frames[1:],
                       duration=20, loop=0, optimize=False)
    # 遠〜中距離の寸法が停滞していた区間も静止画像で比較できるようにする。
    samples = animations['13']
    montage = Image.new('RGB', (512*4, 384*2))
    for i, z in enumerate((110, 104, 98, 92, 86, 80, 74, 68)):
        montage.paste(samples[110-z], ((i%4)*512, (i//4)*384))
    montage.save(output/'boss_body_steps.png')
    montage = Image.new('RGB', (512*4, 384*2))
    for i, z in enumerate((90, 81, 80, 79, 56, 55, 54, 53)):
        montage.paste(animations['36'][110-z], ((i%4)*512, (i//4)*384))
    montage.save(output/'em1_steps.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay', action='store_true', help='主要6素材と開いたEM1の5poseの全ZをMesenで再描画する。')
    args = parser.parse_args()
    output = BUILD/'smooth_depth'
    output.mkdir(exist_ok=True)
    labels = {m[2]: int(m[1], 16) for m in re.finditer(
        r'al ([0-9A-Fa-f]+) \.([^\s]+)', (BUILD/'game.lbl').read_text())}
    rom = (BUILD/'MonoSHFX2_v001.sfc').read_bytes()
    mode = json.loads((BUILD/'build_mode.json').read_text())
    assert mode['smoothDepthSizes']
    report = {'romSha256': hashlib.sha256(rom).hexdigest(), 'tables': {}}
    legacy = (GAME.parents[1]/'releases/MonoSHFX2_v001.sfc').read_bytes()
    previous = GAME/'results/smooth_depth_20261008/previous_release.sfc.gz'
    if not mode.get('gsuColor') and legacy == rom and previous.exists():
        legacy = gzip.decompress(previous.read_bytes())
    report['comparisonRomSha256'] = hashlib.sha256(legacy).hexdigest()
    if report['comparisonRomSha256'] != report['romSha256']:
        report['cpuCodeIdentical'] = rom[0x10000:0x20000] == legacy[0x10000:0x20000]
        report['gsuCodeIdentical'] = rom[0x8000:0x10000] == legacy[0x8000:0x10000]
        # $43はPPU背景、GSU用の原画・縮小画像・UVは$44以降。
        report['graphicsAndUvIdentical'] = rom[0x40000:] == legacy[0x40000:]
        if mode.get('gsuColor'):
            # The new GSU code and added palette tables are intentional. Source
            # pixels, scaled graphics, UV tables and scaling metadata stay exact.
            report['graphicsAndUvIdentical'] = (
                rom[0x40000:0x1ec000] == legacy[0x40000:0x1ec000]
                and rom[0x1f0000:] == legacy[0x1f0000:])
            report['gsuPaletteCodeAndTablesAdded'] = True
            assert report['graphicsAndUvIdentical']
        else:
            assert all(report[key] for key in ('gsuCodeIdentical', 'graphicsAndUvIdentical'))
    manifest = json.loads((GAME.parents[1]/'releases/v001.json').read_text(encoding='utf-8'))
    for filename, expected in manifest['sourceSha256'].items():
        assert hashlib.sha256((GAME/'upstream'/filename).read_bytes()).hexdigest() == expected
    report['upstreamFilesVerified'] = len(manifest['sourceSha256'])
    ground_text = (GAME/'upstream/monosh_projection_data.asm').read_text(encoding='utf-8')
    ground_text = ground_text.split('_monosh_ground_depth_rows:', 1)[1]
    ground_rows = []
    for line in ground_text.splitlines():
        if line.strip().startswith('defb'):
            ground_rows.extend(map(int, line.split('defb')[1].strip().split(',')))
        elif ground_rows and line.strip() and not line.lstrip().startswith(';'):
            break
    assert len(ground_rows) == 65*81
    rows = []
    for filename, tables in TABLES.items():
        original = (GAME/'upstream'/f'{filename}.c').read_text(encoding='utf-8')
        built = (BUILD/f'{filename}.c').read_text(encoding='utf-8')
        for name, stride in tables:
            _, before = parse_table(original, name)
            _, after = parse_table(built, name)
            addr = labels['__RODATA_LOAD__']-0x400000+labels['_'+name]-labels['__RODATA_RUN__']
            assert rom[addr:addr+len(after)] == bytes(after), name
            old = list(zip(before[::stride], before[1::stride]))
            new = list(zip(after[::stride], after[1::stride]))
            assert old[0] == new[0] and old[-1] == new[-1], name
            for axis in (0, 1):
                assert all(1 <= p[axis] <= 255 for p in new)
                assert all(a[axis] >= b[axis] for a, b in zip(new, new[1:])), name
            if stride == 4:
                assert before[2::stride] == after[2::stride], name
                assert after[3::stride] == [p[0]//2 for p in new], name
            stats = {'before': metrics(old), 'after': metrics(new),
                     'maximumDimensionDifference': max(abs(a-b) for p, q in zip(old, new)
                                                        for a, b in zip(p, q))}
            if name in ('stage_tree0_geometry', 'stage_bush0_geometry', 'stage_bush1_geometry'):
                for phase, sizes in (('before', old), ('after', new)):
                    reversals = []
                    for camera in range(65):
                        tops = [207-ground_rows[camera*81+219-before[z*stride+2]]
                                + (0 if z < 2 else 1 if z < 6 else 2 if z < 9 else 3)
                                - sizes[z][1] for z in range(111)]
                        reversals.extend((camera, z, a-b) for z, (a, b) in enumerate(zip(tops, tops[1:])) if a > b)
                    stats[phase]['groundTopReversals'] = len(reversals)
                    stats[phase]['maximumTopReversal'] = max((r[2] for r in reversals), default=0)
            report['tables'][name] = stats
            for z, (a, b) in enumerate(zip(old, new)):
                rows.append([name, z, *a, *b])
    open_source = (GAME/'upstream/monosh_enemy_data.c').read_text(encoding='utf-8')
    _, original = parse_table(open_source, 'monosh_em1_open_geometry')
    open_sizes = (BUILD/'em1_open_sizes.bin').read_bytes()
    addr = labels['__CODE_LOAD__']-0x400000+labels['fx_em1_open_sizes']-labels['__CODE_RUN__']
    assert rom[addr:addr+1110] == open_sizes and len(open_sizes) == 1110
    for pose in range(5):
        old = [tuple(original[(pose+(10 if z < 54 else 5 if z < 80 else 0))*2:][:2]) for z in range(111)]
        new = [tuple(open_sizes[z*10+pose*2:][:2]) for z in range(111)]
        assert old[0] == new[0] and old[-1] == new[-1]
        assert all(0 <= a[axis]-b[axis] <= 1 for a, b in zip(new, new[1:]) for axis in (0, 1))
        name = f'em1_open_pose{pose+1}'
        stats = {'before': metrics(old), 'after': metrics(new),
                 'maximumDimensionDifference': max(abs(a-b) for p, q in zip(old, new) for a, b in zip(p, q))}
        for phase, sizes in (('before', old), ('after', new)):
            stats[phase]['maximumSizeStep'] = max(abs(a[axis]-b[axis]) for a, b in zip(sizes, sizes[1:]) for axis in (0, 1))
        report['tables'][name] = stats
        for z, (a, b) in enumerate(zip(old, new)):
            rows.append([name, z, *a, *b])
    report['totals'] = {phase: {'sizeJerk': sum(v[phase]['sizeJerk'] for v in report['tables'].values()),
                               'changeEvents': sum(v[phase]['changeEvents'] for v in report['tables'].values())}
                        for phase in ('before', 'after')}
    assert report['totals']['after']['changeEvents'] > report['totals']['before']['changeEvents']
    for name in ('stage_tree0_geometry', 'monosh_enemy_geometry', 'monosh_boss_body_geometry',
                 'monosh_boss_face_geometry'):
        assert report['tables'][name]['after']['longestHold'] < report['tables'][name]['before']['longestHold']
    tree = report['tables']['stage_tree0_geometry']
    assert tree['after']['groundTopReversals'] <= tree['before']['groundTopReversals']
    assert tree['after']['maximumTopReversal'] <= tree['before']['maximumTopReversal']
    (output/'tables.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    with (output/'sizes.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['table', 'z', 'old_width', 'old_height', 'new_width', 'new_height'])
        writer.writerows(rows)
    print(json.dumps(report, indent=2))
    if args.replay:
        from compare_command_cache import run_variant
        from verify_game_objects import verify as verify_objects
        cases = []
        targets = ((4, 'monosh_stage_data', 'stage_tree0_geometry', 4),
                   (3, 'monosh_enemy_data', 'monosh_enemy_geometry', 2),
                   (13, 'monosh_boss_data', 'monosh_boss_body_geometry', 2),
                   (14, 'monosh_boss_data', 'monosh_boss_face_geometry', 2),
                   (6, 'monosh_enemy_data', 'monosh_ebullet_animation_geometry', 2),
                   (31, 'monosh_enemy_data', 'monosh_ebullet4_geometry', 2))
        for asset, filename, name, stride in targets:
            _, old = parse_table((GAME/'upstream'/f'{filename}.c').read_text(encoding='utf-8'), name)
            _, new = parse_table((BUILD/f'{filename}.c').read_text(encoding='utf-8'), name)
            for z in range(110, -1, -1):
                raw = b''.join(struct.pack('<hh6B', center, 190, data[z*stride], data[z*stride+1],
                                           asset, 0, z, 0) for center, data in ((64, old), (192, new)))
                cases.append({'name': f'depth_{asset}_{z}', 'count': 2, 'bytes': list(raw)})
        for pose in range(5):
            for z in range(110, -1, -1):
                index = (pose+(10 if z < 54 else 5 if z < 80 else 0))*2
                pairs = ((64, original[index:index+2]), (192, open_sizes[z*10+pose*2:z*10+pose*2+2]))
                raw = b''.join(struct.pack('<hh6B', center, 190, *data, 32+pose, 0, z, 0) for center, data in pairs)
                cases.append({'name': f'depth_{32+pose}_{z}', 'count': 2, 'bytes': list(raw)})
        result = run_variant('smoothdepth', [], cases, reuse_build=True)
        dest = BUILD/'cache_compare_smoothdepth'
        (dest/'fixtures.json.gz').write_bytes(gzip.compress(json.dumps(cases).encode(), mtime=0))
        verify_objects(dest)
        replay_previews(dest, cases, output)
        print('Verified all-depth rendering:', len(result['scenes']), 'scenes;', result['imagesVerified'], 'images')


if __name__ == '__main__':
    main()
