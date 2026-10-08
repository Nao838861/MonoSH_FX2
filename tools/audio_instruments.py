"""SFC用の楽器サンプルをオフラインで合成する（TADがBRRへ変換する）。

原作の業務用基板は FM音源（YM2203）と PCM打楽器。旋律・ベース・和音は2〜3オペレータのFMで、
変調の深さを時間で変えて「立ち上がりは明るく、すぐ落ち着く」音色の変化を作る。
立ち上がり部分は時間で変わる波形を書き、その後は一定の変調で周期が揃った波形を数周期ループする
（周期は16サンプルの倍数。ループ点も16サンプル境界）。音量の減衰・ビブラートはSPC側（ADSR・MP）で付ける。
打楽器は音程が下がる正弦波・帯域を絞ったノイズの組合せで、Sega PCM のドラムに近い太さを狙う。
"""
import math
import random
import struct
import wave
from pathlib import Path

import numpy as np

RATE = 32000


# SPC700の再生時の補間（Gaussian）で削れる高域を、波形の段階で持ち上げる（[-a, 1+2a, -a]）
EMPHASIS = 0.30


def emphasize(values, loop):
    """ループのある音はループ部分を循環として扱い、継ぎ目を崩さない。loop=None は単発の音。"""
    a = EMPHASIS
    x = np.asarray(values, dtype=np.float64)
    if loop is None:
        p = np.concatenate([[x[0]], x, [x[-1]]])
        return (1 + 2 * a) * x - a * (p[:-2] + p[2:])
    head, body = x[:loop], x[loop:]
    pb = np.concatenate([[body[-1]], body, [body[0]]])
    body = (1 + 2 * a) * body - a * (pb[:-2] + pb[2:])
    if len(head):
        ph = np.concatenate([[head[0]], head, [body[0]]])
        head = (1 + 2 * a) * head - a * (ph[:-2] + ph[2:])
    return np.concatenate([head, body])


def write_wav(path, values, rate=RATE, level=0.70):
    values = np.asarray(values, dtype=np.float64)
    values = np.concatenate([values, np.zeros(-len(values) % 16)])
    peak = np.max(np.abs(values)) or 1.0
    data = np.round(values / peak * 32767 * level).astype('<i2')
    with wave.open(str(path), 'wb') as out:
        out.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(data.tobytes())


def env_to(t, start, end, tau):
    """start から end へ時定数 tau で近づく。"""
    return end + (start - end) * np.exp(-t / tau)


def fm_voice(period, attack_periods, loop_periods, index1, index2=None, ratio2=2, feedback=0.0,
             rise=0.004, ratio1=1):
    """2〜3オペレータFM。index* は時間t（秒）→変調指数の関数。立ち上がり後は値を固定して周期を揃える。"""
    f0 = RATE / period
    n_attack = period * attack_periods
    n = n_attack + period * loop_periods
    t = np.arange(n) / RATE
    t_fixed = np.minimum(t, n_attack / RATE)          # ループ部分は変調を固定
    i1 = index1(t_fixed)
    i2 = index2(t_fixed) if index2 else 0.0
    mod = i1 * np.sin(2 * np.pi * ratio1 * f0 * t)
    if feedback:
        # 自己帰還の近似: 変調器自身へ位相を足す（周期は保たれる）
        mod = i1 * np.sin(2 * np.pi * ratio1 * f0 * t + feedback * np.sin(2 * np.pi * ratio1 * f0 * t))
    if index2:
        mod = mod + i2 * np.sin(2 * np.pi * ratio2 * f0 * t)
    y = np.sin(2 * np.pi * f0 * t + mod)
    amp = np.minimum(1.0, t / rise) if rise else 1.0
    return y * amp, n_attack


# 原作サントラ（効果音なし）の主旋律 E5 の倍音（dB、基音=0）。0.1〜0.3秒の平均。
# 2倍音-13dB、3倍音-17dB、4〜12倍音が-21dB前後で平ら、その上はなだらかに下がる
LEAD_DB = [0.0, -12.6, -16.9, -21.5, -21.7, -21.1, -20.0, -20.6, -21.3, -20.9, -21.1, -22.8, -24.2, -25.4,
           -26.2, -26.9, -29.4, -31.5, -32.4, -34.7, -35.8, -37.1, -37.7, -40.4]


def additive(period, dbs, max_harmonic, copies=2):
    """倍音の強さ（dB）から1周期の波形を作り、数周期並べてループさせる。"""
    t = np.arange(period) / period
    y = sum(10 ** (db / 20) * np.sin(2 * np.pi * (k + 1) * t) for k, db in enumerate(dbs[:max_harmonic]))
    return np.tile(y, copies), 0


