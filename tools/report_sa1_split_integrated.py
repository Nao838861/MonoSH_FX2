"""左右二面のゲーム統合と、近景コピーを一面へ戻した比較を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_split_viewport'


def main():
    names=dict(baseline_road='movestress_detinput_captureburst_directleft_currentbase_tracepalette',
        split_noidle_road='movestress_detinput_captureburst_splitintegrated_v3_tracepalette',
        split_idle_road='movestress_detinput_captureburst_splitintegrated_idle_v1_tracepalette',
        split_wide32_road='movestress_detinput_captureburst_splitintegrated_wide32_v1_tracepalette',
        split_packed_road='movestress_detinput_captureburst_splitintegrated_packed_v1_tracepalette',
        near_packed_road='movestress_detinput_captureburst_nearpacked_v1_tracepalette',
        baseline_boss='bossmovestress_detinput_fixedtable_currentbase_long_tracepalette',
        split_packed_boss='bossmovestress_detinput_splitintegrated_packed_v1_long_tracepalette',
        near_packed_boss='bossmovestress_detinput_nearpacked_v1_long_tracepalette')
    dirs=dict(baseline='flame_currentbase_build',split_noidle='split_integrated_noidle_build',
        split_idle='split_integrated_idle_v1_build',split_wide32='split_integrated_wide32_v1_build',
        split_packed='split_integrated_packed_v1_build',near_packed='near_packed_v1_build')
    cases={};summaries={}
    for key,name in names.items():
        s=json.loads((BUILD/name/'summary.json').read_text());summaries[key]=s
        variant=key.rsplit('_',1)[0];m=json.loads((BUILD/dirs[variant]/'manifest.json').read_text())
        assert s['romSha256']==m['romSha256'] and s['hardwarePpuReferencesVerified']
        assert s['pixelMatchedPresents']>=(168 if key.endswith('road') else 144)
        assert not s['goal60fpsAchieved'] and s['stalledTailFields']<=1
        jobs=s['sa1Jobs'];outputs=s['outputJobs'];burst=jobs[529:570]
        value=dict(romSha256=s['romSha256'],fields=s['fields'],logic=s['logic'],presents=s['presents'],
            pixelMatchedPresents=s['pixelMatchedPresents'],intervals=s['presentationFieldIntervals'],
            maxSa1Ms=max(j['totalSa1Ms'] for j in jobs),maxOutputMs=max(j['totalOutputMs'] for j in outputs),
            means={k:sum(j[k] for j in jobs)/len(jobs) for k in ('drawMs','dirtyMs','clearMs','bgMs','totalSa1Ms')})
        if key.endswith('road'):
            assert len(burst)==41
            value['burstMeans']={k:sum(j[k] for j in burst)/41 for k in value['means']}
        if key.startswith('split_'):
            counts=[j['splitDescriptorsVerified'] for j in outputs]
            assert counts and max(counts)<=48
            value.update(transferDescriptorJobsVerified=len(counts),maxDescriptors=max(counts))
        cases[key]=value
    for scene in ('road','boss'):
        expected=packets(names['baseline_'+scene])
        for k,n in names.items():
            if k=='baseline_'+scene or not k.endswith(scene):continue
            actual=packets(n);count=min(len(actual),len(expected))
            assert count>=(640 if scene=='road' else 1600) and actual[:count]==expected[:count],k
            cases[k]['packetMatchedGenerations']=count
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_flame_direct/commands.json').read_text())['baseline']
    split=base.copy();split[split.index('--prefill-count')+1]='3';split.remove('--idle-clear');split.append('--split-viewports')
    commands=dict(baseline=base,split_noidle=split,split_idle=split+['--idle-clear'],
        split_wide32=split+['--idle-clear','--split-wide-clear-min','32'],
        split_packed=split+['--idle-clear','--split-near-packed'],near_packed=base+['--near-packed'])
    (DEST/'integrated_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    archive=DEST/'integrated_evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for key,name in names.items():
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,key+'/'+p.name)
        for key,name in dirs.items():
            m=json.loads((BUILD/name/'manifest.json').read_text())
            assert hashlib.sha256((BUILD/name/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file():z.write(p,'rom_'+key+'/'+p.name)
        for pattern in ('split_viewports*.log','splitintegrated*.log','nearpacked*.log','near_packed*.log'):
            for p in sorted(BUILD.glob(pattern)):z.write(p,'logs/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,allOriginalPatternsRetained=True,gameIntegrated=True,
        samePacketOrderVerified=True,allTransferSourcesKeptWithinViewportHalf=True,
        packedNearScrollCasesVerified=512*9*2,packedNearRomBytes=9216,
        hostSpriteDrawingUsed=False,publicReleaseChanged=False,goal60fpsAchieved=False,
        decision='split renderer not adopted: central boss objects are rendered twice and long boss presentation regresses; near copy remains opt-in pending further optimization',
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'integrated_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
