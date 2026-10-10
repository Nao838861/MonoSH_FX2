"""4面CHR・共有mapの比較と割り込みを除いたCPU処理を保存する。"""
import hashlib,json,statistics,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_vram_four'
CASES=('movestress_vramfour_v1_tracepalette','movestress_vramfour_v1_long_tracepalette',
       'movestress_vramfour_v2_active_tracepalette','bossmovestress_vramfour_v2_active_tracepalette',
       'flipfixture_vramfour_v2_tracepalette')


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    cases=[]
    for name in CASES:
        s=json.loads((BUILD/name/'summary.json').read_text())
        assert s['pixelMatchedPresents']>0
        e={'scenario':name}
        for k in ('fields','logic','presents','pixelMatchedPresents','romSha256','labelsSha256',
                  'irqMathRegistersVerified','goal60fpsAchieved','presentationFieldIntervals','stalledTailFields'):
            e[k]=s[k]
        e['firstVisibleField']=s['presentationTimes'][0]['visibleField']
        e['maxSa1Ms']=max(j['totalSa1Ms'] for j in s['sa1Jobs'])
        jobs=[j for j in s['cpuJobs'] if 'activeLogicMs' in j]
        if jobs:
            e['meanActiveCpuMs']=statistics.mean(j['activeLogicMs'] for j in jobs)
            e['maxActiveCpuMs']=max(j['activeLogicMs'] for j in jobs)
            e['meanActivePacketMs']=statistics.mean(j['activeParts'].get('_fx_build_packet',0) for j in jobs)
            e['maxActivePacketMs']=max(j['activeParts'].get('_fx_build_packet',0) for j in jobs)
        cases.append(e)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in CASES:
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
        for folder,prefix in ((BUILD/'vramfour_v1_build','v1_build'),(BUILD,'v2_build')):
            for n in ('MonoSHSA1_4bpp_game.sfc','game.lbl','game.cfg','manifest.json','vram_four_layout.json'):
                z.write(folder/n,prefix+'/'+n)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'cases':cases,'goal60fpsAchieved':False,
            'evidenceSha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print({'cases':len(cases),'archiveBytes':archive.stat().st_size,'sha256':report['evidenceSha256']})


if __name__=='__main__':main()
