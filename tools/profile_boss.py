"""通常入力でボス戦を観測し、画像ごとのCPU/GSU・DMA・締切を記録する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from build_game import BUILD, GAME
from run_probe import MESEN_EXE, lua, prepare_runtime
from analyze_boss_profile import physical_frame


def presentation_intervals(summary, timings):
    # 完了callbackのfieldは、転送が225行をまたぐだけでも0/2と揺れる。
    # 実際の提示間隔はDMA開始の物理fieldで数える。元の値は履歴として残す。
    if 'legacyCompletionIntervals' not in summary:
        summary['legacyCompletionIntervals'] = {str(n):summary['interval'+str(n)] for n in (1,2)}
        summary['legacyCompletionIntervals']['3plus'] = summary['interval3plus']
    gaps = [physical_frame(b['dmaStart'])-physical_frame(a['dmaStart'])
            for a,b in zip(timings,timings[1:])]
    assert all(n >= 1 for n in gaps)
    summary.update(interval1=gaps.count(1), interval2=gaps.count(2),
                   interval3plus=sum(n >= 3 for n in gaps),
                   intervalSource='DMA start physical field; completion callback counts are legacy')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=18000)
    parser.add_argument('--timeout', type=int, default=360)
    parser.add_argument('--boss-fire', choices=('a', 'none'), default='a',
                        help='noneは通常入力だけでボス戦を長く観測する。')
    parser.add_argument('--output', default='boss_profile')
    parser.add_argument('--allow-unreleased', action='store_true', help='未公開の比較ビルドもハッシュ付きで計測する。')
    parser.add_argument('--minimal', action='store_true', help='Keep final CPU/GSU/DMA stamps; omit detailed phase callbacks to reduce host overhead.')
    args = parser.parse_args()
    rom = BUILD / 'MonoSHFX2_v001.sfc'
    data = rom.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert args.allow_unreleased or data == (GAME.parents[1] / 'releases/MonoSHFX2_v001.sfc').read_bytes()
    labels = {m[2]: int(m[1], 16) for m in re.finditer(
        r'al ([0-9A-Fa-f]+) \.([^\s]+)', (BUILD / 'game.lbl').read_text())}
    start, end = labels['render_started'], labels['render_finished']
    marker = bytes([0x20, labels['_fx_frame'] & 255, labels['_fx_frame'] >> 8, 0xe2, 0x20])
    region = data[0x10000 + start:0x10000 + end]
    assert region.count(marker) == 1
    labels['cpu_frame_return'] = start + region.index(marker) + 3
    # CPUのwait_bottom直前のSEPを機械語から特定。ROMは変更しない。
    marker = bytes.fromhex('e220af3f2100af372100af3d2100c9cb')
    region = data[0x10000:0x20000]
    assert region.count(marker) >= 1
    labels['admission_ready'] = region.rindex(marker)
    marker = bytes.fromhex('a9808f002100')
    region_start, region_end = labels['render_finished'], labels['dma_started']
    region = data[0x10000 + region_start:0x10000 + region_end]
    assert region.count(marker) >= 1
    # Color staging may enter forced blank first; the last marker is FB admission.
    labels['admitted'] = region_start + region.rindex(marker)
    assert re.fullmatch(r'boss_profile(?:_[a-z0-9]+)?', args.output), 'unsafe output name'
    output = BUILD / args.output
    output.mkdir(exist_ok=True)
    # 検証ツールが作ったbuild/boss_profileの直下ファイルだけを掃除する。
    assert output.resolve().parent == BUILD.resolve()
    for old in output.iterdir():
        if old.is_file():
            old.unlink()
    script = (GAME / 'test.lua').read_text(encoding='utf-8')
    if args.boss_fire == 'none':
        marker = 'emu.setInput({a=true,right=x<tx-3'
        assert script.count(marker) == 1
        script = script.replace(marker, 'emu.setInput({a=false,right=x<tx-3')
    insertion = "emu.addMemoryCallback(guard(function()\n  gsu_ms="
    assert script.count(insertion) == 1
    script = script.replace(insertion, (GAME / 'boss_profile.lua').read_text(encoding='utf-8').replace('PROFILE_SECTIONS', 'false' if args.minimal else 'true') + '\n' + insertion)
    config = json.loads((BUILD / 'build_mode.json').read_text())
    for key, value in {'LABELS': lua(labels), 'OUTDIR': lua(output.as_posix()),
                       'MAXFRAME': str(args.frames), 'SCENARIO': lua('profile'),
                       'HELD_DIRECTION': lua('none'), 'HELD_FIRE': lua('none'),
                       'GSU_UV': str(config['gsuUv']).lower(),
                       'GSU_CLIP': str(config['gsuClip']).lower(),
                       'CPU_CLIP_COMMANDS': str(config.get('cpuClipCommands',False)).lower(),
                       'DMA_ADMISSION_BYTES': str(config.get('dmaAdmissionBytes',9216)),
                       'DISPLAY_CODE': (GAME / 'display.lua').read_text(encoding='utf-8')}.items():
        script = script.replace(key, value)
    script = script.replace('report:close();emu.stop(0);return', 'boss_report:close();report:close();emu.stop(0);return')
    path = output / 'test.lua'
    path.write_text(script, encoding='utf-8')
    mesen = prepare_runtime(MESEN_EXE)
    settings = mesen.parent / 'settings.json'
    settings_data = json.loads(settings.read_text())
    settings_data['Debug']['ScriptWindow']['ScriptTimeout'] = 10
    settings_data['Snes'].update({'Port1': {'Type': 'SnesController'}, 'DisableFrameSkipping': True})
    settings.write_text(json.dumps(settings_data))
    result = subprocess.run([str(mesen), '--testRunner', f'--timeout={args.timeout}',
                             '--doNotSaveSettings', '--enableStdout', str(rom), str(path)],
                            cwd=mesen.parent, capture_output=True, timeout=args.timeout + 10,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (output / 'emulator.log').write_bytes(result.stdout + result.stderr)
    print('Mesen exit', result.returncode)
    if (output / 'error.txt').exists():
        print((output / 'error.txt').read_text())
    if result.returncode:
        raise SystemExit(result.returncode)
    assert hashlib.sha256(rom.read_bytes()).hexdigest() == digest
    summary = json.loads((output / 'summary.json').read_text())
    timings = [json.loads(line) for line in (output / 'timings.jsonl').read_text().splitlines()]
    assert len(timings) == summary['rendered']
    presentation_intervals(summary, timings)
    # test.luaの旧cpuMaxMsはCPU/GSU合流の最大。CPU終了の観測から別々に保存する。
    summary['joinedMaxMs'] = summary.pop('cpuMaxMs')
    summary['cpuMaxMs'] = max(((row['cpuEnd']['clock'] - row['start']['clock']) & 0xffffffff) / 21477.272
                              for row in timings)
    summary.update({'romSha256': digest, 'mesenSha256': hashlib.sha256(mesen.read_bytes()).hexdigest(),
                    'scenario': 'natural-profile', 'framesRequested': args.frames, 'bossFire': args.boss_fire,
                    'detailedPhaseCallbacks': not args.minimal,
                    'bossMeasurement': 'timings.jsonl', 'buildMode': config,
                    'generatedLuaSha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    for tool in ('verify_game_pixels.py', 'verify_game_objects.py'):
        subprocess.run([sys.executable, str(Path(__file__).with_name(tool)), args.output], check=True)
    print('Recorded', summary['rendered'], 'images; boss seen:', summary['bossSeen'])


if __name__ == '__main__':
    main()
