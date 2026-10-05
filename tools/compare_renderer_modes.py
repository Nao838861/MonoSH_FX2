"""GSU準備版の全転送と、検証済みの既定部分転送を比較する。"""
import gzip
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path
from build_game import BUILD, GAME, ROOT

TOOLS=Path(__file__).resolve().parent

def run(name,*args):
    subprocess.run([sys.executable,'-X','utf8',str(TOOLS/name),*args],check=True)

def main():
    target=GAME/'results/renderer_modes';target.mkdir(exist_ok=True)
    partial=json.loads((GAME/'results/long.json').read_text())
    released=hashlib.sha256((ROOT/'releases/MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    assert partial['romSha256']==released
    manifest=json.loads((ROOT/'releases/v001.json').read_text())
    assert manifest['buildMode']=={'fullFramebufferTransfer':False,'gsuUv':True,'gsuClip':True}
    run('build_game.py')
    assert hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()==released,'source differs from tested partial release'
    run('build_game.py','--gsu-clip','--full-transfer')
    run('test_game.py','--scenario','long','--frames','18000','--timeout','360')
    full=json.loads((BUILD/'long/summary.json').read_text())
    trace=(BUILD/'long/trace.jsonl').read_bytes()
    rows=[json.loads(line) for line in trace.decode().splitlines()]
    for key,label in [('cpuMs','cpuMeanMs'),('gsuMs','gsuMeanMs'),('joinedMs','joinedMeanMs'),('dmaMs','dmaMeanMs')]:
        full[label]=statistics.mean(r[key] for r in rows if key in r)
    full['dmaBytesMean']=statistics.mean(r['bytes'] for r in rows if 'dmaMs' in r)
    full['framesPerSecondIncludingBoot']=full['rendered']/full['fields']*60.0988
    (target/'full_final.jsonl.gz').write_bytes(gzip.compress(trace,mtime=0))
    (target/'partial_final.jsonl.gz').write_bytes((GAME/'results/long.jsonl.gz').read_bytes())
    (target/'comparison.json').write_text(json.dumps({'partial':partial,'full':full},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    run('build_game.py')
    assert hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()==released,'default rebuild differs'
    print('Partial/full fps:',partial['framesPerSecondIncludingBoot'],full['framesPerSecondIncludingBoot'])

if __name__=='__main__':main()
