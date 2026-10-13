"""木4の逆順描画、同配置の無効比較、bank読出しの修正を保存する。"""
import collections,hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare
from report_sa1_long_audit import audit_compare

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_reverse_tree'
BASE='move_detinput_auditgame_long4000_tracepalette_tracebounds_tracedeadline'
BOSS_BASE='bossmovestress_detinput_auditgame_rightnarrow_v2_long5000_tracepalette_tracebounds_tracedeadline'
NAMES=dict(fixed='move_detinput_auditgame_reversetree_v2_long4000_tracepalette_tracebounds_tracedeadline',
 bypass='move_detinput_auditgame_reversetree_bypass_v2_long4000_tracepalette_tracebounds_tracedeadline',
 combo='move_detinput_auditgame_reversetree_combo_v2_long4000_tracepalette_tracebounds_tracedeadline',
 fixture='treefixture_reversetree_combo_v2_tracepalette_tracebounds_tracedeadline',
 boss='bossmovestress_detinput_auditgame_reversetree_combo_v2_long5000_tracepalette_tracebounds_tracedeadline')


def records(p):return [json.loads(x)for x in p.read_text().splitlines()]if p.exists()else []


def case(key,name):
    p=BUILD/name;s=json.loads((p/'summary.json').read_text());assert not(p/'failure.txt').exists()
    assert s['hardwarePpuReferencesVerified']and s['stalledTailFields']<=1 and not s['goal60fpsAchieved']
    result={k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents','presentationFieldIntervals','stalledTailFields','goal60fpsAchieved')}
    result.update(scenario=name,maxSa1Ms=max(x['totalSa1Ms']for x in s['sa1Jobs']),
        worstJobs=[dict(generation=i+1,**x)for i,x in sorted(enumerate(s['sa1Jobs']),key=lambda v:v[1]['totalSa1Ms'],reverse=True)[:5]],
        maxActiveCpuLogicMs=max(x['activeLogicMs']for x in s['cpuJobs']))
    t=s['presentationTimes'];result['heldGenerations']=[dict(nextGeneration=i+1,previousField=a['visibleField'],nextField=b['visibleField'])
        for i,(a,b)in enumerate(zip(t[2:],t[3:]),start=3)if b['visibleField']-a['visibleField']>1]
    events=records(p/'tree_right.jsonl');enters=[e for e in events if e['event']=='sa1_reverse_tree_right'];rows=[e for e in events if e['event']=='tree_right_invoke']
    result['treeCoverage']=dict(objects=len(enters),rows=len(rows),rowsSkippingHiddenCode=sum(e['entry']>e['code']for e in rows))
    if key in ('fixed','bypass','combo','boss'):
        base=BOSS_BASE if key=='boss'else BASE
        result.update(compare(name,base),**audit_compare(name,base),gameStateAudit=s['gameStateAudit'])
        assert result['fullFramebuffersMatchedGenerations']>=3826 and result['reducedClearBandBounds']==0
    if key in ('bypass','boss'):assert not rows
    if key=='fixture':
        assert s['treeFixtureCoverage']['cases']==2736 and s['pixelMatchedPresents']==1369
        result.update(treeFixtureCoverage=s['treeFixtureCoverage'],fixturePresentationEveryField=s['fixturePresentationEveryField'])
    return result


def archive(path,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for p,name in files:z.write(p,name)
    with zipfile.ZipFile(path)as z:assert z.testzip()is None
    assert path.stat().st_size<95_000_000
    return dict(file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    DEST.mkdir(parents=True,exist_ok=True);cases={k:case(k,n)for k,n in NAMES.items()};evidence=[]
    for key,name in NAMES.items():
        evidence.append(archive(DEST/(key+'.zip'),[(p,p.name)for p in sorted((BUILD/name).iterdir())if p.is_file()and p.suffix!='.png']))
    layout=json.loads((BUILD/'reverse_tree_bypass_v2_build/bypass_layout_verified.json').read_text())
    assert layout['changedBytes']==10 and layout['allLabelsIdentical']and layout['changesLimitedToSixByteDispatchAndChecksum']
    files=[]
    for name in ('reverse_tree_v1_build','reverse_tree_v2_build','reverse_tree_bypass_v2_build','reverse_tree_combo_v2_build'):
        d=BUILD/name;m=json.loads((d/'manifest.json').read_text())
        assert hashlib.sha256((d/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
        files.extend((p,name+'/'+p.relative_to(d).as_posix())for p in sorted(d.rglob('*'))if p.is_file())
    for name in ('move_detinput_auditgame_reversetree_v1_long4000_tracepalette_tracebounds_tracedeadline',
        'treefixture_reversetree_v1_tracepalette_tracebounds_tracedeadline','reversetree_v1_failure_trace_v3','reversetree_v1_safe_observer600'):
        files.extend((p,'historical/'+name+'/'+p.name)for p in sorted((BUILD/name).iterdir())if p.is_file()and p.suffix!='.png')
    for p in sorted(BUILD.glob('reverse_tree_*_build.log')):files.append((p,'logs/'+p.name))
    for n in ('build_sa1_game.py','sa1_game_compiled.py','sa1_left_hints.py','sa1_reverse_tree.py','test_sa1_game.py',
        'verify_sa1_reverse_tree.py','verify_sa1_reverse_explosions.py','verify_sa1_dirty_shapes.py','probe_sa1_dirty_read_guard.py','report_sa1_reverse_tree_game.py'):
        files.append((ROOT/'tools'/n,'current_sources/'+n))
    files.append((ROOT/'game/sa1/v001/reverse_tree_game.s','current_sources/reverse_tree_game.s'))
    for n in ('build_reverse_tree_variant.py','trace_reverse_tree_failure.py','replay_tree_v1_safe_observer.py','probe_tree_left_prefix_reuse.py'):
        files.append((ROOT/'.cache'/n,'diagnostics/'+n))
    smoke=BUILD/'movestress_detinput_reversetree_default_restore_tracepalette'
    files.extend((p,'default_smoke/'+p.name)for p in sorted(smoke.iterdir())if p.is_file()and p.suffix!='.png')
    evidence.append(archive(DEST/'roms_sources_history.zip',files))
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_transfer_deadline/commands.json').read_text())['full192']
    commands=dict(fixed=base+['--reverse-tree'],bypass=base+['--reverse-tree','--reverse-tree-bypass'],
        combo=base+['--reverse-tree','--right-narrow-prefix','--right-narrow-scenery'],
        tests=[f'python tools/test_sa1_game.py --frames {cases[k]["fields"] if k!="fixture"else 2200} '+('--presents 1369 'if k=='fixture'else '')+f'--scenario {n} --timeout 700'for k,n in NAMES.items()],
        historical='v1はpaddingなしの旧ROMが正本。現在の--reverse-treeは修正版。保存ROMとLuaで再生する。')
    samples=[];old=json.loads((BUILD/BASE/'summary.json').read_text())
    for k,name in NAMES.items():
        if k not in ('fixed','bypass','combo'):continue
        new=json.loads((BUILD/name/'summary.json').read_text());a={(x['job'],x['index']):x for x in new['objectJobs']}
        for job,index in ((2619,9),(2617,8),(2228,12)):
            before=next(x for x in old['objectJobs']if(x['job'],x['index'])==(job,index));after=a[job,index]
            assert all(before[n]==after[n]for n in ('asset','width','height','x','bottom'))
            samples.append(dict(variant=k,job=job,index=index,before=before,after=after))
    restored=json.loads((smoke/'summary.json').read_text());public=hashlib.sha256((ROOT/'releases/MonoSHSA1_4bpp_experimental.sfc').read_bytes()).hexdigest()
    assert restored['romSha256']=='a9bcd2478e39f479b641ededc38d77abe4e693d2b958d1bd7b4f7ab20af603f7'and restored['pixelMatchedPresents']==120
    assert public=='9934d77b85913187be8d3ebd8315f854718eb24b08492204ce8b3288f620146c'
    result=dict(cases=cases,bypassLayout=layout,objectTimingPairsAboveHalfMillisecond=samples,evidence=evidence,
        allOriginalPatternsRetained=True,hostSpriteDrawingUsed=False,publicReleaseChanged=False,goal60fpsAchieved=False,
        initialFailureCauseNotUniquelyEstablished=True,oldRomSafeObserver600Passed=True,
        bankOverreadIndependentlyVerifiedAndGuarded=True,bossIsForcedStageAndInvulnerable=True)
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf8')
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    (DEST/'default_restore.json').write_text(json.dumps({k:restored[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents')},indent=2)+'\n')
    print(json.dumps(dict(cases={k:{n:v[n]for n in ('presents','presentationFieldIntervals','maxSa1Ms','treeCoverage')}for k,v in cases.items()},evidence=evidence),indent=2))


if __name__=='__main__':main()
