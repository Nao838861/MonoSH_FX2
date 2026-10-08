"""SFC向け楽器・8声編曲・SEを固定版TADで生成する（通常ROMビルドには不要）。

曲の楽器は tools/audio_instruments.py（原作サントラで測った倍音・減衰に合わせた合成音）、
編曲は tools/audio_arrange.py（採譜MIDIのパートごとに8声へ割り振る）。
効果音は前版と同じ短い周期波形（se_lead・se_bell・se_bass）で鳴らし、音を変えない。
音のデータは $59 バンクの予約領域（$59:1300〜$59:FFFF）に置く。起動時に一度だけ転送する。
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import re
import struct
import subprocess
import urllib.request
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
AUDIO = ROOT / 'game/v001/audio'
CACHE = ROOT / '.cache/tad'
VERSION = '0.4.2'
ZIP_HASH = '4532822bd06778b89658afe7a782b6359600ac51205686be6fbb0d485c8019dd'
MIDI_URL = 'https://www.vgmusic.com/new-files/spaceharrier_main_theme.mid'
MIDI_HASH = 'a63eb2425c523e3a29e8c94ba4acd42e4bde829961c2d7019e4540c27a38ba4f'


def obtain(url, path, digest):
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path


def write_wav(name, values, rate=32000):
    values = list(values)
    values += [0.0] * (-len(values) % 16)
    peak = max(abs(x) for x in values) or 1
    with wave.open(str(AUDIO / 'samples' / (name + '.wav')), 'wb') as out:
        out.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(struct.pack('<' + 'h' * len(values),
                                   *[round(x / peak * 28600) for x in values]))


def se_samples():
    """前版の効果音用の楽器（同じ波形・同じADSR）。曲には使わない。"""
    (AUDIO / 'samples').mkdir(parents=True, exist_ok=True)
    entries = []
    for name, harmonics, envelope in [
        ('lead', [1, .38, .22, .11, .07, .035], 'adsr 15 3 5 12'),
        ('bass', [1, .42, .12, .06], 'adsr 15 4 3 18'),
        ('bell', [1, .05, .55, .02, .25, 0, .12], 'adsr 15 6 1 22'),
    ]:
        period = 128 if name == 'bass' else 32
        write_wav('se_' + name, (sum(a * math.sin(2 * math.pi * (h + 1) * i / period)
                                     for h, a in enumerate(harmonics)) for i in range(period)))
        entries.append({'name': 'se_' + name, 'source': {'type': 'wav',
            'source': f'samples/se_{name}.wav', 'evaluator': 'default',
            'loop_point': 0, 'loop_filter': 'reset_filter'},
            'ignore_gaussian_overflow': False, 'pitches': {'type': 'octave',
            'frequency': 32000 / period, 'first_octave': 1,
            'last_octave': 5 if name == 'bass' else 7},
            'envelope': envelope})
    return entries


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / 'release.zip'
    obtain(f'https://github.com/undisbeliever/terrific-audio-driver/releases/download/v{VERSION}/terrific-audio-driver-{VERSION}-win64.zip', archive, ZIP_HASH)
    release = CACHE / 'release' / f'terrific-audio-driver-{VERSION}-win64'
    if not release.exists():
        with zipfile.ZipFile(archive) as z:
            z.extractall(CACHE / 'release')
    midi = CACHE / 'reference.mid'
    obtain(MIDI_URL, midi, MIDI_HASH)
    import audio_instruments, audio_arrange
    for old in (AUDIO / 'samples').glob('*.wav'):
        old.unlink()                                  # 前版の楽器を残さない
    music = audio_arrange.brr_samples(audio_instruments.write_all(AUDIO / 'samples'))
    project = {'_about': {'file_type': 'Terrific Audio Driver project file', 'version': VERSION},
        'brr_samples': music + se_samples(), 'default_sfx_flags': {'one_channel': True, 'interruptible': True},
        'high_priority_sound_effects': ['death', 'boss_explosion'],
        'sound_effects': ['stumble', 'explosion', 'ground_explosion', 'reflect'],
        'low_priority_sound_effects': ['shot'], 'sound_effect_file': 'effects.txt',
        'songs': [{'name': 'theme', 'source': 'theme.mml'}]}
    (AUDIO / 'theme.mml').write_text(audio_arrange.song(audio_arrange.midi_notes(midi)), encoding='utf-8')
    path = AUDIO / 'monosh.terrificaudio'
    path.write_text(json.dumps(project, indent=2) + '\n', encoding='utf-8')
    compiler = str(release / 'tad-compiler.exe')
    def run(*args):
        subprocess.run([compiler, *map(str, args)], check=True, cwd=AUDIO)
    run('check', path)
    run('ca65-export', '--lorom', '--segment', 'AUDIO0', '-a', AUDIO / 'data.s',
        '-b', AUDIO / 'data.bin', '-i', AUDIO / 'enums.inc', path)
    data = (AUDIO / 'data.s').read_text()
    raw = (AUDIO / 'data.bin').read_bytes()
    # 標準callbackはLoROM $8000開始を要求する。本ROMはresetを$8000に保つため、
    # 一bank内に収まる二項目の明示pointerを返すcallbackへ生成し直す。
    table = int(re.search(r'Tad_DataTable := __Tad_AudioData_0 \+ (\d+)', data)[1])
    callback_size = int(re.search(r'\.sizeof\(LoadAudioData\) = (\d+)', data)[1])
    offsets = [int.from_bytes(raw[table + i * 3:table + i * 3 + 3], 'little') - callback_size for i in range(2)]
    sizes = [offsets[1] - offsets[0], len(raw) - offsets[1]]
    loader_size = int(re.search(r'Tad_Loader_SIZE = (\d+)', data)[1])
    driver_size = int(re.search(r'Tad_AudioDriver_SIZE = (\d+)', data)[1])
    custom = f'''; Generated by tools/build_audio.py; fixed-bank callback for this Super FX ROM.
.setcpu "65816"
.smart
.export LoadAudioData: far
.export Tad_Loader_Bin := audio_data
.export Tad_Loader_SIZE = {loader_size}
.export Tad_AudioDriver_Bin := audio_data + {loader_size}
.export Tad_AudioDriver_SIZE = {driver_size}
.import TAD_IO_VERSION
.assert TAD_IO_VERSION = 20, lderror, "TAD IO version mismatch"
.segment "BOOT"
.a8
.i16
LoadAudioData:
  cmp #0
  beq common
  cmp #1
  beq song
  clc
  rtl
common:
  lda #.bankbyte(audio_data + {offsets[0]})
  ldx #.loword(audio_data + {offsets[0]})
  ldy #{sizes[0]}
  sec
  rtl
song:
  lda #.bankbyte(audio_data + {offsets[1]})
  ldx #.loword(audio_data + {offsets[1]})
  ldy #{sizes[1]}
  sec
  rtl
.segment "AUDIO59"
audio_data: .incbin "data.bin"
.assert .bankbyte(audio_data) = .bankbyte(audio_data + {len(raw)} - 1), lderror, "Audio data crosses bank"
'''
    (AUDIO / 'data.s').write_text(custom, encoding='utf-8')
    run('song2spc', '-s', '-o', AUDIO / 'theme.spc', path, 'theme')
    manifest = {'driver': 'Terrific Audio Driver', 'version': VERSION,
        'sourceCommit': '6f9d0d1e5758588bd672a3806bb9ee0c6471c716',
        'releaseSha256': ZIP_HASH, 'noteReferenceUrl': MIDI_URL,
        'noteReferenceSha256': MIDI_HASH, 'noteReferenceAuthor': 'JK150 / SixtyTunes',
        'recordingReference': 'スペースハリアー録画１.mp4',
        'recordingReferenceSha256': 'ad7892c75c4433e6563e83251c12529a56ef1305308ddeed342cdca8bdd234a4',
        'soundtrackReference': '[BGM] [AC] Space Harrier（YouTube、効果音なしのサントラ）。音色・音量の測定にのみ使用、配布物には含めない',
        'arrangementVoices': 8, 'sfxVoices': 2, 'sfxDucksMusicVoices': 'G,H', 'tempoQuarterNotes': 154,
        'durationQuarterNotes': 640,
        'files': {str(p.relative_to(AUDIO)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(AUDIO.rglob('*')) if p.is_file() and p.name != 'manifest.json'}}
    (AUDIO / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Native audio bytes:', (AUDIO / 'data.bin').stat().st_size)


if __name__ == '__main__':
    main()
