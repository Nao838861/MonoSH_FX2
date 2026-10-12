"""爆発のstack描画とclip hint圧縮の実測・停止修正の証拠を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_stack_explosions'
CASES=(
    ('fifostackexp_v1','movestress_detinput_captureburst_fifostackexp_v1_tracepalette'),
    ('fifostackexp_v2','movestress_detinput_captureburst_fifostackexp_v2_tracepalette'),
    ('fifostackexp_v3','movestress_detinput_captureburst_fifostackexp_v3_tracepalette'),
    ('fifostackexp_v4','movestress_detinput_captureburst_stackexp_v4_tracepalette'),
    ('fifostackexpcompressed_v1','movestress_detinput_captureburst_stackexpcompressed_v1_tracepalette'),
    (None,'stackfixture_stackexp_v4_tracepalette'),
    (None,'leftfixture_stackcompressed_v1_tracepalette'),
    (None,'stackfixture_stackcompressed_v1_tracepalette'),
)


def main():
    DEST.mkdir(exist_ok=True,parents=True)
    reference=packets('movestress_detinput_captureburst_fixedtable_v1_tracepalette')
    cases=[]
    commands=json.loads((DEST/'commands.json').read_text())
    with zipfile.ZipFile(DEST/'evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for snapshot,name in CASES:
            d=BUILD/name;s=json.loads((d/'summary.json').read_text())
            assert s['pixelMatchedPresents']==len(list(d.glob('present*_meta.bin')))>=120
            assert s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
            result=dict(scenario=name,maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
                **{k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','hardwarePpuReferencesVerified','stalledTailFields','romSha256','presentationFieldIntervals')})
            if snapshot:
                actual=packets(name);n=min(len(reference),len(actual));assert reference[:n]==actual[:n]
                result['packetMatchedGenerations']=n
                result['buildCommand']=commands[snapshot]
                b=BUILD/(snapshot+'_build');m=json.loads((b/'manifest.json').read_text())
                assert m['romSha256']==s['romSha256']
                assert hashlib.sha256((b/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==s['romSha256']
                for p in b.iterdir():
                    if p.is_file():z.write(p,b.name+'/'+p.name)
            cases.append(result)
            for p in d.iterdir():
                if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
        # 画素一致172枚だけでは通過しない。停止した旧版は比較から除外して明記する。
        failures=[]
        for version in (2,3):
            name=f'stackfixture_stackexp_v{version}_tracepalette';d=BUILD/name
            s=json.loads((d/'summary.json').read_text())
            assert s['presents']==172 and s['stalledTailFields']>1
            failures.append(dict(scenario=name,presents=s['presents'],stalledTailFields=s['stalledTailFields'],passed=False))
            for n in ('summary.json','manifest.json','emulator.log'):
                if (d/n).exists():z.write(d/n,'failed/'+name+'/'+n)
        for dname in ('stackdebug_v3','stackdebug_baseline'):
            for name in ('bad_iram.bin','bad_state.txt','exec_ring.jsonl','debug.log'):
                p=BUILD/dname/name
                if p.exists():z.write(p,'failed/'+dname+'/'+name)
        for name in ('stack_rows_verified.json','hint_compression_capacity.json'):
            p=BUILD/name
            if p.exists():z.write(p,name)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,failedFixtures=failures,goal60fpsAchieved=False,publicReleaseChanged=False,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(dict(cases=len(cases),archiveBytes=result['evidenceBytes'],sha256=result['evidenceSha256']))


if __name__=='__main__':main()
