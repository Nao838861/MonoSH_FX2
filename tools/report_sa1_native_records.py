"""native行を再利用する右hint別表と左定数のbyte探索を比較する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets
from test_sa1_game import verify_minimum_clip_coverage

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_native_records'
VARIANTS={
    'reversenative79_v1':['--reverse-explosions-min-width','79','--reverse-records-native','--reverse-full-row-fast'],
    'reversenative76_v2':['--reverse-explosions-min-width','76','--reverse-records-native','--reverse-full-row-fast','--reverse-hints-compressed'],
    'leftbytescan_v1':['--left-byte-constant-scan'],
}


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    base=json.loads((DEST.parent/'20261013_reverse_native/commands.json').read_text())['fiforeverseexp_v5']
    commands={name:base+' '+' '.join(flags) for name,flags in VARIANTS.items()}
    commands['excluded_reversenative76_v1']=base+' --reverse-explosions-min-width 76 --reverse-records-native --reverse-full-row-fast'
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    reference=packets('movestress_detinput_captureburst_fixedtable_v1_tracepalette')
    archive=DEST/'evidence.zip';cases=[];packing={}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in VARIANTS:
            b=BUILD/('fifo'+name+'_build');m=json.loads((b/'manifest.json').read_text())
            sha=hashlib.sha256((b/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest();assert sha==m['romSha256']
            for proof in ('reverse_explosions_verified.json','left_hints_verified.json'):
                assert json.loads((b/proof).read_text())['romSha256']==sha
            packing[name]=json.loads((b/'reverse_explosions_packing.json').read_text())
            for p in b.iterdir():
                if p.is_file():z.write(p,b.name+'/'+p.name)
            fixture=('leftfixtureexplosion_' if name=='leftbytescan_v1' else 'stackfixturemin_')+name+'_tracepalette'
            for scenario in (fixture,'movestress_detinput_captureburst_'+name+'_tracepalette'):
                d=BUILD/scenario;s=json.loads((d/'summary.json').read_text())
                assert s['romSha256']==sha and s['pixelMatchedPresents']==len(list(d.glob('present*_meta.bin')))>=120
                assert s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
                case={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','romSha256','stalledTailFields','presentationFieldIntervals')}
                case.update(scenario=scenario,buildCommand=commands[name],maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']))
                if scenario.startswith('stackfixturemin'):
                    case['minimumClipCoverage']=verify_minimum_clip_coverage(d,m)
                elif scenario.startswith('movestress'):
                    actual=packets(scenario);n=min(len(reference),len(actual));assert actual[:n]==reference[:n];case['packetMatchedGenerations']=n
                cases.append(case)
                for p in d.iterdir():
                    if p.is_file() and p.suffix!='.rgb':z.write(p,scenario+'/'+p.name)
            for p in BUILD.glob(name+'*.log'):z.write(p,'logs/'+p.name)
        z.write(BUILD/'reversenative76_v1_build.log','excluded_capacity_failure/reversenative76_v1_build.log')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    assert archive.stat().st_size<95_000_000
    result=dict(cases=cases,packing=packing,goal60fpsAchieved=False,publicReleaseChanged=False,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert hashlib.sha256((ROOT/'releases/MonoSHSA1_4bpp_experimental.sfc').read_bytes()).hexdigest()=='9934d77b85913187be8d3ebd8315f854718eb24b08492204ce8b3288f620146c'
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),bytes=result['evidenceBytes'],sha256=result['evidenceSha256']))


if __name__=='__main__':main()
