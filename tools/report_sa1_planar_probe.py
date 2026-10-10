"""直接planar描画の速度試験と容量・キャッシュ試算を保存する。"""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_v001'
DEST=ROOT/'game/sa1/v001/results/20261010_planar_probe'


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    cases=[]
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in ('packed_native','planar_native','planar_bits','planar_data'):
            d=BUILD/name;s=json.loads((d/'summary.json').read_text())
            assert s['pixelMatchedJobs']==55
            rom=BUILD/f'MonoSHSA1_{name}_probe.sfc'
            assert hashlib.sha256(rom.read_bytes()).hexdigest()==s['mode']['romSha256']
            cases.append(dict(variant=name,pixelMatchedJobs=55,maxDrawMs=s['maxDrawMs'],
                              maxTotalMs=s['maxTotalMs'],romSha256=s['mode']['romSha256']))
            for p in sorted(d.iterdir()):
                if p.is_file():z.write(p,d.name+'/'+p.name)
            z.write(rom,rom.name)
        for name in ('planar_data_feasibility.json','planar_feasibility.json'):
            shutil.copy2(BUILD/name,DEST/name)
        shutil.copy2(ROOT/'build/sa1_game/planar_code_cache.json',DEST/'planar_code_cache.json')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,fixturePrograms=True,runtimePlacementExcluded=True,
                gameIntegrated=False,goal60fpsAchieved=False,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=result['evidenceSha256']))


if __name__=='__main__':main()
