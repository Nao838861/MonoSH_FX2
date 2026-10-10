"""スタック描画の楽観的条件と行ごとに復帰する条件を区別して保存する。"""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_v001'
DEST=ROOT/'game/sa1/v001/results/20261011_stack_probe'


def main():
    DEST.mkdir(parents=True,exist_ok=True);cases=[]
    with zipfile.ZipFile(DEST/'evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in ('packed_native','packed_stack','packed_native_rows','packed_stack_rows'):
            d=BUILD/name;s=json.loads((d/'summary.json').read_text());assert s['pixelMatchedJobs']==55
            rom=BUILD/f'MonoSHSA1_{name}_probe.sfc';assert hashlib.sha256(rom.read_bytes()).hexdigest()==s['mode']['romSha256']
            cases.append(dict(variant=name,maxDrawMs=s['maxDrawMs'],maxTotalMs=s['maxTotalMs'],mode=s['mode']))
            for p in d.iterdir():
                if p.is_file() and '_expected' not in p.name:z.write(p,d.name+'/'+p.name)
            z.write(rom,rom.name)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,goal60fpsAchieved=False,gameIntegrated=False,
        evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        correctedFailure='stack prototype wrote 2225 through DB=40; changed to long bank-zero register write')
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=result['evidenceSha256']))


if __name__=='__main__':main()
