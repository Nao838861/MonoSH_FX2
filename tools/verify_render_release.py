"""現行の描画最適化を、固定標本・通常入力・回帰試験で再検証する。"""
import subprocess
import sys

from build_game import BUILD


def run(name, *args):
    subprocess.run([sys.executable, '-u', '-X', 'utf8', 'tools/'+name, *args], check=True)


def main():
    run('benchmark_render.py', '--name', 'final', '--edges')
    run('verify_scaled_assets.py')
    for name, frames in (('objects',360), ('packed',360), ('controls',720),
                        ('pause',360), ('display',720), ('held',1800),
                        ('boss',2600), ('stumble',800), ('stress',360)):
        run('test_game.py', '--scenario', name, '--frames', str(frames), '--timeout', '90')
    run('profile_boss.py', '--frames', '18000', '--timeout', '600',
        '--allow-unreleased', '--output', 'boss_profile_final')
    run('analyze_render_profile.py', str(BUILD/'boss_profile_final'),
        '--output', str(BUILD/'road_final.json'))
    # 歴史的な途中版は再生成せず、保存済みのresultsと比較する。
    # 公開する場合は結果を確認し、archive_render_iterations.pyを別途実行する。


if __name__ == '__main__':
    main()
