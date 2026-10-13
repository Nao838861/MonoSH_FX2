"""左端prefixのコピー・再利用・無効比較と、次のstack行容量を保存する。"""
import collections,hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare
from report_sa1_long_audit import audit_compare

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game';DEST=ROOT/'game/sa1/v001/results/20261013_tree_left'
BASE='move_detinput_auditgame_reversetree_combo_v2_long4000_tracepalette_tracebounds_tracedeadline'
CASES={v:'move_detinput_auditgame_treeleft_'+v+'_long4000_tracepalette_tracebounds_tracedeadline'for v in ('v1','v2','nocache_v2','bypass_v2')}
CASES.update(fixture_v1='treefixture_treeleft_v1_tracepalette_tracebounds_tracedeadline',fixture_v2='treefixture_treeleft_v2_tracepalette_tracebounds_tracedeadline')
QUEUE='move_detinput_auditgame_treeleft_reference_queue_long4000_tracepalette_tracebounds_tracevisiblequeue'


def queue_result():
    p=BUILD/QUEUE;s=json.loads((p/'summary.json').read_text())
    assert s['romSha256']=='34226b2622f640137b6ddb8f08dbb03ceeb2111155cbf1642f73caf66febf092'
    events=[json.loads(x)for x in (p/'visible_queue.jsonl').read_text().splitlines()]
    visible=[e for e in events if e['event']=='visible'];blank={e['field']:e for e in events if e['event']=='blank'}
    holds=[(a,b)for a,b in zip(visible,visible[1:])if a['presents']>=3 and a['presents']==b['presents']]
    assert len(holds)==23 and s['presentationFieldIntervals']['2']==23
    values=[]
    for a,b in holds:
        start=blank[b['field']-1]
        assert start['complete']==b['complete']==0
        kind='transfer-in-progress'if b['target']!=65535 else 'no-transfer-selected'
        if kind=='no-transfer-selected':assert start['target']==65535 and start['ready']==0 and start['rendering']==1
        values.append(dict(kind=kind,previousVisible=a,blankStart=start,visibleDeadline=b))
    counts=dict(collections.Counter(v['kind']for v in values))
    assert counts=={'transfer-in-progress':5,'no-transfer-selected':18}
    return dict(scenario=QUEUE,romSha256=s['romSha256'],fields=s['fields'],pixelMatchedPresents=s['pixelMatchedPresents'],
        holds=values,counts=counts,onlyObservedStateClassification=True,slotGenerationsNotSampled=True,
        totalRenderingAndTransferCausesNotUniquelySeparated=True,goal60fpsAchieved=False)


