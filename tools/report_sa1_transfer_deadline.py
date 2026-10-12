"""転送期限の追跡・探索短縮・一回の予算計算の証拠を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_transfer_deadline'
ROAD={v:f'movestress_detinput_captureburst_deadline_{v}_tracepalette_tracebounds_tracedeadline'
    for v in ('base','unroll','onepass_v2','full192')}
BOSS={v:f'bossmovestress_detinput_deadline_{v}_tracepalette_tracebounds_tracedeadline'
    for v in ('onepass_v2','full192')}
FIXTURE={v:f'transferfixture_deadline_{v}_tracedeadline_tracepalette_tracebounds'
    for v in ('onepass_v2','full192')}
BOSS_BASE='bossmovestress_detinput_edgeguard_large12_tracepalette_tracebounds_traceedge'


def records(path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def case(name,snapshot):
    path=BUILD/name;s=json.loads((path/'summary.json').read_text())
    m=json.loads((BUILD/snapshot/'manifest.json').read_text())
    assert s['romSha256']==m['romSha256'] and s['hardwarePpuReferencesVerified']
    assert not (path/'failure.txt').exists()
    tail_limit=max(map(int,s['presentationFieldIntervals'])) if name.startswith('transferfixture') else 1
    assert s['stalledTailFields']<=tail_limit
    assert s['maskBoundsVerified']['fullFramebufferJobs']==len(s['sa1Jobs'])
    result={k:s[k] for k in ('romSha256','fields','logic','presents','pixelMatchedPresents',
        'presentationFieldIntervals','goal60fpsAchieved')}
    result.update(scenario=name,maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
        maxOutputMs=max(j['totalOutputMs'] for j in s['outputJobs']),maskBoundsVerified=s['maskBoundsVerified'],
        stalledTailFields=s['stalledTailFields'])
    missed={f for a,b in zip(s['presentationTimes'][2:],s['presentationTimes'][3:])
        for f in range(a['visibleField']+1,b['visibleField'])}
    result['heldFields']=sorted(missed)
    if not name.startswith('transferfixture'):
        result['heldFieldQueues']=[q for q in s['queueSamples'] if q['field'] in missed]
    checks=records(path/'prefix_search_verified.jsonl')
    result['prefixOracle']=dict(uses=len(checks),partialDescriptorUses=sum(e['partial']>0 for e in checks),
        maxPartialBytes=max((e['partial'] for e in checks),default=0),maxCount=max((e['count'] for e in checks),default=0))
    events=records(path/'transfer_deadline.jsonl')
    result['deadlineTraceEvents']=len(events)
    # 予算値のavailableはpipe_reserved label時点では保存前。算出後はAにある。
    result['selectedGenerationTimeline']=[e for e in events if e['generation'] in (543,544,546,549,551)
        and e['event'] in ('pipe_prefix_plan','pipe_fast_begin','pipe_fast_partial_done',
            'pipe_transfer_pause','p3Complete','pipe_flip')]
    if name.startswith('movestress'):
        assert s['fields']==800 and s['pixelMatchedPresents']==168
        result['burstMeans']={k:sum(j[k] for j in s['sa1Jobs'][529:570])/41
            for k in ('drawMs','dirtyMs','clearMs','bgMs','totalSa1Ms')}
    if name.startswith('transferfixture'):
        assert not result['goal60fpsAchieved'] and result['pixelMatchedPresents']>=140
        assert result['prefixOracle']['partialDescriptorUses']>=120
    return result


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    snapshots=dict(base='deadline_base_build',unroll='deadline_unroll_build',
        onepass_v2='deadline_onepass_build',full192='deadline_full192_build')
    roads={v:case(n,snapshots[v]) for v,n in ROAD.items()}
    for v in ('unroll','onepass_v2','full192'):
        roads[v].update(compare(ROAD[v],ROAD['base']))
        assert roads[v]['fullFramebuffersMatchedGenerations']>=653
        assert roads[v]['reducedClearBandBounds']==0
    bosses={v:case(n,snapshots[v]) for v,n in BOSS.items()}
    for v,n in BOSS.items():
        assert bosses[v]['fields']==1900 and bosses[v]['pixelMatchedPresents']==147
        bosses[v].update(compare(n,BOSS_BASE))
    fixtures={v:case(n,snapshots[v]) for v,n in FIXTURE.items()}
    fixtures['full192'].update(compare(FIXTURE['full192'],FIXTURE['onepass_v2']))
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_edge_guard/commands.json').read_text())['large12']
    base+=['--trace-transfer-deadline']
    commands=dict(base=base,unroll=base+['--prefix-unrolled-search'])
    commands['onepass_v2']=base+['--dma-budget-table','--prefix-unrolled-search','--dma-word-start','--prefix-one-pass']
    commands['full192']=commands['onepass_v2']+['--prefix-full-reserve','192']
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    invalid=dict(all=dict(romSha256='d4250fce6173b8c8949708d715f3b71a0ddb01e55516053565a308c6845774a6',
        reason='予算表末尾でCODEへ戻さず、後続HDMA表がGSUへ移動。画像照合の成功だけで採用しない。',performanceEvidence=False),
        firstOnepass=dict(romSha256='6f5372f630040d02bcb0365cc46839f3a84342ebe29ee3439cd931a84889aba5',
            reason='同じsegment漏れ。field145 line203でHDMAが予約期間をunblankし検査が停止。',performanceEvidence=False,romSnapshotAvailable=False))
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for group,names in (('road',ROAD),('boss',BOSS),('fixture',FIXTURE)):
            for v,name in names.items():
                for p in sorted((BUILD/name).iterdir()):
                    if p.is_file() and p.suffix!='.png':z.write(p,f'{group}_{v}/'+p.name)
        for v,name in snapshots.items():
            path=BUILD/name;m=json.loads((path/'manifest.json').read_text())
            assert hashlib.sha256((path/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
            for p in sorted(path.iterdir()):
                if p.is_file():z.write(p,'rom_'+v+'/'+p.name)
        # 不合格の途中結果は採用結果と分離して保存する。
        for v,name in (('all','movestress_detinput_captureburst_deadline_all_tracepalette_tracebounds_tracedeadline'),
            ('all_fixture','transferfixture_deadline_all_tracedeadline_tracepalette_tracebounds'),
            ('first_onepass','movestress_detinput_captureburst_deadline_onepass_tracepalette_tracebounds_tracedeadline')):
            for n in ('manifest.json','game.lbl','test.lua','summary.json','failure.txt','failure_state.txt','emulator.log','transfer_deadline.jsonl','prefix_search_verified.jsonl'):
                p=BUILD/name/n
                if p.exists():z.write(p,'invalid_'+v+'/'+n)
        for p in sorted((BUILD/'deadline_all_build').iterdir()):
            if p.is_file():z.write(p,'invalid_all_build/'+p.name)
        for p in sorted(BUILD.glob('deadline_*_verified.json')):z.write(p,'verification/'+p.name)
        for p in sorted(BUILD.glob('deadline_*_build.log')):z.write(p,'logs/'+p.name)
        for n in ('sa1_prefix_unrolled.py','sa1_transfer_deadline.py','verify_sa1_prefix_unrolled.py','test_sa1_game.py'):
            z.write(ROOT/'tools'/n,'current_sources/'+n)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(roads=roads,bosses=bosses,fixtures=fixtures,invalid=invalid,
        allOriginalPatternsRetained=True,gameIntegrated=True,hostSpriteDrawingUsed=False,
        publicReleaseChanged=False,goal60fpsAchieved=False,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(evidenceBytes=result['evidenceBytes'],evidenceSha256=result['evidenceSha256'],
        roads={v:{k:r[k] for k in ('presents','presentationFieldIntervals','maxSa1Ms')} for v,r in roads.items()},
        bosses={v:{k:r[k] for k in ('presents','presentationFieldIntervals','maxSa1Ms')} for v,r in bosses.items()}),indent=2))


if __name__=='__main__':main()
