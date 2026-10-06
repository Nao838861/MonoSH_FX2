"""反復最適化の固定標本・自然入力・回帰検証を保存し、検証したROMを公開する。"""
import gzip
import hashlib
import json
import shutil

from build_game import ROOT, GAME, BUILD
from analyze_render_profile import analyze


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compressed(source, target):
    target.write_bytes(gzip.compress(source.read_bytes(), mtime=0))


def main():
    target = GAME/'results/render_iterations_20261007'
    target.mkdir(exist_ok=True)
    rom = BUILD/'MonoSHFX2_v001.sfc'
    digest = sha(rom)
    iterations = {}
    for name in ('opt_base', 'opt_cpu', 'opt_spans', 'opt_scaled', 'opt_shared',
                 'opt_bucket', 'opt_obj', 'opt_clip', 'opt_uv', 'final'):
        source = BUILD/('cache_compare_'+name)
        dest = target/name
        dest.mkdir(exist_ok=True)
        result = json.loads((source/'comparison.json').read_text())
        assert sha(source/rom.name) == result['romSha256']
        if name == 'final':
            assert result['romSha256'] == digest
        iterations[name] = result
        for filename in ('comparison.json', 'summary.json', 'build_mode.json', 'game.lbl', 'emulator.log'):
            shutil.copy2(source/filename, dest/filename)
        for filename in ('replay.jsonl', 'trace.jsonl', 'test.lua', rom.name):
            compressed(source/filename, dest/(filename+'.gz'))
    (target/'iterations.json').write_text(json.dumps(iterations, indent=2)+'\n')
    baseline, final = iterations['opt_base'], iterations['final']
    for a,b in zip(baseline['scenes'], final['scenes']):
        assert a['scene'] == b['scene'] and a['framebufferHashes'] == b['framebufferHashes']
    (target/'final_pixel_comparison.json').write_text(json.dumps({
        'baselineRomSha256':baseline['romSha256'], 'finalRomSha256':digest,
        'baselineScenesCompared':len(baseline['scenes']), 'allBaselineFramebufferHashesMatch':True,
        'finalScenes':len(final['scenes']), 'finalImagesVerified':final['imagesVerified']}, indent=2)+'\n')
    shutil.copy2(BUILD/'cache_compare_final/fixtures.json.gz', target/'fixtures.json.gz')
    profiles = {}
    for name in ('boss_profile_scaled', 'boss_profile_optimized', 'boss_profile_dma', 'boss_profile_final', 'boss_profile_finalnofire'):
        source = BUILD/name
        dest = target/name
        dest.mkdir(exist_ok=True)
        profiles[name] = analyze(source)
        if name in ('boss_profile_final', 'boss_profile_finalnofire'):
            assert profiles[name]['romSha256'] == digest
        for filename in ('summary.json', 'emulator.log', 'worst_gsu.json', 'worst_gsu_frame.bin',
                         'worst_gsu_packet.bin', 'worst_gsu_oam.bin', 'worst_road.json',
                         'worst_road_frame.bin', 'worst_road_packet.bin'):
            if (source/filename).exists():
                shutil.copy2(source/filename, dest/filename)
        for filename in ('timings.jsonl', 'trace.jsonl', 'test.lua'):
            compressed(source/filename, dest/(filename+'.gz'))
        (dest/'analysis.json').write_text(json.dumps(profiles[name], ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tests = {}
    for name in ('objects', 'packed', 'controls', 'pause', 'display', 'held', 'boss', 'stumble', 'stress'):
        source = BUILD/name
        assert not (source/'error.txt').exists()
        result = json.loads((source/'summary.json').read_text())
        assert result['romSha256'] == digest, name
        tests[name] = result
        shutil.copy2(source/'summary.json', target/(name+'.json'))
        compressed(source/'trace.jsonl', target/(name+'.jsonl.gz'))
    for name in ('objects_ppu.json',):
        shutil.copy2(BUILD/'objects'/name, target/name)
    for name in ('scene_enemies.png', 'display00238.png', 'display00478.png', 'display00718.png'):
        shutil.copy2(BUILD/'display'/name, target/name)
    shutil.copy2(BUILD/'scaled_assets_verified.json', target/'scaled_assets_verified.json')
    assert json.loads((target/'scaled_assets_verified.json').read_text())['romSha256'] == digest
    for filename in ('game.lbl', 'game.map', 'build_mode.json'):
        (target/filename).write_text('\n'.join(line.rstrip() for line in (BUILD/filename).read_text().splitlines()).rstrip()+'\n')
    manifest = json.loads((ROOT/'releases/v001.json').read_text(encoding='utf-8'))
    if manifest['romSha256'] != digest:
        manifest['previousRomSha256'] = manifest['romSha256']
    manifest['romSha256'] = digest
    manifest['buildMode'] = json.loads((BUILD/'build_mode.json').read_text())
    manifest['scenarioFrames'] = {name:s['fields'] for name,s in tests.items()}
    manifest['scenarioFrames']['naturalProfile'] = profiles['boss_profile_final']['fields']
    manifest['scenarioFrames']['bossLongNoFire'] = profiles['boss_profile_finalnofire']['fields']
    manifest['optimizationMeasurement'] = 'game/v001/results/render_iterations_20261007'
    manifest['replayScenes'] = len(iterations['final']['scenes'])
    manifest['replayImagesVerified'] = iterations['final']['imagesVerified']
    manifest['verificationKind'] = '同じ122標本の全FB/OBJ、自然入力18,000field、押しっぱなし・表示・ボス・操作を更新ROMで再検証。'
    manifest['playerImageValidation'] = 'game/v001/results/render_iterations_20261007/objects_ppu.json'
    manifest.pop('playerImageScenarioFrames', None)
    manifest.pop('playerImageIntegratedFromRomSha256', None)
    for key in ('equivalenceMatchedUpdates', 'bossEquivalenceMatchedUpdates'):
        manifest.pop(key, None)
    shutil.copy2(rom, ROOT/'releases'/rom.name)
    (ROOT/'releases/v001.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Archived and released', digest)


if __name__ == '__main__':
    main()