# 原作の主旋律の厚み: 高い倍音ほど深く揺れる（基音±1dB、5倍音±3dB、10倍音±5dB）、
# 周波数のぶれも倍音の番号に比例、基音のうなり約2.9Hz。約9セントずれた2つ目の音が、
# 高い倍音ほど強く重なっていると同じ特徴。2つ目の音の強さの比 r（倍音ごと）は、
# 揺れの幅（山と谷の差 = 20log((1+r)/(1-r))）から逆算した。
# 主旋律を伸ばしている間の高域（4〜8kHz）は、倍音だけでは原作より約3dB少ない。倍音の間のノイズ成分で補う
LEAD_GRAIN_DB = -12
LEAD_BEAT_RATIO = [0.11, 0.17, 0.27, 0.35, 0.37, 0.30, 0.40, 0.46, 0.50, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52]


def loop_noise(n, low, high, rng):
    """ループ長 n で継ぎ目なく繰り返すノイズ。low〜high（ループ再生時の周波数比、0.5=ナイキスト）の帯域だけ。"""
    spec = np.zeros(n // 2 + 1, dtype=complex)
    f = np.arange(n // 2 + 1) / n
    band = (f >= low) & (f <= high)
    spec[band] = np.exp(1j * rng.uniform(0, 2 * np.pi, band.sum()))
    x = np.fft.irfft(spec, n)
    return x / np.sqrt(np.mean(x * x))


def detuned_pair(period, dbs, ratios, max_harmonic, periods=192, grain_db=None, grain_band=(0.05, 0.33)):
    """period の音（periods周期）と、1周期だけ多い音（約9セント上）を重ねる。両方の周期がループ長に収まる。
    grain_db: 倍音の合計に対するノイズ成分の強さ（dB）。原作のFM音源の細かいざらつき"""
    n = period * periods
    t = np.arange(n)
    y = np.zeros(n)
    rng = np.random.default_rng(1985)
    for k in range(max_harmonic):
        a = 10 ** (dbs[k] / 20)
        r = ratios[min(k, len(ratios) - 1)]
        a1 = a / np.sqrt(1 + r * r)
        y += a1 * np.sin(2 * np.pi * (k + 1) * t / period)
        y += r * a1 * np.sin(2 * np.pi * (k + 1) * (periods + 1) * t / n + rng.uniform(0, 2 * np.pi))
    if grain_db is not None:
        y = y + loop_noise(n, *grain_band, rng) * np.sqrt(np.mean(y * y)) * 10 ** (grain_db / 20)
    return y, 0


def lead():
    # G5以下（ループ周波数の約1.57倍まで）。原作の主旋律は約20倍音（13kHz）まで倍音を持つ
    return detuned_pair(64, LEAD_DB, LEAD_BEAT_RATIO, 20, grain_db=LEAD_GRAIN_DB)


def lead_mid():
    # G#5〜C6（約2.1倍まで）。折り返さない15倍音まで。使う音が少ないので短いループ
    return additive(64, LEAD_DB, 15)


def lead_hi():
    # C6より上（G#6で約3.3倍）。折り返さない9倍音まで
    return additive(64, LEAD_DB, 9)


# 主旋律の1オクターブ下を重ねるブラス。倍音は控えめ、主旋律と同じく約9セント上の2つ目の音を重ねて厚くする
BRASS_DB = [0, -10, -16, -22, -25, -28, -31, -34, -37, -40]
BRASS_BEAT_RATIO = [0.15, 0.25, 0.35, 0.45, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]


def brass():
    return detuned_pair(64, BRASS_DB, BRASS_BEAT_RATIO, 10)


def bass():
    # FMベース: 弾いた瞬間に倍音が強く、すぐ丸くなる
    return fm_voice(256, 12, 1, lambda t: env_to(t, 4.5, 1.3, 0.025),
                    lambda t: env_to(t, 1.0, 0.15, 0.02), ratio2=2, rise=0.002)


def pad():
    return fm_voice(64, 40, 2, lambda t: env_to(t, 1.0, 0.7, 0.2), rise=0.03)


def harmonics_wave(period, amps):
    t = np.arange(period) / period
    return sum(a * np.sin(2 * np.pi * (k + 1) * t) for k, a in enumerate(amps))


# 原作サントラの刻みの和音（C4・D4）の倍音（dB）。偶数倍音が中心の柔らかい音で、矩形波ではない
# （2倍音-6.5dB、3倍音-20dB、4倍音-12.5dB、5倍音-29dB、6倍音-15dB）
STAB_DB = [0.0, -6.5, -19.5, -12.5, -29.0, -15.5, -24.0, -22.0]


def stab():
    return additive(64, STAB_DB, len(STAB_DB))


# ---- 打楽器 ------------------------------------------------------------------

def _noise(n, seed, colour=0.0):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1, 1, n)
    if colour:
        # 簡単な1次フィルタで低域寄り（colour>0）/高域寄り（colour<0）にする
        y = np.zeros(n); prev = 0.0
        for i in range(n):
            prev = prev * colour + x[i] * (1 - abs(colour))
            y[i] = prev
        x = y if colour > 0 else x - y
    return x


def _onepole(x, a):
    y = np.zeros_like(x); prev = 0.0
    for i, v in enumerate(x):
        prev += a * (v - prev); y[i] = prev
    return y


def kick(rate=16000, length=0.32, top=150, bottom=46, tau=0.03, decay=11):
    t = np.arange(int(rate * length)) / rate
    f = bottom + (top - bottom) * np.exp(-t / tau)
    phase = 2 * np.pi * np.cumsum(f) / rate
    body = np.sin(phase) * np.exp(-t * decay)
    click = _onepole(_noise(len(t), 35), 0.5) * np.exp(-t * 300) * 0.5
    y = np.tanh((body + click) * 1.6)
    return y * np.minimum(1, t * rate / 6)


def snare(rate=32000, length=0.26):
    t = np.arange(int(rate * length)) / rate
    tone = (np.sin(2 * np.pi * 190 * t) + 0.6 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t * 28)
    n = _noise(len(t), 38)
    n = n - _onepole(n, 0.12)                  # 低域を抜いて「バシッ」とした成分
    noise = n * (0.85 * np.exp(-t * 16) + 0.4 * np.exp(-t * 60))
    y = np.tanh((tone * 0.9 + noise * 1.1) * 1.4)
    return y * np.minimum(1, t * rate / 8)


def tom(rate=16000, length=0.42):
    # 原作の印象的なタム回し: 音程が少し下がりながら太く鳴る
    t = np.arange(int(rate * length)) / rate
    f = 120 + 70 * np.exp(-t / 0.035)
    phase = 2 * np.pi * np.cumsum(f) / rate
    body = (np.sin(phase) + 0.25 * np.sin(2 * phase)) * np.exp(-t * 7.5)
    hit = _onepole(_noise(len(t), 41), 0.35) * np.exp(-t * 90) * 0.4
    y = np.tanh((body + hit) * 1.3)
    return y * np.minimum(1, t * rate / 6)


def hat(rate=32000, length=0.05, decay=95, seed=42):
    t = np.arange(int(rate * length)) / rate
    n = _noise(len(t), seed)
    n = n - _onepole(n, 0.25)                  # 高域だけ（原作サントラの4〜16kHzに合わせて明るめ）
    return n * np.exp(-t * decay) * np.minimum(1, t * rate / 4)


def crash(rate=32000, length=0.30):
    # 原作の決めの1打は、15kHzまで届く明るい成分が約0.25秒で消える。長い尾の鈍いノイズにしない
    t = np.arange(int(rate * length)) / rate
    n = _noise(len(t), 49)
    n = n - _onepole(n, 0.55)
    ring = sum(a * np.sin(2 * np.pi * f * t + ph) for a, f, ph in
               ((0.22, 3290, 0.3), (0.18, 4870, 1.1), (0.16, 6730, 2.0), (0.13, 8410, 0.7), (0.10, 10230, 2.6)))
    env = 0.6 * np.exp(-t * 11) + 0.4 * np.exp(-t * 30)
    return (n + ring) * env * np.minimum(1, t * rate / 4)


# 名前 → (合成関数, サンプル周期 or 再生レート, 種類)
TONAL = {
    'lead': (lead, 64), 'lead_mid': (lead_mid, 64), 'lead_hi': (lead_hi, 64), 'brass': (brass, 64), 'bass': (bass, 256), 'pad': (pad, 64),
    'stab': (stab, 64),
}
DRUMS = {
    'kick': (lambda: kick(), 16000), 'kick2': (lambda: kick(top=175, bottom=55, tau=0.022, decay=15), 16000),
    'snare': (snare, 32000), 'tom': (tom, 16000), 'hat': (hat, 32000),
    'ohat': (lambda: hat(length=0.18, decay=18, seed=46), 32000), 'crash': (crash, 32000),
}

# 決めの1打の明るさは原作サントラに合わせて、クラッシュだけ約5dB下げる
DRUM_LEVEL = {'crash': 0.45}


def write_all(folder):
    """サンプルを書き、名前→(ループ点, 周期 or レート) を返す。"""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    info = {}
    for name, (make, period) in TONAL.items():
        y, loop = make()
        write_wav(folder / f'{name}.wav', emphasize(y, loop))
        info[name] = dict(loop=loop, period=period)
    for name, (make, rate) in DRUMS.items():
        write_wav(folder / f'{name}.wav', emphasize(make(), None), rate=rate, level=DRUM_LEVEL.get(name, 0.8))
        info[name] = dict(rate=rate)
    return info
