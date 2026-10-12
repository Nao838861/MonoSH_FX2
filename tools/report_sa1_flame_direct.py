"""現行固定map基準と、炎の直接clip表の同配置比較を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_flame_direct'


def main():
    DEST.mkdir(exist_ok=True)
    names=dict(baseline='bossmovestress_detinput_fixedtable_currentbase_long_tracepalette',
        active='bossmovestress_detinput_flamedirect_v2_long_tracepalette',
        control='bossmovestress_detinput_flamedirect_v2_control_long_tracepalette',
        fixture='leftfixtureflame_direct_v2_tracepalette')
    dirs=dict(baseline='flame_currentbase_build',active='flame_direct_v2_build',control='flame_direct_v2_control_build')
    manifests={k:json.loads((BUILD/v/'manifest.json').read_text()) for k,v in dirs.items()}
    assert (BUILD/dirs['active']/'game.lbl').read_bytes()==(BUILD/dirs['control']/'game.lbl').read_bytes()
    ar=(BUILD/dirs['active']/'MonoSHSA1_4bpp_game.sfc').read_bytes();cr=(BUILD/dirs['control']/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    diffs=[i for i,(a,c) in enumerate(zip(ar,cr)) if a!=c];assert len(diffs)<=5
    cases={}
    for key,name in names.items():
        s=json.loads((BUILD/name/'summary.json').read_text());m=manifests['active' if key=='fixture' else key]
        assert s['romSha256']==m['romSha256'] and s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
        assert s['pixelMatchedPresents']>=(300 if key=='fixture' else 146)
        if key!='fixture':assert not s['goal60fpsAchieved']
        cases[key]=dict(fields=s['fields'],logic=s['logic'],presents=s['presents'],
            intervals=s['presentationFieldIntervals'],pixelMatchedPresents=s['pixelMatchedPresents'],
            maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),coverage=s.get('flameDirectCoverage'),
            fixtureCoverage=s.get('flameFixtureCoverage'))
    assert cases['active']['coverage']['rows']>120 and cases['control']['coverage']['rows']==0
    assert cases['fixture']['fixtureCoverage']['cases']==126
    expected=packets(names['baseline'])
    for key in ('active','control'):
        actual=packets(names[key]);n=min(len(actual),len(expected));assert n>=1700 and actual[:n]==expected[:n]
        cases[key]['packetMatchedGenerations']=n
    for name in ('flame_direct_verified.json','reverse_explosions_verified.json','dirty_shapes_verified.json'):
        p=BUILD/dirs['active']/name;assert json.loads(p.read_text())['romSha256']==manifests['active']['romSha256']
        (DEST/name).write_bytes(p.read_bytes())
    (DEST/'left_hints_verified.json').write_bytes((BUILD/dirs['control']/'left_hints_verified.json').read_bytes())
    (DEST/'direct_left_capacity.json').write_bytes((BUILD/'direct_left_capacity.json').read_bytes())
    args=json.loads((BUILD/'public_build_args.json').read_text())
    (DEST/'commands.json').write_text(json.dumps(dict(baseline=args,active=args+['--flame-direct-hints'],
        control=args+['--flame-direct-hints','--flame-direct-hints-bypass']),indent=2)+'\n')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for k,n in names.items():
            for p in sorted((BUILD/n).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,k+'/'+p.name)
        for k,n in dirs.items():
            assert hashlib.sha256((BUILD/n/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==manifests[k]['romSha256']
            for p in sorted((BUILD/n).iterdir()):
                if p.is_file():z.write(p,'rom_'+k+'/'+p.name)
        for pattern in ('flame_*base*.log','flame_direct*.log','public_rebuild.log','direct_left_capacity.log'):
            for p in sorted(BUILD.glob(pattern)):z.write(p,'logs/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,romSha256={k:v['romSha256'] for k,v in manifests.items()},
        sameActiveControlCodeLayoutVerified=True,activeControlDifferentBytes=len(diffs),
        baselineIsCurrentSourceRebuild=True,baselineIsNotByteIdenticalToPublicRelease=True,
        allOriginalPatternsRetained=True,publicReleaseChanged=False,goal60fpsAchieved=False,
        fixture60fpsIsNotGameCompletionProof=True,
        decision='not adopted; no presentation improvement; test indexed initial-value tables separately',
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
