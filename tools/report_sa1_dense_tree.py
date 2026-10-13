"""PEA/PHAによる木4の実ゲーム組込、境界修正と不採用理由を保存する。"""
import collections,hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare
from report_sa1_long_audit import audit_compare

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game';DEST=ROOT/'game/sa1/v001/results/20261014_dense_tree'
BASE='move_detinput_auditgame_reversetree_combo_v2_long4000_tracepalette_tracebounds_tracedeadline'
NORMAL='move_detinput_auditgame_densetree_v2_long4000_tracepalette_tracebounds_tracevisiblequeue'
FIXTURE='treefixture_densetree_v2_tracepalette_tracebounds'
CASES=dict(normal=NORMAL,fixture=FIXTURE,initial_smoke='move_detinput_auditgame_densetree_v1_tracepalette_tracebounds',initial_boundary_failure='treefixture_densetree_v1_tracepalette_tracebounds')


def archive(name,files):
    path=DEST/name
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for p,n in files:z.write(p,n)
    with zipfile.ZipFile(path)as z:assert z.testzip()is None
    assert path.stat().st_size<95_000_000
    return dict(file=name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    DEST.mkdir(parents=True,exist_ok=True);result={};evidence=[]
    for key,name in CASES.items():
        p=BUILD/name;s=json.loads((p/'summary.json').read_text())
        if key=='initial_boundary_failure':
            a=(p/'present00013_fb.bin').read_bytes();b=(p/'present00013_expected.bin').read_bytes()
            differences=[dict(offset=i,actual=x,expected=y)for i,(x,y)in enumerate(zip(a,b))if x!=y]
            assert differences==[dict(offset=23552,actual=0,expected=132)]
            result[key]=dict(passed=False,pixelVerificationFailure='present00013',byteDifferences=differences,
                failedRomSha256='40094cd28d216b92de09e6f675a45f58215b46d06b80a288b0c237ec1828b6cb',excludedFromPerformanceAcceptance=True)
        else:
            assert s['hardwarePpuReferencesVerified']and s['stalledTailFields']<=1
            value={k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents','presentationFieldIntervals','stalledTailFields','goal60fpsAchieved')}
            value['maxSa1Ms']=max(x['totalSa1Ms']for x in s['sa1Jobs'])
            if key in ('normal','fixture'):
                rows=[json.loads(x)for x in(p/'dense_tree.jsonl').read_text().splitlines()]
                value['runtimeStackAndCopiedPrefixVerifiedRows']=len(rows)
                value['runtimePrefixRows']=sum(x['code']==0x500 for x in rows)
                value['runtimeGuardRestorationVerified']=True
            if key=='normal':value.update(compare(name,BASE),**audit_compare(name,BASE),gameStateAudit=s['gameStateAudit'])
            if key=='fixture':assert s['pixelMatchedPresents']==1369;value['fixtureCoverage']=s['treeFixtureCoverage']
            result[key]=value
        evidence.append(archive(key+'.zip',[(f,f.name)for f in sorted(p.iterdir())if f.is_file()and f.suffix!='.png']))
    files=[]
    for version in ('v1','v2'):
        d=BUILD/f'dense_tree_{version}_build';m=json.loads((d/'manifest.json').read_text())
        assert hashlib.sha256((d/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
        files.extend((p,d.name+'/'+p.relative_to(d).as_posix())for p in sorted(d.rglob('*'))if p.is_file())
        files.append((BUILD/f'dense_tree_{version}_build.log','logs/'+f'dense_tree_{version}_build.log'))
    for n in ('build_sa1_game.py','sa1_game_compiled.py','sa1_reverse_tree.py','test_sa1_game.py','verify_sa1_dense_tree.py','verify_sa1_reverse_explosions.py','report_sa1_dense_tree.py'):
        files.append((ROOT/'tools'/n,'current_sources/'+n))
    files.append((ROOT/'game/sa1/v001/dense_stack_tree_game.s','current_sources/dense_stack_tree_game.s'))
    for n in ('build_dense_tree.py','build_dense_tree_history.py'):files.append((ROOT/'.cache'/n,'diagnostics/'+n))
    smoke=BUILD/'movestress_detinput_densetree_default_restore_tracepalette';s=json.loads((smoke/'summary.json').read_text())
    assert s['romSha256']=='a9bcd2478e39f479b641ededc38d77abe4e693d2b958d1bd7b4f7ab20af603f7'and s['pixelMatchedPresents']==120
    files.extend((p,'default_smoke/'+p.name)for p in sorted(smoke.iterdir())if p.is_file()and p.suffix!='.png')
    evidence.append(archive('roms_sources.zip',files))
    old=json.loads((BUILD/'reverse_tree_combo_v2_build/compiled_game_packing.json').read_text());new=json.loads((BUILD/'dense_tree_v2_build/compiled_game_packing.json').read_text())
    assert result['normal']['presentationFieldIntervals']=={'1':3745,'2':50,'3':1}
    result.update(evidence=evidence,normalClock=True,allOriginalPatternsRetained=True,gameIntegrated=True,
        adoptedAsDefault=False,goal60fpsAchieved=False,publicReleaseChanged=False,
        nativeCodeBytesBefore=old['nativeCodeBytes'],nativeCodeBytesAfter=new['nativeCodeBytes'],
        payloadEndBefore=old['payloadEnd'],payloadEndAfter=new['payloadEnd'])
    commands=dict(build=json.loads((BUILD/'dense_tree_commands.json').read_text()),
        normal=f'python tools/test_sa1_game.py --frames 4000 --scenario {NORMAL} --timeout 700',
        fixture=f'python tools/test_sa1_game.py --frames 2200 --presents 1369 --scenario {FIXTURE} --timeout 700')
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    (DEST/'default_restore.json').write_text(json.dumps({k:s[k]for k in ('romSha256','fields','logic','presents','pixelMatchedPresents')},indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('normal','fixture','nativeCodeBytesBefore','nativeCodeBytesAfter','payloadEndBefore','payloadEndAfter','evidence')},indent=2))


if __name__=='__main__':main()
