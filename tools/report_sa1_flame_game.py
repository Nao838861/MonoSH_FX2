"""炎3位相の左端描画と、投影表WRAM配置を長いボス戦で比較する。"""
import hashlib,json,struct,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_flame_inline'
CASES=(
    ('fiforeverseexp_v5','bossmovestress_detinput_reverseexp_v5_long_tracepalette'),
    ('fifoflameinline_v1','bossmovestress_detinput_flameinline_v1_long_tracepalette'),
    ('fifoflameinline_v2','bossmovestress_detinput_flameinline_v2_long_tracepalette'),
    (None,'leftfixtureflame_flameinline_v1_complete_tracepalette'),
)


def phase_coverage():
    d=BUILD/CASES[-1][1];actual=set()
    for p in d.glob('present*_meta.bin'):
        raw=p.read_bytes();count=struct.unpack_from('<H',raw,6)[0]
        for i in range(count):
            x,bottom,w,h,asset,flags,z,priority=struct.unpack_from('<hh6B',raw,10+i*10)
            if asset==31:actual.add((w,h,flags,x,bottom))
    expected={(w,h,phase,x,bottom) for w,h in ((64,63),(66,65)) for phase in range(3) for x in (-40,0,16,30,64,128,250) for bottom in (40,120,205)}
    assert actual==expected
    return dict(cases=len(actual),geometryPatterns=2,colorPhases=[0,1,2],allCentersAndBottomsRetained=True)


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    commands=json.loads((DEST/'commands.json').read_text());cases=[]
    reference=packets('bossmovestress_detinput_fixedtable_long_v1_tracepalette')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for snapshot,name in CASES:
            d=BUILD/name;s=json.loads((d/'summary.json').read_text())
            assert s['pixelMatchedPresents']==len(list(d.glob('present*_meta.bin')))>=120
            assert s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
            case={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','romSha256','presentationFieldIntervals','stalledTailFields')}
            case.update(scenario=name,maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']))
            if snapshot:
                actual=packets(name);n=min(len(reference),len(actual));assert actual[:n]==reference[:n]
                case.update(packetMatchedGenerations=n,buildCommand=commands[snapshot])
                b=BUILD/(snapshot+'_build');m=json.loads((b/'manifest.json').read_text())
                assert m['romSha256']==s['romSha256']==hashlib.sha256((b/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()
                for p in b.iterdir():
                    if p.is_file():z.write(p,b.name+'/'+p.name)
            for p in d.iterdir():
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
            cases.append(case)
        z.write(BUILD/'bossmovestress_detinput_fixedtable_long_v1_tracepalette/summary.json','previous_public_reference/summary.json')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,flameFixture=phase_coverage(),goal60fpsAchieved=False,publicReleaseChanged=False,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),bytes=result['evidenceBytes'],sha256=result['evidenceSha256']))


if __name__=='__main__':main()
