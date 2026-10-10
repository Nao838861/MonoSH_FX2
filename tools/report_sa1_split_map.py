"""低・高byte分離マップ試験の原データとビルドを保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_split_map'
CASES=('movestress_splitmap_v1_tracepalette','movestress_splitmap_v1_long_tracepalette',
       'movestress_splitmap_mvn_tracepalette','movestress_splitmap_mvn_long_tracepalette')


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
        cases.append(e)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in CASES:
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
        for folder,prefix in ((BUILD/'splitmap_v1_build','v1_build'),(BUILD,'mvn_build')):
            for n in ('MonoSHSA1_4bpp_game.sfc','game.lbl','game.cfg','manifest.json'):
                z.write(folder/n,prefix+'/'+n)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'cases':cases,'goal60fpsAchieved':False,
            'evidenceSha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print({'cases':len(cases),'archiveBytes':archive.stat().st_size,'sha256':report['evidenceSha256']})


if __name__=='__main__':main()
