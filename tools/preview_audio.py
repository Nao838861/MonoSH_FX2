"""実ROMの試験で保存したSPC状態から、BGMとSEの試聴音を作る（ffmpeg/libgme。SFCの実行時には不要）。

BGM: audio/bgm.spc（ゲーム開始直後の状態）から60秒。
SE: audio/sfx<n>.spc（SE命令を受け取る直前の状態）。試聴用のコピーだけ曲の8声を消音して1.5秒ずつ並べる。
"""
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

from build_game import BUILD, GAME

SE = [('shot', 6), ('reflect', 5), ('explosion', 3), ('ground_explosion', 4), ('stumble', 2), ('death', 0), ('boss_explosion', 1)]


def render(spc, wav, seconds):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(spc), '-t', str(seconds), '-ar', '32000', str(wav)], check=True)


def encode(wav, mp3):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(wav), '-c:a', 'libmp3lame', '-b:a', '160k', str(mp3)], check=True)


def samples(wav):
    with wave.open(str(wav), 'rb') as f:
        assert f.getparams()[:3] == (2, 2, 32000)
        return f.readframes(f.getnframes())


def main(target):
    source = BUILD / 'audio'             # tools/test_audio.py の長時間試験の保存先
    target.mkdir(parents=True, exist_ok=True)
    levels = {}
    bgm = source / 'bgm_preview.wav'
    render(source / 'bgm.spc', bgm, 60)
    encode(bgm, target / 'bgm_preview.mp3')
    values = np.frombuffer(samples(bgm), dtype='<i2').astype(float)
    levels['bgm'] = {'peak': int(np.max(np.abs(values))), 'rms': float(np.sqrt(np.mean(values ** 2)))}
    assert 1000 < levels['bgm']['peak'] < 32760, levels['bgm']
    clips = []
    for name, index in SE:
        data = bytearray((source / f'sfx{index}.spc').read_bytes())
        data[0x105] = 0                 # TAD io_musicChannelsMask: 試聴コピーのみ曲の声を止める
        for ch in range(8):             # 鳴っている曲の声の音量も0に（SEは鳴らすときに自分の音量を書く）
            data[0x10100 + ch * 16:0x10100 + ch * 16 + 2] = b'\0\0'
        spc = target / f'se_{name}.spc'
        spc.write_bytes(data)
        wav = source / f'se_{name}.wav'
        render(spc, wav, 1.5)
        raw = samples(wav)
        v = np.frombuffer(raw, dtype='<i2').astype(float)
        levels[name] = {'peak': int(np.max(np.abs(v))), 'rms': float(np.sqrt(np.mean(v ** 2))),
                        'tailRms': float(np.sqrt(np.mean(v[-6400:] ** 2)))}
        assert levels[name]['peak'] > 1000, (name, 'silent sound effect')
        assert levels[name]['peak'] < 32760, (name, 'clipping')
        clips.append(raw + b'\0' * (32000 * 4 * 3 // 10))
    combined = source / 'se_preview.wav'
    with wave.open(str(combined), 'wb') as f:
        f.setparams((2, 2, 32000, 0, 'NONE', 'not compressed'))
        f.writeframes(b''.join(clips))
    encode(combined, target / 'se_preview.mp3')
    (target / 'audio_levels.json').write_text(json.dumps(levels, indent=2) + '\n')
    print(json.dumps(levels, indent=2))


if __name__ == '__main__':
    main(GAME / 'results/native_audio_v2_20261009')
