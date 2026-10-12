"""左右二面のSA-1描画比較を、未統合のfixtureとして保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_split_viewport'


def main():
    name='splitfixture_replay_v2_tracepalette';folder=BUILD/name
    s=json.loads((folder/'summary.json').read_text());r=s['splitViewportFixture']
    assert s['pixelMatchedPresents']==500 and s['hardwarePpuReferencesVerified']
    assert r['pairedSpriteReconstructionChecks']==165 and r['allSubsequentPacketOrderVerified']
    assert not s['goal60fpsAchieved'] and not r['gameIntegrated']
    manifest=json.loads((BUILD/'flame_currentbase_build/manifest.json').read_text())
    assert s['romSha256']==manifest['romSha256']
    archive=DEST/'drawing_replay_evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix!='.png':z.write(p,'fixture/'+p.name)
        for p in sorted((BUILD/'flame_currentbase_build').iterdir()):
            if p.is_file():z.write(p,'rom/'+p.name)
        for n in ('splitfixture_replay_v1.log','splitfixture_replay_v2.log'):z.write(BUILD/n,'logs/'+n)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    p=r['pairs'];totals=r['totals'];count=len(p)
    result=dict(romSha256=s['romSha256'],fields=s['fields'],logic=s['logic'],presents=s['presents'],
        pixelMatchedPresents=s['pixelMatchedPresents'],presentationFieldIntervals=s['presentationFieldIntervals'],
        splitViewportFixture=r,means={k:{m:v/count for m,v in a.items()} for k,a in totals.items()},
        drawRatio=totals['drawMs']['splitSum']/totals['drawMs']['baseline'],
        totalRatio=totals['totalSa1Ms']['splitSum']/totals['totalSa1Ms']['baseline'],
        fasterDrawingPairs=sum(j['drawMs']['splitSum']<j['drawMs']['baseline'] for j in p),
        gameIntegrated=False,publicReleaseChanged=False,goal60fpsAchieved=False,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'drawing_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k!='splitViewportFixture'})


if __name__=='__main__':main()
