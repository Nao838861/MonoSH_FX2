"""同じROMの音・画素・性能の根拠を保存し、通常配布ROMを更新する。"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import wave
import zipfile
import numpy as np
from build_game import ROOT, BUILD, GAME


def main():
    target = GAME / 'results/native_audio_20261008'
    target.mkdir(parents=True, exist_ok=True)
    rom = BUILD / 'MonoSHFX2_v001.sfc'
    sha = hashlib.sha256(rom.read_bytes()).hexdigest()
    for name in ['audio', 'audio_quick', 'play', 'boss', 'objects', 'pause', 'scenery', 'color']:
        source = BUILD / name
        summary = json.loads((source / 'summary.json').read_text())
        assert summary['romSha256'] == sha, (name, 'different ROM')
        assert not (source / 'error.txt').exists(), name
        out = target / name
        out.mkdir(exist_ok=True)
        shutil.copy2(source / 'summary.json', out / 'summary.json')
        for file in ['test.lua', 'trace.jsonl', 'emulator.log']:
            (out / (file + '.gz')).write_bytes(gzip.compress((source / file).read_bytes(), mtime=0))
        with zipfile.ZipFile(out / 'samples.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(source.iterdir()):
                if p.suffix in ['.bin', '.json', '.png', '.ram', '.dsp', '.state', '.spc'] and p.name != 'summary.json' and '_solo' not in p.stem:
                    z.write(p, p.name)
    perf = json.loads((BUILD / 'audio_perf.json').read_text())
    assert perf['native']['romSha256'] == sha
    shutil.copy2(BUILD / 'audio_perf.json', target / 'performance.json')
    for name in ['baseline', 'native']:
        source = BUILD / ('audio_perf_' + name)
        out = target / ('perf_' + name)
        out.mkdir(exist_ok=True)
        for p in source.iterdir():
            if p.is_file():
                shutil.copy2(p, out / p.name)
    shutil.copy2(ROOT / '.cache/tad/baseline.lbl', target / 'perf_baseline/game.lbl')
    (target / 'perf_baseline/baseline.sfc.gz').write_bytes(gzip.compress(
        (ROOT / '.cache/tad/baseline.sfc').read_bytes(), mtime=0))
    for name in ['game.map', 'game.lbl', 'build_mode.json']:
        shutil.copy2(BUILD / name, target / name)
    # 試聴は実ROMから出したSPC状態をlibgmeで演奏する。SFCの実行時には不要。
    shutil.copy2(BUILD / 'audio_quick/bgm.spc', target / 'bgm.spc')
    def render(source, wav, seconds):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(source), '-t', str(seconds),
            '-ar', '32000', str(wav)], check=True)
    def encode(source, output):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(source),
            '-c:a', 'libmp3lame', '-b:a', '128k', str(output)], check=True)
    preview = BUILD / 'audio_quick/bgm_preview.wav'
    render(target / 'bgm.spc', preview, 45)
    encode(preview, target / 'bgm_preview.mp3')
    clips = []
    levels = {}
    for name, index in [('shot', 5), ('reflect', 4), ('explosion', 3),
                        ('stumble', 2), ('death', 0), ('boss_explosion', 1)]:
        source = BUILD / 'audio_quick' / f'sfx{index}.spc'
        data = bytearray(source.read_bytes())
        data[0x105] = 0  # TAD io_musicChannelsMask: 試聴コピーのみBGM六声をミュート。
        for ch in range(6):
            data[0x10100 + ch * 16:0x10100 + ch * 16 + 2] = b'\0\0'
        spc = target / f'se_{name}.spc'
        spc.write_bytes(data)
        wav = BUILD / 'audio_quick' / f'se_{name}.wav'
        render(spc, wav, 1.5)
        with wave.open(str(wav), 'rb') as f:
            assert f.getparams()[:3] == (2, 2, 32000)
            raw = f.readframes(f.getnframes())
        values = np.frombuffer(raw, dtype='<i2').astype(float)
        levels[name] = {'peak': int(np.max(np.abs(values))),
            'rms': float(np.sqrt(np.mean(values ** 2))),
            'tailRms': float(np.sqrt(np.mean(values[-6400:] ** 2)))}
        assert levels[name]['peak'] > 1000, (name, 'silent sound effect')
        assert levels[name]['peak'] < 32760, (name, 'clipping')
        assert levels[name]['tailRms'] == 0, (name, 'did not stop')
        clips.append(raw + b'\0' * (32000 * 4 * 3 // 10))
    combined = BUILD / 'audio_quick/se_preview.wav'
    with wave.open(str(combined), 'wb') as f:
        f.setparams((2, 2, 32000, 0, 'NONE', 'not compressed'))
        f.writeframes(b''.join(clips))
    encode(combined, target / 'se_preview.mp3')
    with wave.open(str(preview), 'rb') as f:
        bgm = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').astype(float)
    levels['bgm'] = {'peak': int(np.max(np.abs(bgm))), 'rms': float(np.sqrt(np.mean(bgm ** 2)))}
    assert 1000 < levels['bgm']['peak'] < 32760
    (target / 'audio_levels.json').write_text(json.dumps(levels, indent=2) + '\n')
    previous = json.loads((ROOT / 'releases/v001.json').read_text(encoding='utf-8'))
    if not (target / 'previous_release.json').exists():
        (target / 'previous_release.json').write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    previous = json.loads((target / 'previous_release.json').read_text(encoding='utf-8'))
    shutil.copy2(rom, ROOT / 'releases/MonoSHFX2_v001.sfc')
    previous.update(romSha256=sha, romBytes=rom.stat().st_size,
        verificationKind='標準SPC700のBGM・SE。実ROMのAPUIO/DSP/SPC、曲一周、ポーズ、画素・OBJ・遠景・ボス・カラー回帰、同一論理区間の速度を検証。',
        verificationResults='game/v001/results/native_audio_20261008',
        previousRomSha256=perf['baseline']['romSha256'],
        nativeAudio={'driver': 'TAD v0.4.2', 'streaming': False,
            'musicVoices': 6, 'sfxVoices': 2, 'songs': 1, 'soundEffects': 6,
            'romAudioBytes': 18246, 'physicalHardwareTested': False},
        audioPerformance=perf,
        scenarioFrames={name:json.loads((target/name/'summary.json').read_text())['fields']
            for name in ['audio','audio_quick','play','boss','objects','pause','scenery','color']})
    # 色版以前のperformanceは履歴へ退避し、新版は同一入力A/B値を使う。
    previous['previousColorPerformance'] = previous.pop('performance', {})
    (ROOT / 'releases/v001.json').write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Released', sha)
    print(json.dumps(levels, indent=2))


if __name__ == '__main__':
    main()
