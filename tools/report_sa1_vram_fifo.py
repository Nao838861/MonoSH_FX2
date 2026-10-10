"""可変長VRAM配置の実測と画素照合を保存する。公開ROMは変更しない。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_vram_fifo'


def main():
    commands=json.loads((DEST/'commands.json').read_text(encoding='utf-8'))
    reference=packets('movestress_detinput_captureburst_fixedtable_v1_tracepalette')
    cases=[];paths=[]
    for variant,command in commands.items():
        d=BUILD/('movestress_detinput_captureburst_'+variant+'_tracepalette')
        s=json.loads((d/'summary.json').read_text())
        assert s['pixelMatchedPresents']==168 and s['hardwarePpuReferencesVerified'],variant
        assert not (d/'failure.txt').exists() and not (d/'pixel_failure.txt').exists(),variant
        actual=packets(d.name);count=min(len(reference),len(actual))
        assert reference[:count]==actual[:count],variant
        entry=dict(variant=variant,buildCommand=command,**{k:s[k] for k in (
            'fields','logic','presents','pixelMatchedPresents','romSha256',
            'hardwarePpuReferencesVerified','presentationFieldIntervals','goal60fpsAchieved')})
        entry.update(firstVisibleField=s['presentationTimes'][0]['visibleField'],
                     maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
                     packetMatchedGenerations=count)
        cases.append(entry);paths.append(d)
    paths.append(BUILD/'fifofusedraw_v1_build')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for d in paths:
            assert d.exists(),d
            for p in sorted(d.iterdir()):
                if p.is_file() and p.suffix!='.rgb':z.write(p,d.name+'/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,goal60fpsAchieved=False,publicReleaseChanged=False,
        excludedCases={'fifo_v1':'map wrap limit aliased tile bit 10; corrected',
                       'fifo_v2':'checker missed real 64KiB VRAM address wrap; same ROM retested as fifo_v3'},
        evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=result['evidenceSha256']))


if __name__=='__main__':main()
