"""配置表のCPU移動と初期化DMAの実測を保存する。"""
import hashlib,json,shutil,zipfile
from pathlib import Path
from report_sa1_compact_game import packets
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261011_cpu_map'


def main():
    commands=json.loads((DEST/'commands.json').read_text())
    reference=packets('movestress_detinput_captureburst_fixedtable_v1_tracepalette')
    cases=[]
    with zipfile.ZipFile(DEST/'evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,command in commands.items():
            d=BUILD/('movestress_detinput_captureburst_'+name+'_tracepalette')
            s=json.loads((d/'summary.json').read_text())
            assert s['pixelMatchedPresents']==168 and s['hardwarePpuReferencesVerified']
            assert not list(d.glob('*_expected.bin')) and not (d/'failure.txt').exists()
            actual=packets(d.name);n=min(len(reference),len(actual));assert reference[:n]==actual[:n]
            cases.append(dict(variant=name,buildCommand=command,packetMatchedGenerations=n,
                maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
                **{k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','romSha256','presentationFieldIntervals','goal60fpsAchieved')}))
            for folder in (d,BUILD/(name+'_build')):
                for p in folder.iterdir():
                    if p.is_file() and p.suffix!='.rgb':z.write(p,folder.name+'/'+p.name)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    shutil.copy2(BUILD/'tile_flip_cache.json',DEST/'tile_flip_cache.json')
    result=dict(cases=cases,goal60fpsAchieved=False,publicReleaseChanged=False,
        excludedCases={'fifocpumap_v1':'WRAM routine called through bank 00 instead of 7F; HDMA guard failed',
                       'fifocpumap_v2':'source tile offset included raw buffer base; PPU pixel mismatch',
                       'fifocpumap_v3':'raw-base correction mistakenly applied to descriptor count; no presentation'},
        evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=result['evidenceSha256']))


if __name__=='__main__':main()
