"""不透明spanの容量・正しさと、実SA-1分割probeの証拠をまとめる。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
PROBE=ROOT/'build/sa1_fragment_probe'
DEST=ROOT/'game/sa1/v001/results/20261013_opaque_spans'


def main():
    source=BUILD/'movestress_detinput_captureburst_fixedtable_v1_tracepalette'
    summary=json.loads((PROBE/'summary.json').read_text());jobs=json.loads((PROBE/'jobs.json').read_text())
    manifest=json.loads((PROBE/'manifest.json').read_text());rom=PROBE/'MonoSHSA1_fragment_probe.sfc'
    assert summary['romSha256']==manifest['romSha256']==hashlib.sha256(rom.read_bytes()).hexdigest()
    assert summary['pixelMatchedJobs']==summary['jobs']==len(jobs)==596
    assert not summary['gameIntegrated'] and not summary['goal60fpsAchieved']
    groups={}
    for name,prefix in (('pairedExplosions','a'),('roadReplay41','replay')):
        cases=[r for r in summary['comparisons'] if r['name'].startswith(prefix)]
        assert len(cases)==(108 if name=='pairedExplosions' else 41)
        group=dict(cases=len(cases),hiddenWords=sum(c['hiddenWords'] for c in cases),directHiddenWords=sum(c['directHiddenWords'] for c in cases))
        for variant in ('baseline','dma','mvn','direct'):
            group[variant+'SumMs']=sum(c[variant+'Ms'] for c in cases)
            if variant!='baseline':
                group[variant+'WeightedRatio']=group[variant+'SumMs']/group['baselineSumMs']
                group[variant+'FasterCases']=sum(c[variant+'Ratio']<1 for c in cases)
                group[variant+'RatioRange']=[min(c[variant+'Ratio'] for c in cases),max(c[variant+'Ratio'] for c in cases)]
        groups[name]=group
    feasibility=json.loads((DEST/'feasibility.json').read_text())
    assert groups['roadReplay41']['hiddenWords']==feasibility['cases'][0]['totals']['bboxSelectedHiddenWords']
    inputs=[]
    for path in sorted(source.glob('present*_meta.bin')):
        if not 530<=int(path.name[7:12])<=570:continue
        for p in (path,path.with_name(path.name.replace('_meta.bin','_fb.bin'))):
            inputs.append(dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    assert len(inputs)==82
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in PROBE.iterdir():
            if p.is_file() and p.suffix!='.bin':z.write(p,'probe/'+p.name)
        for j in jobs:
            p=PROBE/(j['name']+'.bin');assert p.stat().st_size==24576
            z.write(p,'probe/'+p.name)
        for p in inputs:z.write(source/p['name'],'input/'+p['name'])
        for name in ('MonoSHSA1_4bpp_game.sfc','manifest.json','game.lbl','compiled_game_packing.json','left_hints_packing.json','reverse_explosions_packing.json'):
            z.write(BUILD/name,'game_baseline/'+name)
        for name in ('opaque_fragment_build.log','opaque_fragment_test.log','opaque_fragment_v2_excluded_summary.json','opaque_fragment_build_v2.log','opaque_fragment_test_v2.log'):
            z.write(BUILD/name,'excluded/'+name)
        for name in ('opaque_fragment_build_v8.log','opaque_fragment_test_v8.log','opaque_spans_feasibility.log'):
            z.write(BUILD/name,'successful/'+name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(romSha256=summary['romSha256'],pixelMatchedJobs=596,groups=groups,inputHashes=inputs,
        gameIntegrated=False,goal60fpsAchieved=False,publicReleaseChanged=False,
        excludedInitialClearAndTimingRuns=True,occlusionSelectionAndTableGenerationCostIncluded=False,
        unoccludedRowRunsPrecompiled=True,noCopyChainFormationCostIncluded=False,
        decision='prefix-copy variants rejected; no-copy precompiled oracle requires a real game implementation and timing',
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(groups=groups,evidenceBytes=result['evidenceBytes'],evidenceSha256=result['evidenceSha256']))


if __name__=='__main__':main()
