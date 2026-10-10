"""PPU位置を確認した転送・待機バッファの比較実験を保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_transfer_trials'

def main():
    commands=json.loads((DEST/'commands.json').read_text(encoding='utf-8'))
    cases=[]
    paths=[]
    for variant,command in commands.items():
        scenario='movestress_detinput_captureburst_'+variant+'_tracepalette'
        d=BUILD/scenario
        if not (d/'summary.json').exists():continue
        s=json.loads((d/'summary.json').read_text())
        assert not (d/'failure.txt').exists(),scenario
        assert not (d/'pixel_failure.txt').exists(),scenario
        assert s['pixelMatchedPresents']==168 and s['hardwarePpuReferencesVerified'],scenario
        cases.append(dict(variant=variant,buildCommand=command,**{k:s[k] for k in (
            'fields','logic','presents','pixelMatchedPresents','romSha256',
            'hardwarePpuReferencesVerified','presentationFieldIntervals','goal60fpsAchieved')},
            maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs'])))
        paths.append(d)
    for name in ('fixedtable_v1_build','fixedtable_budget_v1_build','fixedtable_prefetch_v1_build','fourowned_v2_build','fixedtable_wideedge_v1_build'):
        p=BUILD/name
        if p.exists():paths.append(p)
    DEST.mkdir(parents=True,exist_ok=True)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for d in paths:
            for p in sorted(d.iterdir()):
                if p.is_file() and p.suffix!='.rgb':z.write(p,d.name+'/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,goal60fpsAchieved=False,publicReleaseChanged=False,
        excludedCases={'fourowned_v1':'Lua capture timeout; use v2',
            'cpupackdouble_v1':'wrong WRAM bank in IRQ; pixel verification failed'},
        evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=result['evidenceSha256']))

if __name__=='__main__':main()
