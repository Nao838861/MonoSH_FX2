"""切替準備・DMA宛先事前計算・短いI/O・転送予約の比較証拠を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_mask_bounds import compare
from report_sa1_transfer_deadline import case,records

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_flip_prepare'
BASE='movestress_detinput_captureburst_deadline_full192_tracepalette_tracebounds_tracedeadline'
BOSS_BASE='bossmovestress_detinput_deadline_full192_tracepalette_tracebounds_tracedeadline'
ROAD={v:'movestress_detinput_captureburst_flipprepare_'+v+'_tracepalette_tracebounds_tracedeadline'
    for v in ('early','gap32','prebank','prebank_short_v2','prebank16','prebank20','refresh16','tail16')}
BOSS={v:'bossmovestress_detinput_flipprepare_'+v+'_tracepalette_tracebounds_tracedeadline'
    for v in ('early','prebank20','tail16')}
FIXTURE={v:'transferfixture_flipprepare_'+v+'_tracedeadline_tracepalette_tracebounds'
    for v in ('refresh16','tail16')}


def snapshot(v):
    return 'flipprepare_'+('prebank_short' if v=='prebank_short_v2' else v)+'_build'


def checks(name):
    p=BUILD/name
    prep=records(p/'flip_preparation.jsonl');bank=records(p/'prebank_dma_verified.jsonl')
    return dict(flipPreparations=len(prep),earlyPreparations=sum(197<=x['prepareLine']<203 for x in prep),
        prebankOwnershipChecks=len(bank),prebankPages=sorted({x['page'] for x in bank}),
        prebankResumedOwnershipChecks=sum(x['cursor']>0 for x in bank))


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    roads={v:case(n,snapshot(v)) for v,n in ROAD.items()}
    for v,n in ROAD.items():
        roads[v].update(compare(n,BASE),**checks(n))
        assert roads[v]['fullFramebuffersMatchedGenerations']>=653
        assert roads[v]['reducedClearBandBounds']==0
    bosses={v:case(n,snapshot(v)) for v,n in BOSS.items()}
    for v,n in BOSS.items():
        bosses[v].update(compare(n,BOSS_BASE),**checks(n))
        assert bosses[v]['fields']==1900 and bosses[v]['pixelMatchedPresents']==147
    fixtures={v:case(n,snapshot(v)) for v,n in FIXTURE.items()}
    for v,n in FIXTURE.items():
        fixtures[v].update(**checks(n))
        fixtures[v].update(compare(n,'transferfixture_deadline_full192_tracedeadline_tracepalette_tracebounds'))
        assert fixtures[v]['prefixOracle']['partialDescriptorUses']>=120
        assert fixtures[v]['prebankResumedOwnershipChecks']>=120
        assert fixtures[v]['prebankPages']==[0,12288]
    commands=json.loads((ROOT/'game/sa1/v001/results/20261013_transfer_deadline/commands.json').read_text())
    base=commands['full192']
    variants=dict(early=base+['--early-flip-prepare'],gap32=base+['--sparse-merge-gap','32'],
        prebank_current=base+['--prebank-dma'],prebank_short=base+['--prebank-dma','--dma-short-io'])
    variants['prebank16']=variants['prebank_short']+['--dma-unroll-count','16']
    variants['prebank20']=variants['prebank_short']+['--dma-unroll-count','20']
    variants['refresh16']=variants['prebank16']+['--prefix-refresh-sixteenth']
    for option,value in (('--flip-small-reserve','1600'),('--flip-player-reserve','2400')):
        variants['refresh16'][variants['refresh16'].index(option)+1]=value
    variants['tail16']=variants['prebank16']+['--tail-flip-reserve','1400']
    # 最初の宛先移動だけの対照は、費用表の割引をまだ入れていない履歴。
    command_result=dict(variants=variants,historicalPrebankControl=dict(romSha256=roads['prebank']['romSha256'],
        prefixDescriptorCost=57,rebuildFromCurrentSource=False,
        note='現在の--prebank-dmaは命令削減に合わせ4を割り引く。初回対照ROMと実生成source・ca65引数は証拠zipに保存。'))
    (DEST/'commands.json').write_text(json.dumps(command_result,indent=2)+'\n',encoding='utf8')
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for group,names in (('road',ROAD),('boss',BOSS),('fixture',FIXTURE)):
            for v,n in names.items():
                for p in sorted((BUILD/n).iterdir()):
                    if p.is_file() and p.suffix!='.png':z.write(p,f'{group}_{v}/'+p.name)
        for v in ('early','gap32','prebank','prebank_short','prebank16','prebank20','refresh16','tail16'):
            p=BUILD/('flipprepare_'+v+'_build');m=json.loads((p/'manifest.json').read_text())
            assert hashlib.sha256((p/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==m['romSha256']
            for f in sorted(p.iterdir()):
                if f.is_file():z.write(f,'rom_'+v+'/'+f.name)
        # ROM故障ではなく、harnessがDBを誤ったstateキーで読んで停止した初回。
        invalid=BUILD/'movestress_detinput_captureburst_flipprepare_prebank_short_tracepalette_tracebounds_tracedeadline'
        for p in sorted(invalid.iterdir()):
            if p.is_file() and p.suffix!='.png':z.write(p,'harness_state_key_failure/'+p.name)
        for p in sorted(BUILD.glob('flipprepare_*_build.log')):z.write(p,'logs/'+p.name)
        for p in sorted(BUILD.glob('flipprepare_*_verified.json')):z.write(p,'verification/'+p.name)
        for p in sorted(BUILD.glob('descriptor_cost_*_analysis.json')):z.write(p,'diagnostic/'+p.name)
        z.write(BUILD/'fixed_front_mask_probe.json','diagnostic/fixed_front_mask_probe.json')
        for n in ('build_sa1_game.py','sa1_transfer_deadline.py','sa1_prebank_dma.py','sa1_prefix_refresh.py','test_sa1_game.py','report_sa1_flip_prepare.py','probe_sa1_fixed_front_mask.py'):
            z.write(ROOT/'tools'/n,'current_sources/'+n)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result=dict(roads=roads,bosses=bosses,fixtures=fixtures,
        gameIntegrated=True,allOriginalPatternsRetained=True,hostSpriteDrawingUsed=False,
        publicReleaseChanged=False,goal60fpsAchieved=False,
        evidenceBytes=archive.stat().st_size,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert result['evidenceBytes']<95_000_000
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(evidenceBytes=result['evidenceBytes'],evidenceSha256=result['evidenceSha256'],
        roads={v:{k:r[k] for k in ('presents','presentationFieldIntervals','maxSa1Ms')} for v,r in roads.items()},
        bosses={v:{k:r[k] for k in ('presents','presentationFieldIntervals','maxSa1Ms')} for v,r in bosses.items()}),indent=2))


if __name__=='__main__':main()
