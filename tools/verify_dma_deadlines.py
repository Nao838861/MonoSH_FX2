"""各転送量の上限を最終許可行に置き、OBJと全FBの転送を実測する。"""
import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from build_game import ROOT,GAME,BUILD


def run(name,*args):
    subprocess.run([sys.executable,'-u','-X','utf8',str(Path(__file__).with_name(name)),*args],check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='boss_scaling_20261008/integrated/dma_deadlines')
    args=parser.parse_args()
    results=(GAME/'results').resolve();target=(results/args.output).resolve()
    assert target.is_relative_to(results) and target!=results
    default_hash=hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    try:
        run('build_game.py','--dma-deadline-probe')
        fine=json.loads((BUILD/'build_mode.json').read_text()).get('fineDmaDeadline',False)
        run('test_game.py','--scenario','objects','--frames','4200' if fine else '360','--timeout','240','--dma-probe')
        source=BUILD/'objects';target.mkdir(parents=True,exist_ok=True)
        rows=[json.loads(s) for s in (source/'trace.jsonl').read_text().splitlines()]
        tiers={};pending=None
        for row in rows:
            if 'dmaStartLine' in row:
                pending=row
            if 'dmaMs' not in row:
                continue
            deadline=pending['deadline']
            if deadline==203:
                assert row['bytes']==12288
                continue
            count=pending['spans']
            assert count in (1,32)
            limit=min(9984,(279-deadline)*170-1)//16*16 if fine else {220:9984,226:8960,233:7680}[deadline]
            expected=limit-count*64-768
            assert row['bytes']==expected
            assert deadline+2<=pending['dmaStartLine']<=deadline+4
            assert row['line']<=20
            tier=tiers.setdefault(f'{deadline}/{count}',{'bytes':expected,'spans':count,'images':0,'latestCompletionScanline':0,'maxDmaStartLine':0})
            tier['images']+=1
            tier['latestCompletionScanline']=max(tier['latestCompletionScanline'],row['line'])
            tier['maxDmaStartLine']=max(tier['maxDmaStartLine'],pending['dmaStartLine'])
        deadlines=range(220,241) if fine else (220,226,233)
        assert set(tiers)=={f'{d}/{n}' for d in deadlines for n in (1,32)} and all(t['images']>=40 for t in tiers.values())
        summary=json.loads((source/'summary.json').read_text())
        summary.update(defaultRomSha256=default_hash,deadlineTiers=tiers,
            objPrefetchScanline=22,firstVisibleScanline=23,ppuChecks=json.loads((source/'objects_ppu.json').read_text()))
        (target/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for filename in ('trace.jsonl','test.lua'):
            (target/(filename+'.gz')).write_bytes(gzip.compress((source/filename).read_bytes(),mtime=0))
        for filename in ('game.lbl','build_mode.json'):
            shutil.copy2(BUILD/filename,target/filename)
        (target/'MonoSHFX2_dma_probe.sfc.gz').write_bytes(gzip.compress((BUILD/'MonoSHFX2_v001.sfc').read_bytes(),mtime=0))
        print('DMA deadline tiers:',json.dumps(tiers))
    finally:
        run('build_game.py')
        assert hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()==default_hash


if __name__=='__main__':main()
