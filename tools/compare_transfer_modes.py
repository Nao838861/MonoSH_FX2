"""部分転送と全FB転送を同じ通常入力で比較し、測定を保存する。"""
import gzip
import json
from pathlib import Path
import statistics
import subprocess
import sys
from build_game import BUILD, GAME

TOOLS=Path(__file__).resolve().parent

def run(name,*args):
    subprocess.run([sys.executable,'-X','utf8',str(TOOLS/name),*map(str,args)],check=True)

def main():
    target=GAME/'results/transfer_modes'
    target.mkdir(exist_ok=True)
    results={}
    for mode in ['partial','full']:
        run('build_game.py','--cpu-clip','--cpu-uv','--'+mode+'-transfer')
        run('test_game.py','--scenario','long','--frames',18000,'--timeout',240)
        src=BUILD/'long'
        summary=json.loads((src/'summary.json').read_text())
        rows=[json.loads(line) for line in (src/'trace.jsonl').read_text().splitlines()]
        for key in ['cpuMs','gsuMs','dmaMs','joinedMs']:
            summary[key+'Mean']=statistics.mean(r[key] for r in rows if key in r)
        summary['fps']=summary['rendered']/summary['fields']*60.0988
        results[mode]=summary
        (target/(mode+'.jsonl.gz')).write_bytes(gzip.compress((src/'trace.jsonl').read_bytes(),mtime=0))
    (target/'summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print({mode:round(summary['fps'],2) for mode,summary in results.items()})
    run('build_game.py')

if __name__=='__main__':main()
