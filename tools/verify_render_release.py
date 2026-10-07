"""現行の描画最適化を、固定標本・通常入力・回帰試験で再検証する。"""
import subprocess
import sys
import argparse
import hashlib
import json

from build_game import BUILD,GAME


def run(name, *args):
    subprocess.run([sys.executable, '-u', '-X', 'utf8', 'tools/'+name, *args], check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',default='bossfinal')
    parser.add_argument('--fixtures',default=str(GAME/'results/boss_scaling_20261008/base_fixtures.json.gz'))
    parser.add_argument('--skip-benchmark',action='store_true',help='同一ROMで完了済みの標本検証を再利用する。')
    parser.add_argument('--skip-profile',action='store_true',help='同一ROMで完了済みの自然入力検証を再利用する。')
    args=parser.parse_args()
    digest=hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    for skip,path in ((args.skip_benchmark,BUILD/('cache_compare_'+args.name)/'comparison.json'),
                      (args.skip_profile,BUILD/('boss_profile_'+args.name)/'summary.json')):
        if skip:
            assert json.loads(path.read_text())['romSha256']==digest,'reused evidence belongs to another ROM'
    if not args.skip_benchmark:
        run('benchmark_render.py', '--name', args.name, '--edges', *(['--fixtures',args.fixtures] if args.fixtures else []))
    run('verify_scaled_assets.py')
    for name, frames in (('objects',360), ('packed',360), ('controls',720),
                        ('pause',360), ('display',720), ('held',1800),
                        ('boss',2600), ('stumble',800), ('stress',360)):
        run('test_game.py', '--scenario', name, '--frames', str(frames), '--timeout', '90')
    if not args.skip_profile:
        run('profile_boss.py', '--frames', '18000', '--timeout', '900',
            '--allow-unreleased', '--output', 'boss_profile_'+args.name)
    run('analyze_render_profile.py', str(BUILD/('boss_profile_'+args.name)),
        '--output', str(BUILD/('road_'+args.name+'.json')))
    # 歴史的な途中版は再生成せず、保存済みのresultsと比較する。
    # 公開する場合は結果を確認し、archive_render_iterations.pyを別途実行する。


if __name__ == '__main__':
    main()
