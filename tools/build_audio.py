"""SFC向け楽器・6声編曲・SEを固定版TADで生成する（通常ROMビルドには不要）。"""
from pathlib import Path
import hashlib
import json
import math
import random
import re
import struct
import subprocess
import urllib.request
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[1]
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
                                   *[round(x / peak * 23000) for x in values]))


def samples():
    (AUDIO / 'samples').mkdir(parents=True, exist_ok=True)
    entries = []
    # 完全な周期波形を短くループし、SPC側のADSRで音の長さを作る。
    for name, harmonics, envelope in [
        ('lead', [1, .38, .22, .11, .07, .035], 'adsr 15 3 5 12'),
        ('pad', [1, .18, .08], 'adsr 11 2 5 12'),
        ('bass', [1, .42, .12, .06], 'adsr 15 4 3 18'),
        ('bell', [1, .05, .55, .02, .25, 0, .12], 'adsr 15 6 1 22'),
    ]:
        period = 128 if name == 'bass' else 32
        write_wav(name, (sum(a * math.sin(2 * math.pi * (h + 1) * i / period)
                             for h, a in enumerate(harmonics)) for i in range(period)))
        entries.append({'name': name, 'source': {'type': 'wav',
            'source': f'samples/{name}.wav', 'evaluator': 'default',
            'loop_point': 0, 'loop_filter': 'reset_filter'},
            'ignore_gaussian_overflow': False, 'pitches': {'type': 'octave',
            'frequency': 32000 / period, 'first_octave': 1,
            'last_octave': 5 if name == 'bass' else 7},
            'envelope': envelope})
    rng = random.Random(1985)
    for name, duration in [('kick', .16), ('snare', .13), ('hat', .045), ('crash', .3)]:
        rate = 16000
        values = []
        phase = 0
        previous = 0
        for i in range(int(rate * duration)):
            t = i / rate
            n = rng.uniform(-1, 1)
            high = n - previous
            previous = n
            if name == 'kick':
                phase += 2 * math.pi * (48 + 110 * math.exp(-t * 45)) / rate
                v = math.sin(phase) * math.exp(-t * 26) + high * math.exp(-t * 200) * .12
            elif name == 'snare':
                v = (high * .55 + math.sin(2 * math.pi * 185 * t) * .3) * math.exp(-t * 32)
            elif name == 'hat':
                v = high * math.exp(-t * 90)
            else:
                v = (high + .2 * math.sin(2 * math.pi * 1960 * t)) * math.exp(-t * 13)
            values.append(v * min(1, i / 8))
        write_wav(name, values, rate)
        entries.append({'name': name, 'source': {'type': 'wav',
            'source': f'samples/{name}.wav', 'evaluator': 'default'},
            'ignore_gaussian_overflow': False, 'pitches': {'type': 'samples',
            'sample_rates': [rate]}, 'envelope': 'gain F127'})
    return entries


def midi_tracks(path):
    import mido
    # 配布MIDIの一部velocityが128以上。clipはvelocityだけを127へ丸める。
    midi = mido.MidiFile(path, clip=True)
    tracks = []
    for track in midi.tracks:
        tick = 0
        active = {}
        notes = []
        for msg in track:
            tick += msg.time
            now = round(tick * 48 / midi.ticks_per_beat)
            if msg.type == 'note_on' and msg.velocity:
                active[msg.note] = now
            elif msg.type == 'note_off' or (msg.type == 'note_on' and not msg.velocity):
                if msg.note in active:
                    begin = active.pop(msg.note)
                    notes.append((begin, max(begin + 1, now), msg.note))
        tracks.append(notes)
    return tracks


def melodic_lanes(tracks, end):
    # 音符開始/終了の境界ごとに上声・中声・下声を選ぶ。SE用G/Hは使用しない。
    boundaries = sorted({0, end} | {v for tr in tracks[:6] for n in tr for v in n[:2] if v <= end})
    lanes = [[] for _ in range(4)]
    for begin, finish in zip(boundaries, boundaries[1:]):
        active = [sorted({n for a, b, n in tr if a <= begin < b}) for tr in tracks[:6]]
        chord = active[0]
        voices = [chord[-1] if chord else None,
                  chord[-2] if len(chord) >= 2 else (active[2][-1] if active[2] else None),
                  chord[0] if len(chord) >= 3 else
                  (active[5][-1] if active[5] else (active[3][-1] if active[3] else None)),
                  active[1][0] if active[1] else None]
        for lane, note in zip(lanes, voices):
            if lane and lane[-1][2] == note and lane[-1][1] == begin:
                lane[-1] = (lane[-1][0], finish, note)
            else:
                lane.append((begin, finish, note))
    return lanes


