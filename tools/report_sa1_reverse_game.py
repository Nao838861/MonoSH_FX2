"""逆順native行と左右clipポインタの実測・全画素検証を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_reverse_native'
CASES=(
    *[(f'fiforeverseexp_v{v}',f'movestress_detinput_captureburst_reverseexp_v{v}_tracepalette') for v in range(1,5)],
    ('fiforeverseexp_v5','movestress_detinput_captureburst_reverseexp_v5_retry2_tracepalette'),
    (None,'stackfixturewide_reverseexp_v1_tracepalette'),
    (None,'leftfixtureexplosion_reverseexp_v3_tracepalette'),
    (None,'leftfixtureexplosion_reverseexp_v4_tracepalette'),
    (None,'stackfixturewide_reverseexp_v4_tracepalette'),
    (None,'stackfixturewide_reverseexp_v5_tracepalette'),
)


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    commands=json.loads((DEST/'commands.json').read_text())
    reference=packets('movestress_detinput_captureburst_fixedtable_v1_tracepalette')
    cases=[]
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for snapshot,name in CASES:
            d=BUILD/name;s=json.loads((d/'summary.json').read_text())
            assert s['pixelMatchedPresents']==len(list(d.glob('present*_meta.bin')))>=120
            assert s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
            case={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','stalledTailFields','romSha256','presentationFieldIntervals')}
            case.update(scenario=name,maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']))
            if snapshot:
                actual=packets(name);n=min(len(reference),len(actual));assert actual[:n]==reference[:n]
                case.update(packetMatchedGenerations=n,buildCommand=commands[snapshot])
                b=BUILD/(snapshot+'_build');m=json.loads((b/'manifest.json').read_text())
                assert m['romSha256']==s['romSha256']==hashlib.sha256((b/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()
                for p in b.iterdir():
                    if p.is_file():z.write(p,b.name+'/'+p.name)
            cases.append(case)
            for p in d.iterdir():
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
        # 完走しなかったホスト実行は性能比較・正しさの根拠から除外する。
        for name in ('reverseexp_v5_test.log','reverseexp_v5_retry_test.log'):
            z.write(BUILD/name,'excluded_host_runs/'+name)
        for name in ('reverseexp_v4_static.log','reverseexp_v4_hints_static.log'):
            z.write(BUILD/name,'static/'+name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,goal60fpsAchieved=False,publicReleaseChanged=False,
        excludedHostRuns=['reverseexp_v5_test.log','reverseexp_v5_retry_test.log'],
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),archiveBytes=result['evidenceBytes'],sha256=result['evidenceSha256']))


if __name__=='__main__':main()
