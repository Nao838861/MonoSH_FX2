"""4bpp実験のROM・計測・画素比較用標本をモード別に保存する。"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from build_game import ROOT, BUILD

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['color','mono']);p.add_argument('scenarios',nargs='+');args=p.parse_args()
    mode=json.loads((BUILD/'build_mode.json').read_text())
    mode['transferMode']='column-spans-two-pages'
    assert mode['bitsPerPixel']==4 and mode['color']==(args.mode=='color')
    dest=ROOT/'game/v001/results/four_bpp_20261008'/args.mode;dest.mkdir(parents=True,exist_ok=True)
    releases=ROOT/'releases';releases.mkdir(exist_ok=True)
    rom=releases/f'MonoSHFX2_4bpp30_{args.mode}.sfc';shutil.copy2(BUILD/'MonoSHFX2_v001.sfc',rom)
    manifest={'rom':rom.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),
              'buildMode':mode,'packing':json.loads((BUILD/'assets4/packing4.json').read_text()),
              'upstream':subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip(),'scenarios':{}}
    for scenario in args.scenarios:
        src=BUILD/f'four_{scenario}';out=dest/scenario;out.mkdir(exist_ok=True)
        summary=json.loads((src/'summary.json').read_text())
        assert summary.get('romSha256',manifest['sha256'])==manifest['sha256'],'test ROM differs from release ROM'
        summary['romSha256']=manifest['sha256']
        intervals=summary['intervals'];steady={int(k):v for k,v in intervals.items() if int(k)<20}
        summary['renderFPS']=sum(steady.values())*60.0988/sum(k*v for k,v in steady.items())
        summary['delayedPresents']=sum(v for k,v in steady.items() if k>2)
        records=[json.loads(l) for l in (src/'trace.jsonl').read_text().splitlines()]
        sizes=[r['dmaBytes'] for r in records if 'dmaBytes'in r]
        summary['dmaBytes']={'min':min(sizes),'max':max(sizes),'mean':sum(sizes)/len(sizes)}
        summary['mathChecks']=sum(r.get('mathChecks',0) for r in records)
        summary['pixelSamples']=len(list(src.glob('frame*_fb.bin')))
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        manifest['scenarios'][scenario]=summary
        (out/'trace.jsonl.gz').write_bytes(gzip.compress((src/'trace.jsonl').read_bytes(),mtime=0))
        (out/'test.lua.gz').write_bytes(gzip.compress((src/'test.lua').read_bytes(),mtime=0))
        shutil.copy2(src/'emulator.log',out/'emulator.log')
        with zipfile.ZipFile(out/'samples.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(src.glob('frame*')):z.write(f,f.name)
        with zipfile.ZipFile(out/'screens.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(src.glob('screen*.png')):z.write(f,f.name)
        shots=sorted(src.glob('screen*.png'))
        if shots:shutil.copy2(shots[min(1,len(shots)-1)],out/'preview.png')
    for name in ('game.lbl','game.map','build_mode.json'):
        if name=='game.map':
            clean='\n'.join(line.rstrip() for line in (BUILD/name).read_text().splitlines()).rstrip()+'\n'
            (dest/name).write_text(clean)
        else:shutil.copy2(BUILD/name,dest/name)
    (releases/f'4bpp30_{args.mode}.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'rom':str(rom),'sha256':manifest['sha256'],'scenarios':args.scenarios}))

if __name__=='__main__':main()
