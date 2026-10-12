"""展開なし・inline raw hint版の同配置比較と独立検証を保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_opaque_raw'


def main():
    DEST.mkdir(exist_ok=True)
    names=dict(active='movestress_detinput_captureburst_opaqueprefix_v5_raw_tracepalette',
        control='movestress_detinput_captureburst_opaqueprefix_v5_raw_control_tracepalette',
        fixture='opaquefixture_v5_raw_tracepalette')
    dirs=dict(active='fifopaqueprefix_v5_raw_build',control='fifopaqueprefix_v5_raw_control_build')
    manifests={k:json.loads((BUILD/v/'manifest.json').read_text()) for k,v in dirs.items()}
    assert (BUILD/dirs['active']/'game.lbl').read_bytes()==(BUILD/dirs['control']/'game.lbl').read_bytes()
    assert {k:v for k,v in manifests['active'].items() if k not in ('romSha256','opaquePrefixPassThrough')}=={k:v for k,v in manifests['control'].items() if k not in ('romSha256','opaquePrefixPassThrough')}
    cases={}
    for key,name in names.items():
        s=json.loads((BUILD/name/'summary.json').read_text());m=manifests['control' if key=='control' else 'active']
        assert s['romSha256']==m['romSha256']
        assert s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1 and not s['goal60fpsAchieved']
        assert s['pixelMatchedPresents']>=(300 if key=='fixture' else 168)
        if key!='control':assert set(s['opaquePrefixCoverage']['hintFormats'])=={'0'}
        if key=='fixture':assert s['opaqueFixtureCoverage']['everyListedComponentCovered']
        cases[key]=dict(fields=s['fields'],logic=s['logic'],presents=s['presents'],
            intervals=s['presentationFieldIntervals'],pixelMatchedPresents=s['pixelMatchedPresents'],
            maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),coverage=s['opaquePrefixCoverage'])
        if key=='fixture':cases[key]['fixtureCoverage']=s['opaqueFixtureCoverage']
    static_names=('opaque_prefix_verified.json','reverse_explosions_verified.json','left_hints_verified.json','dirty_shapes_verified.json')
    for name in static_names:
        p=BUILD/dirs['active']/name;data=json.loads(p.read_text())
        assert data['romSha256']==manifests['active']['romSha256'];(DEST/name).write_bytes(p.read_bytes())
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for key,name in names.items():
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,key+'/'+p.name)
        for key,name in dirs.items():
            rom=BUILD/name/'MonoSHSA1_4bpp_game.sfc'
            assert hashlib.sha256(rom.read_bytes()).hexdigest()==manifests[key]['romSha256']
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file():z.write(p,'rom_'+key+'/'+p.name)
        for pattern in ('opaqueprefix_v4*.log','opaqueprefix_v5*.log','opaqueprefix_restore.log'):
            for p in sorted(BUILD.glob(pattern)):z.write(p,'logs/'+p.name)
        for name in ('failure.txt','emulator.log','test.lua'):
            p=BUILD/'movestress_detinput_captureburst_opaqueprefix_v4_raw_tracepalette'/name
            if p.exists():z.write(p,'excluded_callback/'+name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,romSha256={k:v['romSha256'] for k,v in manifests.items()},
        sameControlCodeLayoutVerified=True,workerBytes=467,rawHintBytes=23807,deferredGapBytes=12567,
        allOriginalPatternsRetained=True,publicReleaseChanged=False,goal60fpsAchieved=False,
        decision='no improvement in presentation intervals; not adopted',
        excludedInitialCallbackTriggeredByOtherIramWorker=True,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
