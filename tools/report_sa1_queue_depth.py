"""保持数・先行表示・DMA開始の比較を検証済みの画面と共に保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_queue_depth'


def main():
    commands=json.loads((DEST/'commands.json').read_text(encoding='utf-8'))
    cases=[];paths=[]
    for variant,command in commands.items():
        d=BUILD/('movestress_detinput_captureburst_'+variant+'_tracepalette')
        s=json.loads((d/'summary.json').read_text())
        assert s['pixelMatchedPresents']==168 and s['hardwarePpuReferencesVerified'],variant
        assert not (d/'failure.txt').exists() and not (d/'pixel_failure.txt').exists(),variant
        cases.append(dict(variant=variant,buildCommand=command,**{k:s[k] for k in (
            'fields','logic','presents','pixelMatchedPresents','romSha256',
            'hardwarePpuReferencesVerified','presentationFieldIntervals','goal60fpsAchieved')}))
        paths.append(d)
    paths.append(BUILD/'fixedword_v1_build')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for d in paths:
            for p in sorted(d.iterdir()):
                if p.is_file() and p.suffix!='.rgb':z.write(p,d.name+'/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,goal60fpsAchieved=False,publicReleaseChanged=False,
        excludedCases={'depth12_v1':'uninitialized COLORBSS status; status retained in BSS',
            'depth12_v2':'build failed; stale ROM run is not a new measurement',
            'fourdepth12prefill_v1':'raw map reused before presentation; pixel mismatch',
            'fourdepth12prefill_v2':'startup prefill repeated after first completed transfer; deadlock',
            'owneddepth12prefill_v1':'checker rejected a valid partial map transfer; map bounds narrowed correctly'},
        evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=result['evidenceSha256']))


if __name__=='__main__':main()
