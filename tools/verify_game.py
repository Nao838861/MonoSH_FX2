"""移植版をビルドし、短時間・長時間検証後に成果物を保存する。"""
from pathlib import Path
import subprocess
import sys

TOOLS=Path(__file__).resolve().parent

def run(name,*args):
    subprocess.run([sys.executable,'-X','utf8',str(TOOLS/name),*map(str,args)],check=True)

def main():
    if '--equivalence' in sys.argv: run('verify_game_equivalence.py')
    run('build_game.py')
    for scenario,frames in [('play',360),('controls',720),('pause',360),('stumble',800),
                            ('boss',2600),('stress',360),('packed',360),('display',720),('long',18000),('profile',2400)]:
        print(f'=== {scenario}: {frames} fields ===',flush=True)
        run('test_game.py','--scenario',scenario,'--frames',frames,'--timeout',240 if scenario=='long' else 60)
    run('archive_game.py')

if __name__=='__main__': main()
