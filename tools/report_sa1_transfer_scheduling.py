"""収集時期・部分転送の予約・先行IRQと、実DMA時間の検証を保存する。"""
import collections,hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare
from report_sa1_transfer_deadline import case,records

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_transfer_scheduling'
BASE='movestress_detinput_captureburst_deadline_full192_tracepalette_tracebounds_tracedeadline'
STEMS=('collectschedule_v2','collectschedule_tail16_v1','request190_v1','prearm190_v2','prearm196_v1','partialbudget900_tail16_v2')
ROAD={v:'movestress_detinput_captureburst_'+v+'_tracepalette_tracebounds_tracedeadline'+('_tracedmacost' if v=='partialbudget900_tail16_v2' else '')for v in STEMS}
DMA='movestress_detinput_captureburst_dma_cost_base_v2_tracepalette_tracebounds_tracedeadline_tracedmacost'
BOSS='bossmovestress_detinput_partialbudget900_tail16_v2_tracepalette_tracebounds_tracedeadline'
FIXTURE='transferfixture_partialbudget900_tail16_v2_tracedeadline_tracepalette_tracebounds'
REPLAY='movestress_detinput_captureburst_stale_budget_replay_v1_tracepalette_tracebounds_tracedeadline_tracedmacost'


def collection_checks(name):
    data=records(BUILD/name/'collect_scheduling.jsonl')
    if not data:return {}
    published=[x for x in data if x['event']=='publish'];skipped=[x for x in data if x['event']=='skipped']
    assert [x['generation']for x in published]==list(range(1,len(published)+1))
    return dict(publishedGenerations=len(published),publishedFromMain=sum(x['irq']==0 for x in published),
        skippedCollectionCalls=len(skipped),skippedWhileCompletionPending=sum(x['pending']==1 and x['done']==1 for x in skipped),
        urgentCalls=sum(x['event']=='urgent'for x in data))


def request_checks(name):
    data=records(BUILD/name/'transfer_request_verified.jsonl')
    if not data:return {}
    return dict(requestEvents=dict(collections.Counter(x['event']for x in data)),
        lateRequestScanlines=sorted({x['line']for x in data if x['event']=='late'}))