def duration_tokens(token, duration):
    # 一命令の上限を守り、持続音は&で結ぶ。
    out = []
    while duration:
        n = min(192, duration)
        duration -= n
        out.append(f'{token}%{n}' + (' &' if duration and token != 'r' else ''))
    return ' '.join(out)


def song(tracks):
    end = 640 * 48
    lines = ['; 音符参照: JK150 / SixtyTunes (VGMusic)。6声へ削減したSFC編曲。',
             '#Title Space Harrier - native SFC arrangement', '#Composer Hiroshi Kawaguchi',
             '#ZenLen 192', '#Tempo 154', '#MainVolume 88', '#EchoLength 0',
             '@lead lead', '@pad pad', '@bass bass',
             '@kick kick', '@snare snare', '@hat hat', '@crash crash']
    for channel, lane, instrument, volume, pan in zip('ABCD', melodic_lanes(tracks, end),
            ['lead', 'pad', 'pad', 'bass'], [160, 90, 78, 160], [64, 38, 90, 64]):
        lines.append(f'{channel} @{instrument} V{volume} p{pan} L')
        tokens = []
        for begin, finish, note in lane:
            token = 'r' if note is None else f'o{note // 12 - 1}' + ['c','c+','d','d+','e','f','f+','g','g+','a','a+','b'][note % 12]
            tokens.append(duration_tokens(token, finish - begin))
        for i in range(0, len(tokens), 16):
            lines.append(channel + ' ' + ' '.join(tokens[i:i + 16]))
    drums = {}
    for begin, finish, note in tracks[6]:
        if begin < end:
            drums.setdefault(begin, []).append(note)
    for channel in 'EF':
        events = []
        for begin, notes in sorted(drums.items()):
            if channel == 'E':
                instrument = ('snare' if any(n in notes for n in (38, 40)) else
                              'kick' if any(n in notes for n in (35, 36)) else None)
            else:
                instrument = ('crash' if any(n in notes for n in (49, 51, 57)) else
                              'hat' if any(n in notes for n in (42, 44, 46)) else None)
            if instrument:
                events.append((begin, instrument))
        patterns = {}
        calls = []
        for bar in range(0, end, 192):
            selected = [(a - bar, ins) for a, ins in events if bar <= a < bar + 192]
            tokens = []
            cursor = 0
            for i, (begin, instrument) in enumerate(selected):
                if begin > cursor:
                    tokens.append(duration_tokens('r', begin - cursor))
                next_time = selected[i + 1][0] if i + 1 < len(selected) else 192
                duration = min(next_time - begin, {'kick': 10, 'snare': 12, 'hat': 4, 'crash': 24}[instrument])
                tokens.append(f'@{instrument} s0,%{duration}')
                cursor = begin + duration
            if cursor < 192:
                tokens.append(duration_tokens('r', 192 - cursor))
            pattern = ' '.join(tokens)
            if pattern not in patterns:
                name = f'drum{channel}{len(patterns)}'
                patterns[pattern] = name
                lines.append(f'!{name} {pattern}')
            calls.append('!' + patterns[pattern])
        lines.append(f'{channel} V{130 if channel == "E" else 60} p{64 if channel == "E" else 80} L')
        for i in range(0, len(calls), 16):
            lines.append(channel + ' ' + ' '.join(calls[i:i + 16]))
    (AUDIO / 'theme.mml').write_text('\n'.join(lines) + '\n', encoding='utf-8')


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
    project = {'_about': {'file_type': 'Terrific Audio Driver project file', 'version': VERSION},
        'brr_samples': samples(), 'default_sfx_flags': {'one_channel': True, 'interruptible': True},
        'high_priority_sound_effects': ['death', 'boss_explosion'],
        'sound_effects': ['stumble', 'explosion', 'reflect'],
        'low_priority_sound_effects': ['shot'], 'sound_effect_file': 'effects.txt',
        'songs': [{'name': 'theme', 'source': 'theme.mml'}]}
    song(midi_tracks(midi))
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
.segment "AUDIO0"
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
        'arrangementVoices': 6, 'sfxVoices': 2, 'tempoQuarterNotes': 154,
        'durationQuarterNotes': 640,
        'files': {str(p.relative_to(AUDIO)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(AUDIO.rglob('*')) if p.is_file() and p.name != 'manifest.json'}}
    (AUDIO / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Native audio bytes:', (AUDIO / 'data.bin').stat().st_size)


if __name__ == '__main__':
    main()
