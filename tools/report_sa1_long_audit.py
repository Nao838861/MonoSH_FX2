"""長時間のゲーム進行と、狭い右端prefix試作の証拠を保存する。"""
import collections,hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_long_audit'
CASES=dict(
 road_base='move_detinput_auditgame_long4000_tracepalette_tracebounds_tracedeadline',
 boss_base='bossmovestress_detinput_auditgame_long4000_tracepalette_tracebounds_tracedeadline',
 road_v1='move_detinput_auditgame_rightnarrow_v1_long4000_tracepalette_tracebounds_tracedeadline',
 boss_v1='bossmovestress_detinput_auditgame_rightnarrow_v1_long5000_tracepalette_tracebounds_tracedeadline',
 road_v2='move_detinput_auditgame_rightnarrow_v2_long4000_tracepalette_tracebounds_tracedeadline',
 boss_v2='bossmovestress_detinput_auditgame_rightnarrow_v2_long5000_tracepalette_tracebounds_tracedeadline')


def records(path):return [json.loads(x)for x in path.read_text().splitlines()]if path.exists()else []


def audit_compare(name,base):
    a=records(BUILD/name/'game_state_audit.jsonl');b=records(BUILD/base/'game_state_audit.jsonl')
    count=min(len(a),len(b));keys=set(a[0])-{'field','clock'}
    assert all({k:x[k]for k in keys}=={k:y[k]for k in keys}for x,y in zip(a[:count],b[:count]))
    return dict(gameStatesMatchedCompletedUpdates=count)


def case(key,name):
    p=BUILD/name;s=json.loads((p/'summary.json').read_text());assert not(p/'failure.txt').exists()
    assert s['hardwarePpuReferencesVerified']and s['stalledTailFields']<=1 and not s['goal60fpsAchieved']
    assert s['maskBoundsVerified']['fullFramebufferJobs']==len(s['sa1Jobs'])
    audit=records(p/'game_state_audit.jsonl')
    transitions=[{k:x[k]for k in ('logic','field','playerState','bossState','bossHp')}for i,x in enumerate(audit)
        if i==0 or(x['playerState'],x['bossState'])!=(audit[i-1]['playerState'],audit[i-1]['bossState'])]
    value={k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents',
        'presentationFieldIntervals','stalledTailFields','gameStateAudit','maskBoundsVerified','goal60fpsAchieved')}
    value.update(scenario=name,maxSa1Ms=max(x['totalSa1Ms']for x in s['sa1Jobs']),
        maxOutputMs=max(x['totalOutputMs']for x in s['outputJobs']),stateTransitions=transitions,
        worstSa1Jobs=[dict(generation=i+1,**x)for i,x in sorted(enumerate(s['sa1Jobs']),key=lambda v:v[1]['totalSa1Ms'],reverse=True)[:5]])
    events=records(p/'right_narrow.jsonl');jobs=[x for x in events if x['event']=='right_narrow_entry']
    rows=[x for x in events if x['event']=='right_narrow_ready']
    value['rightNarrowCoverage']=dict(objects=len(jobs),rows=len(rows),assets=sorted({x['asset']for x in jobs}),
        maximumCopiedPrefixBytes=max((x['length']for x in rows),default=0))
    if key.endswith('v2'):assert set(value['rightNarrowCoverage']['assets'])<=set((0,2,3,5))and all(248<=x['left']<256 for x in jobs)
    if key=='road_v2':assert jobs
    if key.startswith('road'):assert s['gameStateAudit']['playerStates']==[0,1,2]and not s['gameStateAudit']['invulnerabilityInjected']
    if key.startswith('boss_v'):assert s['gameStateAudit']['bossStates']==[0,1,2,3]and s['gameStateAudit']['minimumBossHp']==0
    if key.startswith('boss'):
        times=[x['visibleField']for x in s['presentationTimes'][2:]if x['visibleField']<=4000]
        value['first4000FieldIntervals']=dict(collections.Counter(str(b-a)for a,b in zip(times,times[1:])))
    if key.endswith(('v1','v2')):
        base=CASES['boss_base'if key.startswith('boss')else 'road_base']
        value.update(compare(name,base),**audit_compare(name,base))
    return value


