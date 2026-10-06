"""全12KiB転送と最大12 OBJを同時検証し、最後に既定ROMを戻す。"""
import argparse
import gzip
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from build_game import ROOT,BUILD,GAME

def run(name,*args):
    subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).with_name(name)),*args],check=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='full_transfer_objects',help='results配下の保存先')
    args=parser.parse_args()
    result_root=(GAME/'results').resolve()
    target=(result_root/args.output).resolve()
    assert target.is_relative_to(result_root) and target!=result_root
    release=ROOT/'releases/MonoSHFX2_v001.sfc'
    default_hash=hashlib.sha256(release.read_bytes()).hexdigest()
    try:
        run('build_game.py','--full-transfer')
        run('test_game.py','--scenario','objects','--frames','360')
        src=BUILD/'objects';target.mkdir(parents=True,exist_ok=True)
        for old in target.iterdir():
            if old.is_file():old.unlink()
        records=[json.loads(x) for x in (src/'trace.jsonl').read_text().splitlines()]
        dmas=[r for r in records if 'dmaMs' in r];objs=[r['objMs'] for r in records if 'objMs' in r]
        assert all(r['bytes']==12288 and r['line']<=20 for r in dmas)
        summary=json.loads((src/'summary.json').read_text())
        summary.update({'dmaBytesPerImage':12288,'objBytesPerImage':68,'latestCompletionScanline':max(r['line'] for r in dmas),
            'objPrefetchScanline':22,'firstVisibleScanline':23,'framebufferDmaMaxMs':max(r['dmaMs'] for r in dmas),
            'objDmaMaxMs':max(objs),'objDmaMeanMs':statistics.mean(objs),
            'ppuChecks':json.loads((src/'objects_ppu.json').read_text()),'defaultRomSha256':default_hash})
        (target/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (target/'trace.jsonl.gz').write_bytes(gzip.compress((src/'trace.jsonl').read_bytes(),mtime=0))
        for path in src.glob('objview*'):
            if path.suffix in {'.bin','.png'}:shutil.copy2(path,target/path.name)
        print('全12KiB+OAM68bytes：最遅20行完了、22行OBJ準備、23行表示開始。')
    finally:
        run('build_game.py')
        assert hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()==default_hash

if __name__=='__main__':main()
