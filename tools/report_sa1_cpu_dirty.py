"""転送範囲計算を本体CPUへ移した二方式の実測を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261011_cpu_dirty'


def main():
    commands=json.loads((DEST/'commands.json').read_text())
    reference=packets('movestress_detinput_captureburst_fixedtable_v1_tracepalette')
    cases=[]
    with zipfile.ZipFile(DEST/'evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,command in commands.items():
            d=BUILD/('movestress_detinput_captureburst_'+name+'_tracepalette')
            s=json.loads((d/'summary.json').read_text())
            assert s['pixelMatchedPresents']==len(list(d.glob('present*_meta.bin')))>=120
            assert s['hardwarePpuReferencesVerified']
            actual=packets(d.name);n=min(len(reference),len(actual));assert reference[:n]==actual[:n]
            dirty=[json.loads(line) for line in (d/'cpu_dirty.jsonl').read_text().splitlines()]
            cases.append(dict(variant=name,buildCommand=command,packetMatchedGenerations=n,
                maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
                maxCpuDirtyActiveMs=max(j['activeMs'] for j in dirty),
                maxCpuLogicActiveMs=max(j['activeLogicMs'] for j in s['cpuJobs']),
                **{k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','romSha256','presentationFieldIntervals','goal60fpsAchieved')}))
            for p in d.iterdir():
                if p.is_file() and p.suffix!='.rgb':z.write(p,d.name+'/'+p.name)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,goal60fpsAchieved=False,publicReleaseChanged=False,
        evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=result['evidenceSha256']))


if __name__=='__main__':main()
