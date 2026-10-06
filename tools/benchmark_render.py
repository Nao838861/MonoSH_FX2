"""保存済み122標本を再描画し、全FB/OBJとGSU・CPU packet時間を検証する。"""
import argparse
import gzip
import json
from pathlib import Path
import re
import struct

from build_game import BUILD, GAME
from compare_command_cache import run_variant
from verify_game_objects import verify as verify_objects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='final')
    parser.add_argument('--fixtures', type=Path,
        default=GAME/'results/command_cache_20261007/fixtures.json.gz')
    parser.add_argument('--edges', action='store_true', help='縮小済み6素材の左右端・上下反転・未収録幅を追加')
    args, flags = parser.parse_known_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', args.name) and args.name != 'baseline'
    raw = args.fixtures.read_bytes()
    if args.fixtures.suffix == '.gz':
        raw = gzip.decompress(raw)
    cases = json.loads(raw)
    if args.edges:
        for asset, limit in ((13,96), (14,96), (31,96), (0,96), (1,96), (4,128)):
            for width in (7,8,9,limit,limit+1):
                for flip in (0,16,32,48):
                    data = b''.join(struct.pack('<hh6B', center, bottom, width, height, asset, flip, z, 0)
                        for z,(center,bottom,height) in enumerate((
                            (width//2-1,80,79), (width//2-2,160,127),
                            (width//2-3,212,193), (256-width//2+1,160,127),
                            (128,20,127), (128,230,127))))
                    cases.append({'name':f'scaled_edge_{asset}_{width}_{flip}',
                                  'count':6, 'bytes':list(data)})
    result = run_variant(args.name, flags, cases)
    directory = BUILD/('cache_compare_'+args.name)
    (directory/'fixtures.json.gz').write_bytes(gzip.compress(json.dumps(cases).encode(), mtime=0))
    verify_objects(directory)
    for name in ('boss_worst_19ms', 'inside64', 'clipped64'):
        row = next(r for r in result['scenes'] if r['scene'] == name)
        print(name, 'GSU ms', row['gsuMedianMs'], 'packet ms', row['packetMedianMs'])


if __name__ == '__main__':
    main()
