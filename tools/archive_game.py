"""検証済みROM・測定ログ・標本をgitに残せる場所へ保存する。"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics
from build_game import ROOT, BUILD, GAME

def main():
    results=GAME/'results';results.mkdir(exist_ok=True)
    release=ROOT/'releases';release.mkdir(exist_ok=True)
    names=['play','controls','pause','stumble','boss','stress','packed','objects','display','long','profile']
    summaries={}
    rom=BUILD/'MonoSHFX2_v001.sfc';rom_sha=hashlib.sha256(rom.read_bytes()).hexdigest()
    for name in names:
        src=BUILD/name
        assert not (src/'error.txt').exists(),f'failed scenario: {name}'
        summary=json.loads((src/'summary.json').read_text())
        assert summary['romSha256']==rom_sha,f'tested ROM mismatch: {name}'
        records=[json.loads(line) for line in (src/'trace.jsonl').read_text().splitlines()]
        wraps=0
        for record in records:
            for key in ['joinedMs','cpuMs','gsuMs','dmaMs','objMs']:
                if record.get(key,0)<0:
                    record[key]+=4294967296/21477.272;wraps+=1
                    assert 0<=record[key]<1000,'unexpected clock discontinuity'
        summary['clockWrapCorrections']=wraps
        # 完了時刻はDMA量によってfield境界をまたぐ。可視画像の間隔は、
        # 必ず203〜223行に来るDMA開始のfieldで数える。
        dma_fields=[r['field'] for r in records if 'dmaStartLine' in r]
        dma_fields=dma_fields[:sum('dmaMs' in r for r in records)]
        intervals=[b-a for a,b in zip(dma_fields,dma_fields[1:])]
        assert all(i>=1 for i in intervals),f'multiple presentations per field: {name}'
        summary['dmaCompletionIntervals']={k:summary[k] for k in ['interval1','interval2','interval3plus']}
        summary['interval1']=intervals.count(1)
        summary['interval2']=intervals.count(2)
        summary['interval3plus']=sum(i>=3 for i in intervals)
        summary['intervalBasis']='DMA開始field。完了時刻のfield跨ぎを除く'
        joins=[r['joinedMs'] for r in records if 'joinedMs' in r]
        dmas=[r for r in records if 'dmaMs' in r]
        summary['joinedMeanMs']=statistics.mean(joins)
        summary['joinedP95Ms']=sorted(joins)[int(len(joins)*.95)]
        cpu=[r['cpuMs'] for r in records if 'cpuMs' in r]
        if cpu:
            summary['cpuMeanMs']=statistics.mean(cpu);summary['cpuMaxMeasuredMs']=max(cpu)
        summary['gsuMeanMs']=statistics.mean(r['gsuMs'] for r in records if 'gsuMs' in r)
        summary['dmaMeanMs']=statistics.mean(r['dmaMs'] for r in dmas)
        objects=[r['objMs'] for r in records if 'objMs' in r]
        summary['objDmaMeanMs']=statistics.mean(objects)
        summary['objDmaMaxMs']=max(objects)
        summary['objDmaBytes']=68
        summary['dmaBytesMean']=statistics.mean(r['bytes'] for r in dmas)
        summary['framesPerSecondIncludingBoot']=summary['rendered']/summary['fields']*60.0988
        summary['sampledScenes']=len(list(src.glob('frame[0-9]*.bin')))
        summaries[name]=summary
        (results/f'{name}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (results/f'{name}.jsonl.gz').write_bytes(gzip.compress((src/'trace.jsonl').read_bytes(),mtime=0))
        target=results/name
        target.mkdir(exist_ok=True)
        assert target.resolve().parent==results.resolve()
        # この生成物ディレクトリの旧標本だけを除き、新旧ROMの標本を混ぜない。
        for prefix in ['frame','draw','packet','meta','display','obj','oam','objview']:
            for old in target.glob(prefix+'[0-9]*.*'):
                if old.is_file():old.unlink()
        for prefix in ['frame','draw','packet','meta','display','obj','oam','objview']:
            for sample in src.glob(prefix+'[0-9]*.*'):
                if prefix=='objview' and sample.suffix=='.rgb':continue # lossless PNGを保存する。
                target=results/name;target.mkdir(exist_ok=True);shutil.copy2(sample,target/sample.name)
        if (src/'objects_ppu.json').exists():shutil.copy2(src/'objects_ppu.json',results/name/'objects_ppu.json')
        for filename in ['field240.png','scene_boss.png','scene_enemies.png','scene_death.png','boss_state2.png','boss_state3.png']:
            path=src/filename
            if path.exists(): shutil.copy2(path,results/f'{name}_{filename}')
    assert summaries['long']['loopSeen'] and summaries['boss']['loopSeen']
    assert summaries['stress']['minBytes']==12288
    shutil.copy2(rom,release/rom.name)
    frozen=json.loads((GAME/'upstream/sources.json').read_text())
    for name,sha in frozen.items(): assert hashlib.sha256((GAME/'upstream'/name).read_bytes()).hexdigest()==sha,name
    manifest={'romSha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'romBytes':rom.stat().st_size,
              'buildMode':json.loads((BUILD/'build_mode.json').read_text()),
              'display':[256,180],'framebuffer':[256,192],'format':'2bpp','sourceSha256':frozen,
              'hardwareObjects':'自機17poseと自弾16サイズ・反射弾。最大16枠、毎frame OAM 68bytes',
              'testedEmulator':'Mesen 2.1.1, GsuClockSpeed=100, NTSC, extra scanlines=0',
              'scenarioFrames':{name:s['fields'] for name,s in summaries.items()}}
    for scenario,key in [('equivalence','equivalenceMatchedUpdates'),
                         ('equivalence_boss','bossEquivalenceMatchedUpdates')]:
        path=results/scenario/'summary.json'
        if path.exists():
            comparison=json.loads(path.read_text(encoding='utf-8'))
            if comparison['nativeRomSha256']==rom_sha:
                manifest[key]=comparison['matchedUpdates']
    (release/'v001.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(BUILD/'game.map',results/'game.map')
    shutil.copy2(BUILD/'game.lbl',results/'game.lbl')
    shutil.copy2(BUILD/'ground_projection.json',results/'ground_projection.json')
    print(json.dumps({name:round(s['framesPerSecondIncludingBoot'],2) for name,s in summaries.items()}))
    print('ROM SHA256:',manifest['romSha256'])

if __name__=='__main__': main()
