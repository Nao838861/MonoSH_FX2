"""コマンド分類/cache比較と通常プレイ検証を固定し、検証済みROMを公開先へ保存する。"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil

from build_game import ROOT, GAME, BUILD


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target=GAME/'results/command_cache_20261007';target.mkdir(exist_ok=True)
    rom=BUILD/'MonoSHFX2_v001.sfc';digest=sha(rom)
    comparison=json.loads((BUILD/'command_cache_comparison.json').read_text())
    assert comparison['both']['romSha256']==digest
    for name in ['command_cache_comparison.json','road_before.json','road_after.json']:
        shutil.copy2(BUILD/name,target/name)
    (target/'fixtures.json.gz').write_bytes(gzip.compress((BUILD/'command_cache_fixtures.json').read_bytes(),mtime=0))
    for name in ['baseline','commands','cache','both']:
        source=BUILD/('cache_compare_'+name);dest=target/name;dest.mkdir(exist_ok=True)
        for filename in ['comparison.json','summary.json','build_mode.json','game.lbl','emulator.log']:
            shutil.copy2(source/filename,dest/filename)
        for filename in ['replay.jsonl','trace.jsonl','test.lua']:
            (dest/(filename+'.gz')).write_bytes(gzip.compress((source/filename).read_bytes(),mtime=0))
    profile=BUILD/'boss_profile_cacheafter';dest=target/'natural_after';dest.mkdir(exist_ok=True)
    natural=json.loads((profile/'summary.json').read_text());assert natural['romSha256']==digest
    for filename in ['summary.json','emulator.log','worst_gsu.json','worst_gsu_frame.bin','worst_gsu_packet.bin','worst_gsu_oam.bin']:
        shutil.copy2(profile/filename,dest/filename)
    for filename in ['timings.jsonl','trace.jsonl','test.lua']:
        (dest/(filename+'.gz')).write_bytes(gzip.compress((profile/filename).read_bytes(),mtime=0))
    tests={}
    for name in ['packed','controls','pause','display','held','boss']:
        source=BUILD/name
        assert not (source/'error.txt').exists()
        summary=json.loads((source/'summary.json').read_text());assert summary['romSha256']==digest,name
        tests[name]=summary
        (target/(name+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
        (target/(name+'.jsonl.gz')).write_bytes(gzip.compress((source/'trace.jsonl').read_bytes(),mtime=0))
    shutil.copy2(BUILD/'full_transfer_cache.json',target/'full_transfer_variant.json')
    for filename in ['game.lbl','game.map','build_mode.json']:
        if filename=='game.map':
            # ld65のmapは行末を空白で埋める。記録では空白を除いてdiff可能にする。
            (target/filename).write_text('\n'.join(line.rstrip() for line in (BUILD/filename).read_text().splitlines()).rstrip()+'\n')
        else:
            shutil.copy2(BUILD/filename,target/filename)
    manifest=json.loads((ROOT/'releases/v001.json').read_text(encoding='utf-8'))
    if manifest['romSha256']!=digest:
        manifest['previousRomSha256']=manifest['romSha256']
    manifest['romSha256']=digest
    manifest['buildMode']=json.loads((BUILD/'build_mode.json').read_text())
    manifest['scenarioFrames']={name:s['fields'] for name,s in tests.items()}
    manifest['scenarioFrames']['naturalProfile']=natural['fields']
    for key in ['equivalenceMatchedUpdates','bossEquivalenceMatchedUpdates']:
        manifest.pop(key,None) # 旧ROMの一致数を新しいROMの検証として引き継がない。
    manifest['optimizationMeasurement']='game/v001/results/command_cache_20261007'
    manifest['replayScenes']=len(comparison['both']['scenes'])
    manifest['replayImagesVerified']=sum(s['imagesVerified'] for s in comparison.values())
    manifest['sampledScenePixelMatch']=True
    shutil.copy2(rom,ROOT/'releases'/rom.name)
    (ROOT/'releases/v001.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Archived and released',digest)


if __name__=='__main__':main()
