"""拡縮検証済みROMへ遠景修正だけを統合したことと、統合後の実測を保存する。"""
import argparse
import gzip
import hashlib
import json
import re
import shutil

from archive_smooth_depth import save_directory, write_json
from analyze_render_profile import analyze
from build_game import ROOT, GAME, BUILD

RESULT = GAME/'results/smooth_depth_20261008'


def labels(path):
    return {m[2]: int(m[1], 16) for m in re.finditer(
        r'al ([0-9A-Fa-f]+) \.([^\s]+)', path.read_text())}


def verify_binary():
    base = gzip.decompress((RESULT/'previous_release.sfc.gz').read_bytes())
    candidate = gzip.decompress((RESULT/'replay/MonoSHFX2_v001.sfc.gz').read_bytes())
    scenery_path = RESULT/'scenery_release.sfc.gz'
    if not scenery_path.exists():
        scenery_path.write_bytes(gzip.compress((ROOT/'.cache/scenery_release.sfc').read_bytes(), mtime=0))
    scenery = gzip.decompress(scenery_path.read_bytes())
    final = (BUILD/'MonoSHFX2_v001.sfc').read_bytes()
    assert len(base) == len(candidate) == len(scenery) == len(final) == 0x200000
    expected = bytearray(candidate)
    background = [i for i, (a, b) in enumerate(zip(base, scenery)) if a != b]
    copied = []
    for i in background:
        if 0x10000 <= i < 0x20000 or 0x7fdc <= i < 0x7fe0:
            continue
        assert candidate[i] == base[i], f'background patch overlaps scaling at {i:x}'
        expected[i] = scenery[i]
        copied.append(i)
    # CPU命令は背景の即値2箇所だけ。命令長、分岐先、ロジックは変わらない。
    changed = [i for i in range(0x10000, 0x20000) if candidate[i] != final[i]]
    assert [(candidate[i-1], candidate[i], final[i]) for i in changed] == [
        (0xa9, 14, 23), (0x69, 87, 74)]
    before = labels(RESULT/'replay/game.lbl')
    after = labels(BUILD/'game.lbl')
    assert all(after.get(name) == addr for name, addr in before.items())
    assert before['_fx_build_ground'] <= changed[0]-0x10000 < before['_fx_ground_native']
    assert before['_fx_ground_native'] <= changed[1]-0x10000 < before['_fx_ground_native']+32
    for i in changed:
        assert candidate[i+1] == final[i+1] == 0
        expected[i] = final[i]
    expected[0x7fdc:0x7fe0] = final[0x7fdc:0x7fe0]
    assert expected == final, 'integration contains changes outside the scenery patch'
    checksum = int.from_bytes(final[0x7fde:0x7fe0], 'little')
    assert checksum == sum(final)&65535
    assert int.from_bytes(final[0x7fdc:0x7fde], 'little') == checksum^65535
    assert candidate[0x8000:0x10000] == final[0x8000:0x10000]
    assert candidate[0x40000:] == final[0x40000:]
    return {'romSha256': hashlib.sha256(final).hexdigest(),
            'scalingReferenceRomSha256': hashlib.sha256(candidate).hexdigest(),
            'sceneryReferenceRomSha256': hashlib.sha256(scenery).hexdigest(),
            'baseRomSha256': hashlib.sha256(base).hexdigest(),
            'referenceLabelsVerified': len(before), 'gsuCodeIdentical': True,
            'spriteGraphicsAndUvIdentical': True, 'backgroundDataBytesChanged': len(copied),
            'cpuOperandChanges': [{'fileOffset': i, 'opcode': candidate[i-1],
                                  'before': candidate[i], 'after': final[i]} for i in changed],
            'scope': 'CPU命令は背景座標の即値2箇所のみ。残りは遠景修正版の画像・色データとchecksum。全旧label位置も一致。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    target = RESULT/'integrated'
    target.mkdir(exist_ok=True)
    proof = verify_binary()
    write_json(target/'integration.json', proof)
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    if args.verify_only:
        return
    digest = proof['romSha256']
    tests = {}
    for name in ('objects', 'packed', 'controls', 'pause', 'display', 'held', 'boss', 'stumble', 'stress'):
        source = BUILD/name
        summary = json.loads((source/'summary.json').read_text())
        assert summary['romSha256'] == digest, name
        tests[name] = summary
        save_directory(source, target/'tests'/name)
    profiles = {}
    for name, directory in (('natural', 'boss_profile_smoothintegrated'),
                            ('no_fire', 'boss_profile_smoothintegratednofire')):
        source = BUILD/directory
        result = analyze(source)
        assert result['romSha256'] == digest
        assert json.loads((source/'summary.json').read_text()).get('openEm1SizeChecks', 0) > 0
        profiles[name] = result
        save_directory(source, target/name)
        write_json(target/name/'analysis.json', result)
        for filename in ('game.lbl', 'build_mode.json'):
            shutil.copy2(BUILD/filename, target/name/filename)
        (target/name/'MonoSHFX2_v001.sfc.gz').write_bytes(
            gzip.compress((BUILD/'MonoSHFX2_v001.sfc').read_bytes(), mtime=0))
    for filename, source in (('tables.json', BUILD/'smooth_depth/tables.json'),
                              ('scaled_assets_verified.json', BUILD/'scaled_assets_verified.json')):
        assert json.loads(source.read_text())['romSha256'] == digest
        shutil.copy2(source, target/filename)
    write_json(target/'tests.json', tests)
    write_json(target/'profiles.json', profiles)
    manifest_path = ROOT/'releases/v001.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update(romSha256=digest, previousRomSha256=proof['sceneryReferenceRomSha256'],
        comprehensiveVerificationReferenceRomSha256=proof['scalingReferenceRomSha256'],
        rendererReplayReferenceRomSha256=proof['scalingReferenceRomSha256'],
        verificationKind='滑らかな奥行き寸法と遠景修正の統合。CPU差分は背景即値2箇所とデータのみ。統合版で表示・操作・通常プレイ・長期ボスを再検証。',
        verificationResults='game/v001/results/smooth_depth_20261008/integrated/profiles.json',
        smoothDepthIntegration='game/v001/results/smooth_depth_20261008/integrated/integration.json',
        playerImageValidation='game/v001/results/smooth_depth_20261008/integrated/tests/objects/objects_ppu.json',
        scenarioFrames={**{name: value['fields'] for name, value in tests.items()},
                        'naturalProfile': profiles['natural']['fields'],
                        'bossLongNoFire': profiles['no_fire']['fields']})
    write_json(manifest_path, manifest)
    shutil.copy2(BUILD/'MonoSHFX2_v001.sfc', ROOT/'releases/MonoSHFX2_v001.sfc')
    print('Released integrated smooth scaling', digest)


if __name__ == '__main__':
    main()
