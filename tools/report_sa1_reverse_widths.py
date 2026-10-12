"""右端逆順描画の対象寸法・hint圧縮・6byte行情報の比較を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets
from test_sa1_game import verify_minimum_clip_coverage

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_reverse_widths'
VARIANTS={
    'reverse88_v1':['--reverse-explosions-min-width','88'],
    'reverse88_v2':['--reverse-explosions-min-width','88','--reverse-hints-compressed'],
    'reverse88_v3':['--reverse-explosions-min-width','88','--reverse-records-compact'],
    'reverse85_v1':['--reverse-explosions-min-width','85','--reverse-records-compact'],
    'reverse82_v1':['--reverse-explosions-min-width','82','--reverse-records-compact','--reverse-hints-compressed'],
    'reverse82_v2':['--reverse-explosions-min-width','82','--reverse-records-compact','--reverse-hints-compressed','--reverse-full-row-fast'],
}


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    base=json.loads((DEST.parent/'20261013_reverse_native/commands.json').read_text())['fiforeverseexp_v5']
    commands={'fifo'+name:base+' '+' '.join(flags) for name,flags in VARIANTS.items()}
    commands['excluded_reverse79_v1']=base+' --reverse-explosions-min-width 79 --reverse-records-compact --reverse-hints-compressed --reverse-full-row-fast'
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    reference=packets('movestress_detinput_captureburst_fixedtable_v1_tracepalette')
    cases=[];archives=[]
    for name in VARIANTS:
        snapshot=BUILD/('fifo'+name+'_build');m=json.loads((snapshot/'manifest.json').read_text())
        sha=hashlib.sha256((snapshot/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()
        assert sha==m['romSha256']
        for proof in ('reverse_explosions_verified.json','left_hints_verified.json'):
            assert json.loads((snapshot/proof).read_text())['romSha256']==sha
        scenarios=['stackfixturemin_'+name+'_tracepalette']
        if name!='reverse88_v3':scenarios.append('movestress_detinput_captureburst_'+name+'_tracepalette')
        archive=DEST/(name+'_evidence.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in snapshot.iterdir():
                if p.is_file():z.write(p,snapshot.name+'/'+p.name)
            for scenario in scenarios:
                d=BUILD/scenario;s=json.loads((d/'summary.json').read_text())
                assert s['romSha256']==sha and s['pixelMatchedPresents']==len(list(d.glob('present*_meta.bin')))>=120
                assert s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
                case={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','stalledTailFields','romSha256','presentationFieldIntervals')}
                case.update(scenario=scenario,buildCommand=commands['fifo'+name],maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']))
                if scenario.startswith('stackfixturemin'):
                    case['minimumClipCoverage']=verify_minimum_clip_coverage(d,m)
                else:
                    actual=packets(scenario);n=min(len(reference),len(actual));assert actual[:n]==reference[:n]
                    case['packetMatchedGenerations']=n
                cases.append(case)
                for p in d.iterdir():
                    if p.is_file() and p.suffix!='.rgb':z.write(p,scenario+'/'+p.name)
            for p in BUILD.glob(name+'*.log'):z.write(p,'logs/'+p.name)
            if name=='reverse82_v2':
                z.write(BUILD/'reverse79_v1_build.log','excluded_capacity_failure/reverse79_v1_build.log')
                z.write(BUILD/'host_access_violations_20261013.txt','excluded_host_runs/windows_access_violations.txt')
        with zipfile.ZipFile(archive) as z:assert z.testzip() is None
        assert archive.stat().st_size<95_000_000
        archives.append(dict(file=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
        print(name,archives[-1]['bytes'],flush=True)
    previous=BUILD/'movestress_detinput_captureburst_reverseexp_v5_retry2_tracepalette/summary.json'
    public=ROOT/'releases/MonoSHSA1_4bpp_experimental.sfc'
    assert hashlib.sha256(public.read_bytes()).hexdigest()=='9934d77b85913187be8d3ebd8315f854718eb24b08492204ce8b3288f620146c'
    result=dict(cases=cases,archives=archives,goal60fpsAchieved=False,publicReleaseChanged=False,
        previousV5Road={k:v for k,v in json.loads(previous.read_text()).items() if k in ('romSha256','logic','presents','pixelMatchedPresents','presentationFieldIntervals')},
        excludedCapacityFailure='reverse79_v1_build.log')
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
