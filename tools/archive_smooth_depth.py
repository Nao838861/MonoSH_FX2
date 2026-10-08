"""滑らかな奥行き寸法の検証を保存し、同じROMだけを公開する。"""
import gzip
import hashlib
import json
import shutil
from PIL import Image
from build_game import ROOT, GAME, BUILD, CC65
from run_probe import MESEN_EXE
from analyze_render_profile import analyze


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def save_directory(source, dest):
    dest.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if not path.is_file():
            continue
        if path.name.startswith('meta') and path.suffix == '.json':
            continue  # 全描画の再生成は固定ROM/Lua/fixturesで行い、数千個の小ファイルを保存しない。
        if path.suffix in ('.json', '.png', '.gif', '.log', '.lbl') or path.name == 'fixtures.json.gz':
            shutil.copy2(path, dest/path.name)
        elif path.name in ('test.lua', 'trace.jsonl', 'timings.jsonl', 'replay.jsonl', 'MonoSHFX2_v001.sfc'):
            (dest/(path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        elif path.suffix == '.rgb':
            raw = path.read_bytes()
            Image.frombytes('RGB', (256, len(raw)//768), raw).save(dest/path.with_suffix('.png').name)


def main():
    target = GAME/'results/smooth_depth_20261008'
    target.mkdir(exist_ok=True)
    rom = BUILD/'MonoSHFX2_v001.sfc'
    digest = sha(rom)
    mode = json.loads((BUILD/'build_mode.json').read_text())
    assert mode['smoothDepthSizes'] and not mode['fullFramebufferTransfer']
    tables = json.loads((BUILD/'smooth_depth/tables.json').read_text())
    assert tables['romSha256'] == digest
    assets = json.loads((BUILD/'scaled_assets_verified.json').read_text())
    assert assets['romSha256'] == digest
    shutil.copy2(BUILD/'scaled_assets_verified.json', target/'scaled_assets_verified.json')
    fixed = json.loads((BUILD/'cache_compare_smoothdepth/comparison.json').read_text())
    assert fixed['romSha256'] == digest and len(fixed['scenes']) == 1221
    assert sha(BUILD/'cache_compare_smoothdepth'/rom.name) == digest
    tests = {}
    for name in ('objects', 'packed', 'controls', 'pause', 'display', 'held', 'boss', 'stumble', 'stress'):
        source = BUILD/name
        summary = json.loads((source/'summary.json').read_text())
        assert summary['romSha256'] == digest, name
        tests[name] = summary
        save_directory(source, target/'tests'/name)
    profiles = {}
    for name in ('boss_profile_smoothfinal', 'boss_profile_smoothnofire'):
        source = BUILD/name
        result = analyze(source)
        assert result['romSha256'] == digest
        profiles[name] = result
        save_directory(source, target/name)
        (target/name/rom.with_suffix('.sfc.gz').name).write_bytes(gzip.compress(rom.read_bytes(), mtime=0))
        shutil.copy2(BUILD/'game.lbl', target/name/'game.lbl')
        shutil.copy2(BUILD/'build_mode.json', target/name/'build_mode.json')
        write_json(target/name/'analysis.json', result)
    for name in ('equivalence', 'equivalence_boss'):
        summary = json.loads((target/name/'summary.json').read_text(encoding='utf-8'))
        assert summary['nativeRomSha256'] == digest, name
    save_directory(BUILD/'cache_compare_smoothdepth', target/'replay')
    save_directory(BUILD/'smooth_depth', target/'tables')
    shutil.copy2(BUILD/'smooth_depth/sizes.csv', target/'tables/sizes.csv')
    write_json(target/'tests.json', tests)
    write_json(target/'profiles.json', profiles)
    # 初回の表のみの試作は、開いたEM1の3段階切替をまだ残していた別ROM。
    trial = BUILD/'boss_profile_curve1'
    if trial.exists():
        save_directory(trial, target/'earlier_table_trial')
        write_json(target/'earlier_table_trial/analysis.json', analyze(trial))
    write_json(target/'environment.json', {
        'romSha256': digest, 'mesenSha256': sha(MESEN_EXE),
        'gsuClockPercent': 100, 'region': 'NTSC', 'extraScanlines': 0,
        'compilerSha256': {name: sha(CC65/(name+'.exe')) for name in ('cc65', 'ca65', 'ld65')},
        'buildMode': mode})
    manifest_path = ROOT/'releases/v001.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    previous = ROOT/'releases/MonoSHFX2_v001.sfc'
    if sha(previous) != digest:
        (target/'previous_release.sfc.gz').write_bytes(gzip.compress(previous.read_bytes(), mtime=0))
        write_json(target/'previous_release.json', manifest)
        manifest['previousRomSha256'] = sha(previous)
    manifest.update(romSha256=digest, buildMode=mode,
        verificationKind='奥行き寸法14表と開いたEM1の5poseを平滑化。全Zの実描画、C/native状態一致、操作・表示・通常プレイを再検証。',
        verificationResults=str((target/'profiles.json').relative_to(ROOT)).replace('\\', '/'),
        smoothDepthMeasurement=str(target.relative_to(ROOT)).replace('\\', '/'),
        scenarioFrames={**{name: value['fields'] for name, value in tests.items()},
                        'naturalProfile': profiles['boss_profile_smoothfinal']['fields'],
                        'bossLongNoFire': profiles['boss_profile_smoothnofire']['fields']},
        replayScenes=len(fixed['scenes']), replayImagesVerified=fixed['imagesVerified'],
        playerImageValidation='game/v001/results/smooth_depth_20261008/tests/objects/objects_ppu.json',
        sampledScenePixelMatch=True,
        geometryPolicy='単調Hermite曲線をビルド時に整数寸法へ変換。近遠端・接地・移動速度を保持。開EM1の描画と当たり判定は同じ111項目。')
    # DMA・素材の試験は実装と画像が同一な旧ROMの履歴であることを明示する。
    manifest['unchangedRendererValidationRomSha256'] = tables['comparisonRomSha256']
    manifest['comprehensiveVerificationReferenceRomSha256'] = digest
    write_json(manifest_path, manifest)
    shutil.copy2(rom, previous)
    print('Archived and released', digest)


if __name__ == '__main__':
    main()
