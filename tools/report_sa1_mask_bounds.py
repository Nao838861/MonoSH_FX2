"""タイル集合から消去端を求める試作の描画・転送・実速度を保存する。"""
import hashlib,json,struct,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_mask_bounds'
NAMES={v+'_road':'movestress_detinput_captureburst_maskbounds_'+('wide_v2' if v=='wide' else v)+'_tracepalette_tracebounds'
    for v in ('base','mask','wide','packed','round','roundpacked')}
BOSS=dict(base='bossmovestress_detinput_fixedtable_currentbase_long_tracepalette',
    nearpacked='bossmovestress_detinput_nearpacked_v1_long_tracepalette',
    roundpacked='bossmovestress_detinput_maskbounds_roundpacked_tracepalette_tracebounds')


def compare(name,base):
    actual=packets(name);expected=packets(base);count=min(len(actual),len(expected))
    assert actual[:count]==expected[:count],name
    a=(BUILD/name/'mask_bounds_trace.bin').read_bytes();b=(BUILD/base/'mask_bounds_trace.bin').read_bytes()
    jobs=min(len(a),len(b))//194;reduced=0;exact_bounds=0
    for i in range(jobs):
        ra=a[i*194:(i+1)*194];rb=b[i*194:(i+1)*194]
        assert ra[:98]==rb[:98],(name,i,'tile mask')
        exact_bounds+=int(ra[98:]==rb[98:])
        if '_maskbounds_round' in name:assert ra==rb,(name,i,'rounding changed bounds')
        for band in range(24):
            left,right=struct.unpack_from('<HH',ra,98+band*4)
            oldleft,oldright=struct.unpack_from('<HH',rb,98+band*4)
            assert max(0,right-left)<=max(0,oldright-oldleft),(name,i,band)
            reduced+=int(max(0,right-left)<max(0,oldright-oldleft))
    frame_jobs=0
    with (BUILD/name/'mask_bounds_frames.bin').open('rb') as f,(BUILD/base/'mask_bounds_frames.bin').open('rb') as g:
        while True:
            x=f.read(24578);y=g.read(24578)
            if not x or not y:break
            assert x==y,(name,frame_jobs+1,'full framebuffer')
            frame_jobs+=1
    assert count==frame_jobs and jobs>=count
    return dict(packetMatchedGenerations=count,tileMasksMatchedGenerations=jobs,
        fullFramebuffersMatchedGenerations=frame_jobs,reducedClearBandBounds=reduced,
        exactBoundsMatchedGenerations=exact_bounds)


def main():
    DEST.mkdir(parents=True,exist_ok=True);cases={}
    for key,name in NAMES.items():
        s=json.loads((BUILD/name/'summary.json').read_text());v,scene=key.split('_')
        snapshot='flame_currentbase_build' if v=='base' else 'maskbounds_'+v+'_build'
        m=json.loads((BUILD/snapshot/'manifest.json').read_text())
        assert s['romSha256']==m['romSha256'] and s['hardwarePpuReferencesVerified']
        assert s['maskBoundsVerified']['fullFramebufferJobs']==len(s['sa1Jobs'])
        assert s['pixelMatchedPresents']>=168
        assert s['stalledTailFields']<=1
        jobs=s['sa1Jobs'];burst=jobs[529:570]
        value=dict(scenario=name,romSha256=s['romSha256'],fields=s['fields'],logic=s['logic'],presents=s['presents'],
            pixelMatchedPresents=s['pixelMatchedPresents'],intervals=s['presentationFieldIntervals'],
            maxSa1Ms=max(j['totalSa1Ms'] for j in jobs),maxOutputMs=max(j['totalOutputMs'] for j in s['outputJobs']),
            maskBoundsVerified=s['maskBoundsVerified'],goal60fpsAchieved=s['goal60fpsAchieved'],
            means={k:sum(j[k] for j in jobs)/len(jobs) for k in ('drawMs','dirtyMs','clearMs','bgMs','totalSa1Ms')})
        if scene=='road':value['burstMeans']={k:sum(j[k] for j in burst)/len(burst) for k in value['means']}
        if v!='base':value.update(compare(name,NAMES['base_'+scene]))
        cases[key]=value
    boss={}
    expected=packets(BOSS['base'])
    for v,name in BOSS.items():
        s=json.loads((BUILD/name/'summary.json').read_text())
        assert s['hardwarePpuReferencesVerified'] and s['pixelMatchedPresents']==147 and s['fields']==1900
        assert s['stalledTailFields']<=1
        actual=packets(name);count=min(len(actual),len(expected))
        assert count>=1740 and actual[:count]==expected[:count]
        boss[v]=dict(scenario=name,romSha256=s['romSha256'],presents=s['presents'],
            intervals=s['presentationFieldIntervals'],pixelMatchedPresents=s['pixelMatchedPresents'],
            maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
            maxOutputMs=max(j['totalOutputMs'] for j in s['outputJobs']),
            packetMatchedGenerations=count,goal60fpsAchieved=s['goal60fpsAchieved'])
    assert boss['roundpacked']['romSha256']==cases['roundpacked_road']['romSha256']
    base=json.loads((ROOT/'game/sa1/v001/results/20261013_flame_direct/commands.json').read_text())['baseline']
    commands=dict(base=base,mask=base+['--mask-bounds'],wide=base+['--mask-bounds','--mask-bounds-wide-table'],
        packed=base+['--mask-bounds','--mask-bounds-wide-table','--near-packed'],
        round=base+['--dirty-tile-round'],roundpacked=base+['--dirty-tile-round','--near-packed'])
    (DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for key,name in NAMES.items():
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,key+'/'+p.name)
        for key,name in BOSS.items():
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file() and p.suffix!='.png':z.write(p,'boss_'+key+'/'+p.name)
        for name in ('flame_currentbase_build',*('maskbounds_'+v+'_build' for v in ('mask','wide','packed','round','roundpacked'))):
            m=json.loads((BUILD/name/'manifest.json').read_text())
            assert hashlib.sha256((BUILD/name/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
            for p in sorted((BUILD/name).iterdir()):
                if p.is_file():z.write(p,'rom_'+name+'/'+p.name)
        for pattern in ('maskbounds_*_build.log','maskbounds_wide_first_failure.*'):
            for p in sorted(BUILD.glob(pattern)):z.write(p,'logs/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(cases=cases,boss=boss,gameIntegrated=True,allOriginalPatternsRetained=True,
        hostSpriteDrawingUsed=False,roadAllCommonFullFramebuffersVerified=True,
        roadAllCommonTileMasksVerified=True,bossAllCommonPacketsVerified=True,
        publicReleaseChanged=False,
        goal60fpsAchieved=False,
        decision='mask-derived bounds not adopted: slower dirty planning and no presentation gain; tile rounding remains opt-in pending complete game audit',
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
