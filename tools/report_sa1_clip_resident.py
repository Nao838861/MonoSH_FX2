"""I-RAM helper再利用の混在fixture・道中・ボスと遮蔽上限を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets
from test_sa1_game import verify_clip_cache_coverage

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_clip_resident'
CASES=(
    ('clipfixture_clipresident_v1_complete_tracepalette',None),
    ('movestress_detinput_captureburst_clipresident_v1_tracepalette','movestress_detinput_captureburst_fixedtable_v1_tracepalette'),
    ('bossmovestress_detinput_clipresident_v1_long_tracepalette','bossmovestress_detinput_fixedtable_long_v1_tracepalette'),
)


def main():
    base=json.loads((DEST.parent/'20261013_reverse_native/commands.json').read_text())['fiforeverseexp_v5']
    commands=dict(build=base+' --clip-resident',tests=[
        'python tools/test_sa1_game.py --frames 1000 --presents 240 --scenario '+CASES[0][0],
        'python tools/test_sa1_game.py --frames 800 --scenario '+CASES[1][0],
        'python tools/test_sa1_game.py --frames 1900 --scenario '+CASES[2][0]])
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    b=BUILD/'fifoclipresident_v1_build';m=json.loads((b/'manifest.json').read_text())
    assert m['clipResident'] and m['romSha256']==hashlib.sha256((b/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()
    for name in ('reverse_explosions_verified.json','left_hints_verified.json'):
        assert json.loads((b/name).read_text())['romSha256']==m['romSha256']
    archive=DEST/'evidence.zip';cases=[]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in b.iterdir():
            if p.is_file():z.write(p,b.name+'/'+p.name)
        for name,reference in CASES:
            d=BUILD/name;s=json.loads((d/'summary.json').read_text())
            assert s['romSha256']==m['romSha256'] and s['pixelMatchedPresents']==len(list(d.glob('present*_meta.bin')))>=120
            assert s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
            case={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','stalledTailFields','romSha256','presentationFieldIntervals')}
            case.update(scenario=name,maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']))
            if reference:
                expected=packets(reference);actual=packets(name);n=min(len(expected),len(actual));assert actual[:n]==expected[:n];case['packetMatchedGenerations']=n
            else:
                assert s['pixelMatchedPresents']>=240;case['clipCacheCoverage']=verify_clip_cache_coverage(d)
            cases.append(case)
            for p in d.iterdir():
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
        # 600field版は予定の240画面へ届かなかったため、合格根拠には使わない。
        z.write(BUILD/'clipresident_v1_mixed_fixture.log','incomplete_fixture/initial_194_presents.log')
        for p in BUILD.glob('clipresident_v1*.log'):z.write(p,'logs/'+p.name)
        source=BUILD/'movestress_detinput_captureburst_fixedtable_v1_tracepalette'
        for p in source.glob('present*_meta.bin'):
            if 530<=int(p.name[7:12])<=570:
                z.write(p,'occlusion_input/'+p.name)
                fb=p.with_name(p.name.replace('_meta.bin','_fb.bin'));z.write(fb,'occlusion_input/'+fb.name)
        z.write(source/'manifest.json','occlusion_input/manifest.json')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    assert archive.stat().st_size<95_000_000
    result=dict(cases=cases,goal60fpsAchieved=False,publicReleaseChanged=False,evidenceBytes=archive.stat().st_size,
        evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),bytes=result['evidenceBytes'],sha256=result['evidenceSha256']))


if __name__=='__main__':main()