def case(key,name):
    p=BUILD/name;s=json.loads((p/'summary.json').read_text());assert not(p/'failure.txt').exists()
    assert s['hardwarePpuReferencesVerified']and s['stalledTailFields']<=1 and not s['goal60fpsAchieved']
    events=[json.loads(x)for x in (p/'tree_left.jsonl').read_text().splitlines()]
    counts=collections.Counter(e['event']for e in events);copies=[e for e in events if e['event']in('tree_left_copy_dma','tree_left_copy_cpu')]
    assert counts['tree_left_prefix_invoke']==counts['tree_left_prefix_done']
    # patch_completeとbuffer_readyは同じ機械語位置。cache hitでも到達する。
    assert counts['tree_left_patch_complete']==counts['tree_left_prefix_invoke']
    assert counts['tree_left_miss']==len(copies)
    assert counts['tree_left_prefix_invoke']==len(copies)+counts['tree_left_cached_ready']
    value={k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents','presentationFieldIntervals','stalledTailFields','goal60fpsAchieved')}
    value.update(scenario=name,maxSa1Ms=max(x['totalSa1Ms']for x in s['sa1Jobs']),
        events=dict(counts),copiedCodeBytes=sum(e['length']for e in copies),maximumCopiedPrefix=max((e['length']for e in copies),default=0),
        runtimePrefixBytesRtlAndGuardVerified=True)
    value['patchCompleteLabelAlsoReachedOnCacheHits']=True
    if key.startswith('fixture'):
        assert s['treeFixtureCoverage']['cases']==2736 and s['pixelMatchedPresents']==1369
        value.update(fixtureCoverage=s['treeFixtureCoverage'],fixturePresentationEveryField=s['fixturePresentationEveryField'])
    else:
        value.update(compare(name,BASE),**audit_compare(name,BASE),gameStateAudit=s['gameStateAudit'])
        assert value['fullFramebuffersMatchedGenerations']>=3831
        value['largeLeftTreeSample']=next(x for x in s['objectJobs']if x['job']==2228 and x['index']==12)
    if key=='bypass_v2':assert not events
    if key=='nocache_v2':assert not counts['tree_left_cached_ready']
    return value


def archive(path,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for p,n in files:z.write(p,n)
    with zipfile.ZipFile(path)as z:assert z.testzip()is None
    assert path.stat().st_size<95_000_000
    return dict(file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    DEST.mkdir(parents=True,exist_ok=True);cases={k:case(k,n)for k,n in CASES.items()};evidence=[]
    for k,n in CASES.items():evidence.append(archive(DEST/(k+'.zip'),[(p,p.name)for p in sorted((BUILD/n).iterdir())if p.is_file()and p.suffix!='.png']))
    queue=queue_result()
    evidence.append(archive(DEST/'visible_queue_reference.zip',[(p,p.name)for p in sorted((BUILD/QUEUE).iterdir())if p.is_file()and p.suffix!='.png']))
    (DEST/'visible_queue_analysis.json').write_text(json.dumps(queue,indent=2)+'\n')
    files=[];controls={}
    for v in ('v1','v2','nocache_v2','bypass_v2'):
        d=BUILD/('tree_left_'+v+'_build');m=json.loads((d/'manifest.json').read_text())
        assert hashlib.sha256((d/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
        files.extend((p,d.name+'/'+p.relative_to(d).as_posix())for p in sorted(d.rglob('*'))if p.is_file())
        if v in ('nocache_v2','bypass_v2'):
            controls[v]=json.loads((d/'layout_verified.json').read_text());assert controls[v]['allRuntimeLabelsIdentical']and controls[v]['changesLimitedToControlJumpAndChecksum']
    for p in sorted(BUILD.glob('tree_left_*build.log')):files.append((p,'logs/'+p.name))
    files.append((BUILD/'tree_left_fixture_object_pairs.json','analysis/tree_left_fixture_object_pairs.json'))
    for n in ('build_sa1_game.py','sa1_game_compiled.py','sa1_reverse_tree.py','test_sa1_game.py','verify_sa1_reverse_tree.py','report_sa1_tree_left.py','verify_sa1_dense_tree.py','verify_sa1_reverse_explosions.py'):
        files.append((ROOT/'tools'/n,'current_sources/'+n))
    files.append((ROOT/'game/sa1/v001/reverse_tree_left_game.s','current_sources/reverse_tree_left_game.s'))
    files.append((ROOT/'game/sa1/v001/dense_stack_tree_game.s','current_sources/dense_stack_tree_game.s'))
    for n in ('build_tree_left_variant.py','probe_tree_dense_stack.py'):files.append((ROOT/'.cache'/n,'diagnostics/'+n))
    smoke=BUILD/'movestress_detinput_treeleft_default_restore_tracepalette';s=json.loads((smoke/'summary.json').read_text())
    files.extend((p,'default_smoke/'+p.name)for p in sorted(smoke.iterdir())if p.is_file()and p.suffix!='.png')
    evidence.append(archive(DEST/'roms_sources.zip',files))
    assert s['romSha256']=='a9bcd2478e39f479b641ededc38d77abe4e693d2b958d1bd7b4f7ab20af603f7'and s['pixelMatchedPresents']==120
    public=hashlib.sha256((ROOT/'releases/MonoSHSA1_4bpp_experimental.sfc').read_bytes()).hexdigest()
    assert public=='9934d77b85913187be8d3ebd8315f854718eb24b08492204ce8b3288f620146c'
    assert cases['v2']['presents']==cases['nocache_v2']['presents']==cases['bypass_v2']['presents']
    assert cases['v2']['presentationFieldIntervals']==cases['nocache_v2']['presentationFieldIntervals']==cases['bypass_v2']['presentationFieldIntervals']
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_reverse_tree/commands.json').read_text())['combo']
    commands=dict(v1=base+['--reverse-tree-left'],v2=base+['--reverse-tree-left','--reverse-tree-left-min-bytes','13'])
    commands['nocache_v2']=commands['v2']+['--reverse-tree-left-no-cache'];commands['bypass_v2']=commands['v2']+['--reverse-tree-left-bypass']
    commands['tests']=[f'python tools/test_sa1_game.py --frames {4000 if not k.startswith("fixture")else 2200} '+('--presents 1369 'if k.startswith('fixture')else '')+f'--scenario {n} --timeout 700'for k,n in CASES.items()]
    result=dict(cases=cases,controls=controls,evidence=evidence,adoptedAsDefault=False,
        wholeGameImprovementAgainstLayoutControls=False,allOriginalPatternsRetained=True,hostSpriteDrawingUsed=False,
        gameIntegrated=True,publicReleaseChanged=False,goal60fpsAchieved=False,denseStackProbeGameIntegrated=False,visibleQueue=queue)
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    (DEST/'default_restore.json').write_text(json.dumps({k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents')},indent=2)+'\n')
    print(json.dumps(dict(cases={k:{n:v[n]for n in ('presents','presentationFieldIntervals','maxSa1Ms','copiedCodeBytes','events')}for k,v in cases.items()},evidence=evidence),indent=2))


if __name__=='__main__':main()
