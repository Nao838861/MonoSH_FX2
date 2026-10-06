"""方向＋通常射撃の押しっぱなしで、誤ポーズ・入力混入・処理停止を検査する。"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from build_game import ROOT, BUILD, GAME

DIRECTIONS=['up-left','up-right','down-left','down-right','up','down','left','right']

def archive_held(destination):
    source=BUILD/'held'
    summary=json.loads((source/'summary.json').read_text())
    destination.mkdir(parents=True,exist_ok=True)
    for name in ['summary.json','field120.png','field240.png',f"field{summary['fields']}.png"]:
        path=source/name
        if path.exists():shutil.copy2(path,destination/name)
    (destination/'trace.jsonl.gz').write_bytes(gzip.compress((source/'trace.jsonl').read_bytes(),mtime=0))
    return summary

def run(frames,direction,fire):
    subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).with_name('test_game.py')),
        '--scenario','held','--held-direction',direction,'--held-fire',fire,
        '--frames',str(frames),'--timeout','360' if frames>900 else '60'],check=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-long',action='store_true',help='同じROMの保存済み長時間結果を使う')
    parser.add_argument('--output',default='input_freeze_20261006')
    args=parser.parse_args()
    results=(GAME/'results').resolve();target=(results/args.output).resolve()
    assert target.is_relative_to(results) and target!=results
    sha=hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    long_dir=target/'held_up_left_y_long'
    if not args.skip_long:
        run(18000,'up-left','y');archive_held(long_dir)
    long=json.loads((long_dir/'summary.json').read_text())
    assert long['romSha256']==sha and long['fields']==18000
    cases={}
    for fire in ['y','a']:
        for direction in DIRECTIONS:
            print(f'入力維持: {direction} + {fire}',flush=True)
            run(900,direction,fire)
            name=f"held_{direction.replace('-','_')}_{fire}"
            cases[name]=archive_held(target/name)
            assert cases[name]['romSha256']==sha
    all_cases=[long,*cases.values()]
    report={'romSha256':sha,'physicalTurboUsed':False,'long':long,'cases':cases,
            'totalFields':sum(r['fields'] for r in all_cases),
            'checkedFramebuffers':sum(r['checked'] for r in all_cases),
            'maxLogicGapFields':max(r['maxLogicGap'] for r in all_cases),
            'maxPresentationGapFields':max(r['maxPresentationGap'] for r in all_cases)}
    (target/'inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"16入力条件＋5分継続・合計{report['totalFields']}field：論理更新、正しいJOY1、無操作ポーズ無し、FX/OBJ/VRAM一致")

if __name__=='__main__':main()