def timing():
    path=BUILD/DMA;data=records(path/'dma_cost_verified.jsonl');events=records(path/'transfer_deadline.jsonl')
    manifest=json.loads((path/'manifest.json').read_text());assert not manifest.get('prebankDma')
    oracle=[x for x in records(path/'prefix_search_verified.jsonl')if 660<=x['field']<=720]
    begins=[x for x in events if x['event']=='pipe_fast_begin'];assert len(oracle)==len(begins)
    rows=[];excluded=[]
    for begin,selection in zip(begins,oracle):
        assert begin['field']==selection['field'] and begin['cursor']//6==selection['start']
        end=next((x for x in events if x['clock']>begin['clock']and x['event']=='pipe_fast_groups_done'),None)
        if end is None:
            assert begin['field']==720
            excluded.append(dict(generation=begin['generation'],reason='trace window ends during group'));continue
        block=[x for x in data if begin['clock']<=x['clock']<end['clock']]
        count=selection['last']-selection['start']
        assert len(block)==count and sum(x['bytes']for x in block)==selection['bytes']
        assert all(x['generation']==begin['generation']for x in block)
        actual=end['clock']-begin['clock'];predicted=sum(x['bytes']+x['bytes']//32+x['bytes']//128+57 for x in block)*8
        rows.append(dict(generation=begin['generation'],field=begin['field'],line=begin['line'],
            bytes=selection['bytes'],descriptors=count,actualTicks=actual,estimatedTicks=predicted,errorTicks=actual-predicted))
    assert len(data)==1400 and len(rows)==80 and len(excluded)==1
    return dict(romSha256=manifest['romSha256'],individualDmaSamples=len(data),completeGroups=len(rows),
        groupSelectionAndByteCountsVerified=True,groupMinimumErrorTicks=min(x['errorTicks']for x in rows),
        groupMaximumErrorTicks=max(x['errorTicks']for x in rows),rows=rows,excluded=excluded,
        note='個別sampleはSTY直前から、DMA後の次のLDAを実行し終えた位置まで。groupは設定・NMI/HDMA/refresh等を含む。描画代行なし。')


def fixture():
    path=BUILD/FIXTURE;s=json.loads((path/'summary.json').read_text())
    assert not (path/'failure.txt').exists() and s['fields']==500 and s['hardwarePpuReferencesVerified']
    assert s['pixelMatchedPresents']==s['presents'] and not s['goal60fpsAchieved']
    checks=records(path/'prefix_search_verified.jsonl')
    assert sum(x['partial']>0 for x in checks)>0
    result={k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents','presentationFieldIntervals','stalledTailFields','goal60fpsAchieved')}
    result.update(compare(FIXTURE,'transferfixture_deadline_full192_tracedeadline_tracepalette_tracebounds'))
    result.update(prefixUses=len(checks),resumedPartialDescriptorUses=sum(x['partial']>0 for x in checks),
        maxPartialBytes=max(x['partial']for x in checks),maxSa1Ms=max(x['totalSa1Ms']for x in s['sa1Jobs']))
    return result


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    roads={v:case(n,v+'_build')for v,n in ROAD.items()}
    for v,n in ROAD.items():
        roads[v].update(compare(n,BASE),**collection_checks(n),**request_checks(n))
        assert roads[v]['fullFramebuffersMatchedGenerations']>=653 and roads[v]['reducedClearBandBounds']==0
    baseline=case(DMA,'dma_cost_base_v1_build');baseline.update(compare(DMA,BASE))
    boss=case(BOSS,'partialbudget900_tail16_v2_build')
    boss.update(compare(BOSS,'bossmovestress_detinput_deadline_full192_tracepalette_tracebounds_tracedeadline'))
    assert boss['fields']==1900 and boss['pixelMatchedPresents']==147
    replay=BUILD/REPLAY;failure=(replay/'failure.txt').read_text()
    assert 'VRAM DMA began outside actual blank period' in failure
    state=dict(line.split('=',1)for line in (replay/'failure_state.txt').read_text().splitlines())
    assert int(state['ppu.scanline'])==25
    replay_manifest=json.loads((replay/'manifest.json').read_text())
    assert replay_manifest['romSha256']=='5668da59d649d520af70b0fcbaa5b00d15af3f3e849cb7b1c369817db0618f65'
    result=dict(roads=roads,baseline=baseline,boss=boss,fixture=fixture(),dmaTiming=timing(),
        rejectedStaleBudgetReplay=dict(romSha256=replay_manifest['romSha256'],firstFailure=failure,
            scanline=int(state['ppu.scanline']),masterClock=int(state['masterClock']),firstFailurePreserved=True,performanceEvidence=False),
        gameIntegrated=True,allOriginalPatternsRetained=True,hostSpriteDrawingUsed=False,publicReleaseChanged=False,goal60fpsAchieved=False)
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_transfer_deadline/commands.json').read_text())['full192']
    tail=['--prebank-dma','--dma-short-io','--dma-unroll-count','16','--tail-flip-reserve','1400']
    commands=dict(baseline=base,collectschedule_v2=base+['--defer-ready-collect'],
        collectschedule_tail16_v1=base+['--defer-ready-collect']+tail,
        request190_v1=base+['--transfer-request-line','190'],prearm190_v2=base+['--prearm-transfer-line','190'],
        prearm196_v1=base+['--prearm-transfer-line','196'],partialbudget900_tail16_v2=base+['--partial-transfer-reserve','900']+tail)
    (DEST/'commands.json').write_text(json.dumps(dict(current=commands,historical=dict(
        staleBudgetReplay='診断scriptでpipe_time_left先頭のraw予算ゼロ化だけを除いた旧ROMを再生成し、SHA一致を確認する。通常build引数だけでは再現しない。',
        partial1300And900='旧resetなしのsource。各保存ROM/生成sourceが正本。現在のsourceで同じSHAへ戻ると主張しない。')),indent=2)+'\n',encoding='utf8')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        names={**ROAD,'baseline':DMA,'boss':BOSS,'fixture':FIXTURE,'rejected_replay':REPLAY}
        for key,name in names.items():
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file()and p.suffix!='.png':z.write(p,key+'/'+p.name)
        snapshots=[v+'_build'for v in STEMS]+['dma_cost_base_v1_build','stale_budget_replay_v1_build']
        for name in snapshots:
            path=BUILD/name;m=json.loads((path/'manifest.json').read_text())
            assert hashlib.sha256((path/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
            for p in sorted(path.iterdir()):
                if p.is_file():z.write(p,'rom_'+name+'/'+p.name)
        historical=('partialbudget1300_v1','partialbudget900_v1','partialbudget900_tail16_v1','prearm190_v1','collectschedule_v1')
        for stem in historical:
            name='movestress_detinput_captureburst_'+stem+'_tracepalette_tracebounds_tracedeadline'
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file()and p.suffix!='.png':z.write(p,'historical_'+stem+'/'+p.name)
            for p in sorted((BUILD/(stem+'_build')).iterdir()):
                if p.is_file():z.write(p,'historical_rom_'+stem+'/'+p.name)
        for n in ('reverse_explosions_verified.json','dirty_shapes_verified.json','dma_interval_diagnostic.json','plane_pair_delta_probe.json'):
            z.write(BUILD/n,'verification/'+n)
        for n in ('replay_stale_budget.py','plane_pair_probe.py'):
            z.write(ROOT/'.cache'/n,'diagnostic_scripts/'+n)
        for pattern in ('collectschedule_*_build.log','partialbudget*_build.log','request190*_build.log','prearm*_build.log','dma_cost*_build.log','stale_budget_replay*_build.log'):
            for p in sorted(BUILD.glob(pattern)):z.write(p,'logs/'+p.name)
        for n in ('build_sa1_game.py','sa1_collect_schedule.py','sa1_partial_budget.py','sa1_prearm_transfer.py','sa1_transfer_deadline.py','test_sa1_game.py','verify_sa1_prefix_unrolled.py','report_sa1_transfer_scheduling.py'):
            z.write(ROOT/'tools'/n,'current_sources/'+n)
    with zipfile.ZipFile(archive)as z:assert z.testzip()is None
    result.update(evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(evidenceBytes=result['evidenceBytes'],evidenceSha256=result['evidenceSha256'],
        roads={v:{k:r[k]for k in ('presents','presentationFieldIntervals','maxSa1Ms')}for v,r in roads.items()},
        boss={k:boss[k]for k in ('presents','presentationFieldIntervals','maxSa1Ms')},fixture=result['fixture']),indent=2))


if __name__=='__main__':main()
