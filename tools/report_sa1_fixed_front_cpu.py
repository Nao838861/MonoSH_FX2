"""前面差分の転送リストをS-CPUで作る費用を、単発ROMの実行結果から保存する。"""
import hashlib,json,re,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare
from test_sa1_game import verify_mask_bounds

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_front_cpu'
BASE='movestress_detinput_captureburst_deadline_full192_tracepalette_tracebounds_tracedeadline'


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    mask_probe=json.loads((BUILD/'fixed_front_mask_probe.json').read_text())
    expected={r['generation']:r for r in mask_probe['rows']}
    cases={};commands={}
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_transfer_deadline/commands.json').read_text())['full192']
    for g in (543,546,549):
        snapshot=BUILD/f'frontprobe_sample{g}_final_build'
        name=f'movestress_detinput_captureburst_frontprobe_sample{g}_final_tracepalette_tracebounds_tracedeadline'
        path=BUILD/name;result=json.loads((path/'probe_result.json').read_text())
        manifest=json.loads((snapshot/'manifest.json').read_text());rom=(snapshot/'MonoSHSA1_4bpp_game.sfc').read_bytes()
        assert result['romSha256']==manifest['romSha256']==hashlib.sha256(rom).hexdigest()
        assert manifest['fixedFrontProbeGeneration']==g and result['runtimeMasksDescriptorsPrefixesRegistersVerified']
        assert result['stoppedBeforeReturningToDisplayPath'] and not result['goal60fpsAchieved']
        assert not (path/'failure.txt').exists()
        labels={n:int(a,16) for a,n in re.findall(r'al (\w+) \.(\S+)',(snapshot/'game.lbl').read_text())}
        assert labels['fp_probe_begin']>>16==1 and labels['__RODATA_LOAD__']==0xc20000
        assert labels['blank_table']<65536
        probe=result['probe'];e=expected[g]
        assert (probe['bytes'],probe['cost'],probe['count'],probe['gap'])==tuple(e['frontUnion'][k] for k in ('bytes','estimatedCost','descriptors','mergeGap'))
        result.update(compare(name,BASE),maskBoundsVerified=verify_mask_bounds(path,False))
        assert result['fullFramebuffersMatchedGenerations']==g and result['reducedClearBandBounds']==0
        result['backUnion']=e['backUnion'];result['savedBytes']=e['savedBytes']
        result['savedEstimatedCost']=e['savedCost']
        # 費用単位はDMAの8 master clocks。実転送時間差を測った値ではない。
        result['savedEstimatedDmaMs']=e['savedCost']*8/21477.272
        result['probeToEstimatedSavingRatio']=probe['totalMs']/result['savedEstimatedDmaMs']
        result['staticPrefixVerification']=json.loads((snapshot/'prefix_search_static_verified.json').read_text())
        cases[str(g)]=result
        commands[str(g)]=dict(build=base+['--fixed-front-probe','--fixed-front-probe-generation',str(g)],
            test=['tools/test_sa1_game.py','--frames','800','--scenario',name,'--timeout','300'])
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf8')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for g in (543,546,549):
            for dirname in (f'frontprobe_sample{g}_final_build',f'movestress_detinput_captureburst_frontprobe_sample{g}_final_tracepalette_tracebounds_tracedeadline'):
                for p in sorted((BUILD/dirname).iterdir()):
                    if p.is_file() and p.suffix!='.png':z.write(p,dirname+'/'+p.name)
        for v in ('','_v2','_v3','_v4','_v5'):
            name=f'movestress_detinput_captureburst_frontprobe_cpu{v}_tracepalette_tracebounds_tracedeadline'
            for p in sorted((BUILD/name).iterdir()):
                if p.name in ('test.lua','failure.txt','failure_state.txt','end_state.txt','emulator.log','manifest.json','game.lbl','fixed_front_probe.jsonl'):
                    z.write(p,'rejected_'+(v or 'v1')+'/'+p.name)
        # 連続試作は画面切替期限を越える。ROMと当時の生成sourceを残し採用しない。
        for p in sorted((BUILD/'frontprobe_cpu_v5_build').iterdir()):
            if p.is_file():z.write(p,'rejected_continuous_rom/'+p.name)
        z.write(BUILD/'fixed_front_mask_probe.json','diagnostic/fixed_front_mask_probe.json')
        for n in ('build_sa1_game.py','test_sa1_game.py','report_sa1_fixed_front_cpu.py'):
            z.write(ROOT/'tools'/n,'sources/'+n)
        z.write(ROOT/'game/sa1/v001/fixed_front_probe_cpu.s','sources/fixed_front_probe_cpu.s')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,gameIntegratedFrontUpdates=False,diagnosticOnly=True,goal60fpsAchieved=False,
        allOriginalPatternsRetained=True,hostSpriteDrawingUsed=False,publicReleaseChanged=False,
        decision='S-CPUで毎フレーム前面差分listを構築する方式は費用過大のため不採用。SA-1側へ移せば改善するかは未検証。',
        rejectedContinuous=dict(romSha256='cdac4f519256f11f431bbcd48340e87e233ef573b95fbb522a9072622d4bc2d5',
            reason='field384/line27の表示中にpage flipし、既存harnessが停止。60fps/正常表示の証拠に使わない。'),
        invalidBootAttempts='v1は存在しない81:xxxxミラーを呼び、v2はRODATA位置、v3はBSSゼロ初期化を壊した。初期失敗は速度証拠から除外。v4のDMA完了前観測はNOPを追加し、final3本で再検査。',
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(cases={g:dict(cpuMs=v['probe']['totalMs'],savedEstimatedDmaMs=v['savedEstimatedDmaMs'],matched=v['fullFramebuffersMatchedGenerations'])for g,v in cases.items()},evidenceBytes=result['evidenceBytes'],evidenceSha256=result['evidenceSha256']),indent=2))


if __name__=='__main__':main()
