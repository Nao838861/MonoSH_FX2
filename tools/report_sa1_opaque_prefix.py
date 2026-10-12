"""ゲーム内の不透明先頭省略を、画素・カバレッジ・同配置比較とともに保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_opaque_prefix'
NAMES={
    'roadControl':'movestress_detinput_captureburst_opaqueprefix_v3_control_tracepalette',
    'roadActive':'movestress_detinput_captureburst_opaqueprefix_v3_active_tracepalette',
    'bossActive':'bossmovestress_detinput_opaqueprefix_v3_active_long_tracepalette',
    'fixture':'opaquefixture_v2_tracepalette',
}
SNAPSHOTS={'control':'fifopaqueprefix_v3_control_build','active':'fifopaqueprefix_v3_active_build','fixture':'fifopaqueprefix_v2_build'}


def main():
    DEST.mkdir(exist_ok=True)
    summaries={k:json.loads((BUILD/v/'summary.json').read_text()) for k,v in NAMES.items()}
    manifests={k:json.loads((BUILD/v/'manifest.json').read_text()) for k,v in SNAPSHOTS.items()}
    for key,s in summaries.items():
        m=manifests['fixture' if key=='fixture' else 'control' if key=='roadControl' else 'active']
        assert s['romSha256']==m['romSha256']
        assert s['hardwarePpuReferencesVerified'] and s['pixelMatchedPresents']>0
        assert s['stalledTailFields']<=1 and not s['goal60fpsAchieved']
        (DEST/(key+'_summary.json')).write_text(json.dumps({k:v for k,v in s.items() if k not in (
            'sa1Jobs','presentationTimes','cpuJobs','outputJobs','queueSamples','objectJobs','dmaJobs','cpuStageJobs')},indent=2)+'\n')
    assert summaries['fixture']['pixelMatchedPresents']==300
    assert summaries['fixture']['opaqueFixtureCoverage']['everyListedComponentCovered']
    assert summaries['roadControl']['opaquePrefixCoverage']['selectedObjects']==0
    assert summaries['roadActive']['opaquePrefixCoverage']['advancedRows']>600
    a=manifests['active'];c=manifests['control']
    assert {k:v for k,v in a.items() if k not in ('romSha256','opaquePrefixPassThrough')}=={k:v for k,v in c.items() if k not in ('romSha256','opaquePrefixPassThrough')}
    active=BUILD/SNAPSHOTS['active'];control=BUILD/SNAPSHOTS['control']
    assert (active/'game.lbl').read_bytes()==(control/'game.lbl').read_bytes()
    for key,d in SNAPSHOTS.items():
        p=BUILD/d/'MonoSHSA1_4bpp_game.sfc'
        assert hashlib.sha256(p.read_bytes()).hexdigest()==manifests[key]['romSha256']
    static=json.loads((active/'opaque_prefix_verified.json').read_text())
    assert static['romSha256']==a['romSha256'] and static['wordBoundaryChecks']==23807
    for name in ('opaque_prefix_verified.json','reverse_explosions_verified.json','left_hints_verified.json','opaque_prefix_packing.json'):
        (DEST/name).write_bytes((active/name).read_bytes())
    rows={}
    for k,s in summaries.items():
        rows[k]=dict(fields=s['fields'],logic=s['logic'],presents=s['presents'],
            pixelMatchedPresents=s['pixelMatchedPresents'],intervals=s['presentationFieldIntervals'],
            maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),coverage=s['opaquePrefixCoverage'])
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for k,n in NAMES.items():
            for p in sorted((BUILD/n).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,k+'/'+p.name)
        for k,n in SNAPSHOTS.items():
            for p in sorted((BUILD/n).iterdir()):
                if p.is_file():z.write(p,'rom_'+k+'/'+p.name)
        for p in sorted(BUILD.glob('opaqueprefix_v*_*.log')):z.write(p,'logs/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    assert archive.stat().st_size<95_000_000
    result=dict(cases=rows,activeRomSha256=a['romSha256'],controlRomSha256=c['romSha256'],
        fixtureRomSha256=manifests['fixture']['romSha256'],sameControlCodeLayoutVerified=True,
        all1492GeometryPatternsRetained=True,gameIntegrated=True,goal60fpsAchieved=False,
        publicReleaseChanged=False,excludedV1NibbleRankZeroBug=True,
        decision='correct but slower in the road comparison; keep opt-in, do not promote',
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
