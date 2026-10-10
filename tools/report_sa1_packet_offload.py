"""描画命令のSA-1移行試験をROM・ラベル・原データと保存する。"""
import hashlib,json,statistics,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_packet_offload'
CASES=('movestress_packetoffload_v1_tracepalette',
       'movestress_packetoffload_v1_long_tracepalette',
       'movestress_packetiram_v1_tracepalette',
       'movestress_packetiram_arrays_v2_tracepalette',
       'movestress_packetiram_arrays_v2_long_tracepalette',
       'bossmovestress_packetiram_arrays_v2_tracepalette',
       'flipfixture_packetiram_arrays_v2_tracepalette')


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    cases=[]
    for name in CASES:
        s=json.loads((BUILD/name/'summary.json').read_text())
        assert s['pixelMatchedPresents']>=120
        e={'scenario':name}
        for k in ('fields','logic','presents','pixelMatchedPresents','romSha256','labelsSha256',
                  'irqMathRegistersVerified','goal60fpsAchieved','presentationFieldIntervals','stalledTailFields'):
            e[k]=s[k]
        e['firstVisibleField']=s['presentationTimes'][0]['visibleField']
        e['maxSa1Ms']=max(j['totalSa1Ms'] for j in s['sa1Jobs'])
        jobs=[j for j in s['cpuJobs'] if 'activeLogicMs' in j]
        e['meanActiveCpuMs']=statistics.mean(j['activeLogicMs'] for j in jobs)
        p=BUILD/name/'packet_prepare.jsonl'
        if p.exists():
            a=[json.loads(line) for line in p.read_text().splitlines()]
            e['meanPacketPrepareMs']=statistics.mean(j['ms'] for j in a)
            e['maxPacketPrepareMs']=max(j['ms'] for j in a)
        cases.append(e)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in CASES:
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
        for folder in ('packetoffload_v1_build','packetiram_v1_build','packetiram_arrays_v2_build'):
            for n in ('MonoSHSA1_4bpp_game.sfc','game.lbl','game.cfg','manifest.json'):
                z.write(BUILD/folder/n,folder+'/'+n)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'cases':cases,'goal60fpsAchieved':False,
            'evidenceSha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print({'cases':len(cases),'archiveBytes':archive.stat().st_size,'sha256':report['evidenceSha256']})


if __name__=='__main__':main()
