"""草木の左端を2B表と共有初期値辞書で処理した試験を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_direct_left'


def main():
    DEST.mkdir(exist_ok=True)
    names=dict(baseline_road='movestress_detinput_captureburst_directleft_currentbase_tracepalette',
        active_road='movestress_detinput_captureburst_directleft_v2_tracepalette',
        baseline_boss='bossmovestress_detinput_fixedtable_currentbase_long_tracepalette',
        active_boss='bossmovestress_detinput_directleft_v2_long_tracepalette',
        fixture='leftfixtureindexed_directleft_v2_tracepalette')
    dirs=dict(baseline='flame_currentbase_build',active='direct_left_v2_build')
    manifests={k:json.loads((BUILD/v/'manifest.json').read_text()) for k,v in dirs.items()}
    cases={}
    for key,name in names.items():
        s=json.loads((BUILD/name/'summary.json').read_text())
        m=manifests['baseline' if key.startswith('baseline') else 'active']
        assert s['romSha256']==m['romSha256'] and s['hardwarePpuReferencesVerified'] and s['stalledTailFields']<=1
        assert s['pixelMatchedPresents']>=(1600 if key=='fixture' else 146)
        if key!='fixture':assert not s['goal60fpsAchieved']
        cases[key]=dict(fields=s['fields'],logic=s['logic'],presents=s['presents'],
            intervals=s['presentationFieldIntervals'],pixelMatchedPresents=s['pixelMatchedPresents'],
            maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),coverage=s.get('directLeftCoverage'),
            fixtureCoverage=s.get('directLeftFixtureCoverage'))
    for scene in ('road','boss'):
        expected=packets(names['baseline_'+scene]);actual=packets(names['active_'+scene])
        n=min(len(actual),len(expected));assert n>=(640 if scene=='road' else 1700) and actual[:n]==expected[:n]
        cases['active_'+scene]['packetMatchedGenerations']=n
    assert cases['active_road']['coverage']['rows']==1394
    assert cases['fixture']['fixtureCoverage']==dict(cases=2898,fullCartesianProductVerified=True)
    for name in ('left_hints_verified.json','reverse_explosions_verified.json','dirty_shapes_verified.json'):
        p=BUILD/dirs['active']/name;assert json.loads(p.read_text())['romSha256']==manifests['active']['romSha256']
        (DEST/name).write_bytes(p.read_bytes())
    static=json.loads((DEST/'left_hints_verified.json').read_text())
    assert static['symbolicClipBoundaryChecks']==140509 and static['arbitraryFramebufferInputsVerified']
    args=json.loads((ROOT/'game/sa1/v001/results/20261013_flame_direct/commands.json').read_text())['baseline']
    (DEST/'commands.json').write_text(json.dumps(dict(baseline=args,active=args+['--direct-left-hints']),indent=2)+'\n')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for k,n in names.items():
            for p in sorted((BUILD/n).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,k+'/'+p.name)
        for k,n in dirs.items():
            assert hashlib.sha256((BUILD/n/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==manifests[k]['romSha256']
            for p in sorted((BUILD/n).iterdir()):
                if p.is_file():z.write(p,'rom_'+k+'/'+p.name)
        for p in sorted(BUILD.glob('direct_left*.log')):z.write(p,'logs/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,romSha256={k:v['romSha256'] for k,v in manifests.items()},
        baselineIsCurrentSourceRebuild=True,baselineIsNotByteIdenticalToPublicRelease=True,
        allOriginalPatternsRetained=True,publicReleaseChanged=False,goal60fpsAchieved=False,
        fixture60fpsIsNotGameCompletionProof=True,
        fixtureInitialCoverageCheckFailedThenHostCheckRepaired=True,
        decision='not adopted; road presentation regression; no grass path executed in boss comparison',
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
