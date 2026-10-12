"""退避経路・JIT遅延・alpha帯・cache容量の統合比較を保存する。"""
import argparse,collections,hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_edge_guard'
VARIANTS=('base','dma9','lazy9','lazy13','band13','band13v2','large12')
ROAD={v:'movestress_detinput_captureburst_edgeguard_'+v+('_v2' if v=='large12' else '')+'_tracepalette_tracebounds_traceedge' for v in VARIANTS}
BOSS_BASE='bossmovestress_detinput_maskbounds_roundpacked_tracepalette_tracebounds'


def jsonlines(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def case(name,snapshot):
    path=BUILD/name;s=json.loads((path/'summary.json').read_text())
    m=json.loads((BUILD/snapshot/'manifest.json').read_text())
    assert s['romSha256']==m['romSha256'] and s['hardwarePpuReferencesVerified']
    assert s['stalledTailFields']<=1 and s['maskBoundsVerified']['fullFramebufferJobs']==len(s['sa1Jobs'])
    keys=('drawMs','dirtyMs','clearMs','bgMs','totalSa1Ms')
    result={k:s[k] for k in ('romSha256','fields','logic','presents','pixelMatchedPresents','presentationFieldIntervals','goal60fpsAchieved')}
    result.update(scenario=name,maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
        maxOutputMs=max(j['totalOutputMs'] for j in s['outputJobs']),maskBoundsVerified=s['maskBoundsVerified'])
    missing_fields={field for a,b in zip(s['presentationTimes'][2:],s['presentationTimes'][3:])
        for field in range(a['visibleField']+1,b['visibleField'])}
    result['heldFieldQueues']=[q for q in s['queueSamples'] if q['field'] in missing_fields]
    if name.startswith('movestress'):
        assert s['pixelMatchedPresents']==168 and s['fields']==800
        result['burstMeans']={k:sum(j[k] for j in s['sa1Jobs'][529:570])/41 for k in keys}
    events=jsonlines(path/'edge_cache.jsonl')
    result['edgeChunks']=len(events)
    result['cacheBytesOneDirection']=sum(e['cacheBytes'] for e in events)
    result['edgeSectionMs']=sum(e['saveMs']+e['restoreMs'] for e in events)
    # 遅延版だけ最初のコピー区間にJIT読み込み費が含まれる。区間合計はそのまま比較しない。
    result['jitLoads']=collections.Counter('cpu' if e['cpuCopy'] else 'dma' for e in jsonlines(path/'edge_jit.jsonl'))
    uses=jsonlines(path/'edge_jit_uses.jsonl')
    result['jitByteVerifiedUses']=len(uses)
    result['jitBanks']=sorted({e['bank'] for e in uses})
    result['jitWidths']=sorted({e['cacheWidth'] for e in uses})
    mode_traced="current[kind..'Mode']" in (path/'test.lua').read_text()
    result['edgeModes']=collections.Counter(e.get(k+'Mode','dma') if mode_traced else 'notLogged' for e in events for k in ('save','restore'))
    bands=jsonlines(path/'edge_band.jsonl')
    result['bandGuardChunks']=len(bands)
    result['bandGuardSmallerChunks']=sum(e['newWidth']<e['oldWidth'] for e in bands)
    result['bandGuardZeroChunks']=sum(e['newWidth']==0 for e in bands)
    big=[e for e in events if e['job']==429 and e['asset']==41]
    if name.startswith('movestress'):
        result['rightExplosion429']=dict(chunks=len(big),guardMs=sum(e['saveMs']+e['restoreMs'] for e in big),
            cacheBytesOneDirection=sum(e['cacheBytes'] for e in big))
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',choices=['large12','lazy13'],default='large12');args=ap.parse_args()
    DEST.mkdir(parents=True,exist_ok=True)
    roads={v:case(n,'edgeguard_'+v+'_build') for v,n in ROAD.items()}
    for v in VARIANTS:
        if v!='base':
            roads[v].update(compare(ROAD[v],ROAD['base']))
            assert roads[v]['exactBoundsMatchedGenerations']==653
    boss_names=dict(base=BOSS_BASE,band13='bossmovestress_detinput_edgeguard_band13_tracepalette_tracebounds_traceedge',
        candidate='bossmovestress_detinput_edgeguard_'+args.candidate+'_tracepalette_tracebounds_traceedge')
    bosses={}
    for v,n in boss_names.items():
        snap='maskbounds_roundpacked_build' if v=='base' else 'edgeguard_'+('band13' if v=='band13' else args.candidate)+'_build'
        bosses[v]=case(n,snap)
        assert bosses[v]['fields']==1900 and bosses[v]['pixelMatchedPresents']==147
        if v!='base':bosses[v].update(compare(n,BOSS_BASE))
    fixture_name='stackfixturewide_edgeguard_'+args.candidate+'_tracepalette_tracebounds_traceedge'
    fixture=case(fixture_name,'edgeguard_'+args.candidate+'_build')
    assert fixture['pixelMatchedPresents']>=300 and fixture['presents']>=300
    baseline=json.loads((ROOT/'game/sa1/v001/results/20261013_mask_bounds/commands.json').read_text())['roundpacked']
    commands={v:baseline+['--trace-edge-cache'] for v in VARIANTS}
    for v in VARIANTS:
        if v!='base':commands[v]+= ['--edge-dma-min','9' if v in ('dma9','lazy9') else '13']
        if v.startswith(('lazy','band','large')):commands[v]+=['--edge-lazy-jit']
        if v.startswith('band'):commands[v]+=['--edge-band-guard']
        if v=='large12':commands[v]+=['--edge-jit-max','12']
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        scenarios={**{v+'_road':n for v,n in ROAD.items()},**{'boss_'+v:n for v,n in boss_names.items()},'fixture':fixture_name}
        for key,name in scenarios.items():
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,key+'/'+p.name)
        for v in VARIANTS:
            path=BUILD/('edgeguard_'+v+'_build');m=json.loads((path/'manifest.json').read_text())
            assert hashlib.sha256((path/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
            for p in sorted(path.iterdir()):
                if p.is_file():z.write(p,'rom_'+v+'/'+p.name)
        for p in sorted(BUILD.glob('edgeguard_*_build.log')):z.write(p,'logs/'+p.name)
        for p in sorted(BUILD.glob('edgeguard_*_verified.json')):z.write(p,'verification/'+p.name)
        analysis=BUILD/(ROAD['base']+'_analysis.json')
        if analysis.exists():z.write(analysis,'analysis/base_guard_projection.json')
        # 最初のlarge12道中の画像検証は成功したが、mode文字列のJSON引用を修正して再実行した。
        first=BUILD/'movestress_detinput_captureburst_edgeguard_large12_tracepalette_tracebounds_traceedge'
        for n in ('test.lua','edge_cache.jsonl','summary.json','emulator.log'):
            if (first/n).exists():z.write(first/n,'logging_first/'+n)
        for p in (ROOT/'tools/sa1_edge_band_guard.py',ROOT/'game/sa1/v001/edge_band_guard_game.s'):
            z.write(p,'current_sources/'+p.name)
        z.write(BUILD/'small_edge_templates.bin','reference/small_edge_templates.bin')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(roads=roads,bosses=bosses,fixture=fixture,candidate=args.candidate,
        allOriginalPatternsRetained=True,gameIntegrated=True,hostSpriteDrawingUsed=False,
        publicReleaseChanged=False,goal60fpsAchieved=False,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
