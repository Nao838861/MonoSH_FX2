"""敵弾の透明マスク計算と不透明8word転送の比較を保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_bullet_mask'
CASES=('movestress_bulletmask_arithmetic_v1_tracepalette',
       'movestress_bulletmask_arithmetic_v1_long_tracepalette',
       'flipfixture_bulletmask_arithmetic_v1_tracepalette',
       'flipfixture_bulletopaque8_v1_tracepalette',
       'movestress_bulletopaque8_v1_long_tracepalette')


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    p=BUILD/'bulletopaque8_v1_build';p.mkdir(exist_ok=True)
    for n in ('MonoSHSA1_4bpp_game.sfc','game.lbl','game.cfg','manifest.json'):
        (p/n).write_bytes((BUILD/n).read_bytes())
    cases=[]
    for name in CASES:
        s=json.loads((BUILD/name/'summary.json').read_text())
        assert s['pixelMatchedPresents']>=120
        e={'scenario':name}
        for k in ('fields','logic','presents','pixelMatchedPresents','romSha256',
                  'irqMathRegistersVerified','goal60fpsAchieved','presentationFieldIntervals'):
            e[k]=s[k]
        e['maxSa1Ms']=max(j['totalSa1Ms'] for j in s['sa1Jobs'])
        cases.append(e)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in CASES:
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
        for folder in ('bulletmask_arithmetic_v1_build','bulletopaque8_v1_build'):
            for n in ('MonoSHSA1_4bpp_game.sfc','game.lbl','game.cfg','manifest.json'):
                z.write(BUILD/folder/n,folder+'/'+n)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'cases':cases,'goal60fpsAchieved':False,
            'evidenceSha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print({'cases':len(cases),'archiveBytes':archive.stat().st_size,'sha256':report['evidenceSha256']})


if __name__=='__main__':main()