def archive(path,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for source,name in files:z.write(source,name)
    with zipfile.ZipFile(path)as z:assert z.testzip()is None
    assert path.stat().st_size<95_000_000
    return dict(file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    DEST.mkdir(parents=True,exist_ok=True);cases={k:case(k,n)for k,n in CASES.items()}
    evidence=[]
    for key,name in CASES.items():
        files=[(p,p.name)for p in sorted((BUILD/name).iterdir())if p.is_file()and p.suffix!='.png']
        evidence.append(archive(DEST/(key+'.zip'),files))
    files=[]
    for name in ('long4000_full192_build','right_narrow_v1_build','right_narrow_v2_build'):
        d=BUILD/name;m=json.loads((d/'manifest.json').read_text())
        assert hashlib.sha256((d/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
        files.extend((p,name+'/'+p.relative_to(d).as_posix())for p in sorted(d.rglob('*'))if p.is_file())
    for n in ('long4000_full192_build.log','right_narrow_v1_build.log','right_narrow_v2_build.log',
        'near_row8_v1_build.log','right_narrow_object_comparison.json'):
        files.append((BUILD/n,'diagnostics/'+n))
    for n in ('build_sa1_game.py','test_sa1_game.py','sa1_right_narrow.py','verify_sa1_right_clip.py',
        'probe_sa1_near_row8_capacity.py','report_sa1_long_audit.py'):
        files.append((ROOT/'tools'/n,'current_sources/'+n))
    files.append((ROOT/'.cache/reverify_long_audit.py','diagnostics/reverify_long_audit.py'))
    files.append((ROOT/'.cache/reverse_tree_capacity_probe.py','diagnostics/reverse_tree_capacity_probe.py'))
    files.append((ROOT/'build/game_v001/assets4/background4.bin','probe_input/background4.bin'))
    smoke=BUILD/'movestress_detinput_longaudit_default_restore_tracepalette'
    files.extend((p,'default_smoke/'+p.name)for p in sorted(smoke.iterdir())if p.is_file()and p.suffix!='.png')
    evidence.append(archive(DEST/'roms_and_sources.zip',files))
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_transfer_deadline/commands.json').read_text())['full192']
    commands=dict(base=base,v1=base+['--right-narrow-prefix'],v2=base+['--right-narrow-prefix','--right-narrow-scenery'],
        tests=[f'python tools/test_sa1_game.py --frames {cases[k]["fields"]} --timeout 700 --scenario {name}'for k,name in CASES.items()],
        static='python tools/verify_sa1_right_clip.py --narrow',probe='python tools/probe_sa1_near_row8_capacity.py',
        report='python tools/report_sa1_long_audit.py')
    result=dict(cases=cases,evidence=evidence,allOriginalPatternsRetained=True,hostSpriteDrawingUsed=False,
        gameIntegrated=True,publicReleaseChanged=False,goal60fpsAchieved=False,
        bossScenarioStageForcedAndInvulnerable=True,bossScenarioNaturalEndingNotVerified=True,
        hostAuditInitialFailurePreserved=True,nearRow8ProbeGameIntegrated=False)
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    s=json.loads((smoke/'summary.json').read_text());assert s['romSha256']=='a9bcd2478e39f479b641ededc38d77abe4e693d2b958d1bd7b4f7ab20af603f7'
    public=hashlib.sha256((ROOT/'releases/MonoSHSA1_4bpp_experimental.sfc').read_bytes()).hexdigest()
    assert public=='9934d77b85913187be8d3ebd8315f854718eb24b08492204ce8b3288f620146c'
    assert s['fields']==280 and s['pixelMatchedPresents']==120 and s['hardwarePpuReferencesVerified']
    restored={k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents','presentationFieldIntervals')}
    restored.update(publicRomSha256=public,maxSa1Ms=max(x['totalSa1Ms']for x in s['sa1Jobs']))
    (DEST/'default_restore.json').write_text(json.dumps(restored,indent=2)+'\n')
    print(json.dumps(dict(cases={k:{n:x[n]for n in ('presents','presentationFieldIntervals','maxSa1Ms','rightNarrowCoverage')}for k,x in cases.items()},evidence=evidence),indent=2))


if __name__=='__main__':main()
