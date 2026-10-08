# 標準SFC音源データ

SPC700・S-DSPで鳴るメインテーマ一曲と六種類のSE。音符列とBRR楽器を起動時にARAMへ載せ、ゲーム中はAPUIOの命令だけを送る。MSU1・録音ストリーム・追加DMAは使わない。

音楽：川口博史（Hiroshi Kawaguchi）、原作『Space Harrier』SEGA。音符は [JK150 / SixtyTunesによる公開採譜](https://www.vgmusic.com/file/7bf98bd350648dc6d0548ed8b0e2e6d7.html) を使い、ゲーム録画とテンポ（154BPM）・音の並びが一致することを拍単位で照合した。音色・音量の測定には、効果音のない原作サントラ（YouTube「[BGM] [AC] Space Harrier」）を使った。録画・サントラの音はリポジトリにも配布物にも含めない。

## 曲（第2版）

採譜のパートの役割ごとに8声へ割り振った（[tools/audio_arrange.py](../../../tools/audio_arrange.py)）。

|声|パート|楽器|
|---|---|---|
|A|主旋律（ch0の最高音）|lead／lead_mid／lead_hi（音域で切替）|
|B|スネア・ハット・クラッシュ|snare／hat／ohat／crash|
|C・D|刻みの和音（ch2・ch3）|stab|
|E|ベース（ch1）|bass|
|F|キック2種・タム|kick／kick2／tom|
|G|主旋律の1オクターブ下（ch4）、休みの和音ではch0の2番目|brass|
|H|後半のパッド（ch5）、休みの和音ではch0の3番目|pad|

SEはTADの仕様でG・Hを一時的に借りる。連射音はH、二つ同時のときだけGも使う。HとGには一時的に消えても曲の骨格が残るパートを置き、ドラムと主旋律は消えない。

楽器は [tools/audio_instruments.py](../../../tools/audio_instruments.py) が合成し、TADがBRRへ変換する。

- 主旋律：サントラで測った倍音（2倍音−13dB、3倍音−17dB、4〜12倍音が−21dB前後で平ら、20倍音まで）を足し合わせた波形。約9セント上の2つ目の音を重ね、うなり一周の0.38秒をループして厚みを出す（倍音の揺れの測定から強さを逆算）。倍音の間に薄いノイズ（−12dB）を入れてFM音源のざらつきを模す。ビブラートはない（サントラで±8セント以内）。減衰はADSR `15 1 5 16`（サントラの伸ばした音との差0.7dB）。高音域は折り返しを避けて倍音を減らした短いループへ切り替える。
- 刻みの和音：偶数倍音が中心の柔らかい音（サントラで測定）。鳴っている間は音量一定。試聴で主旋律より6dB下げた。
- ブラス：倍音を控えめにした音に、主旋律と同じ2つ目の音を重ねる。
- ベース：FM合成。低い音が次の音まで鳴り続ける。
- ドラム：キック2種、スネア、タム（録画のタム回しの音程 約147／110／85／65Hz）、ハット2種、クラッシュ（32kHz・0.3秒の短く明るい音）。
- 全サンプルに、S-DSPの補間で削れる高域を先に持ち上げる補正を掛ける。旋律・和音の声に32msの薄いエコー。

640拍・四分音符154BPM、約249秒で先頭へ戻る。ポーズで停止し、解除で続きを演奏する。曲の声の音量は、SEとの釣り合いが前版と同じになるよう一律に約2.2dB下げた。S-DSPの主音量は上限の127、楽器・SEの波形は最大の約87%（ドラムは約99%）で作る。

## SE

SEは死亡、ボス撃破、転倒、敵爆発、弾反射、発射の六種類。前版と同じ定義・同じ短い周期波形（se_lead・se_bell・se_bass）で鳴らし、音は変えていない。実発射の時だけイベントを立て、弾枠が満杯の空撃ちでは鳴らさない。同一論理フレームの衝突は死亡、ボス撃破、転倒、爆発、反射、発射の順で優先する。重要SEは連射に上書きされない。原作SEの再現は今後の課題。

## ROMとARAM

音のデータ（ドライバ・楽器・SE・曲）は53,392bytes。$59バンクの未使用だった後半 `$59:1300..$59:FFFF`（60,672bytes）を `AUDIO59` として予約して置く（[rom.cfg](../rom.cfg)、[gsu.s](../gsu.s) の原画bank取込、[tools/build_game.py](../../../tools/build_game.py) の縮小画像の詰め込み対象から除外）。起動時に一度だけ転送するので、GSUのROMバスとは競合しない。ARAMはTADの収容検査（エコー32msを含む）を通過。

## 生成

音源は [Terrific Audio Driver v0.4.2](https://github.com/undisbeliever/terrific-audio-driver/tree/v0.4.2)（Marcus Rowe、zlib License）。`vendor/LICENSE` とソース内の著作権表示を保持する。APIソースの変更は `.bss` の配置先を専用 `AUDIOBSS` へ変えた点だけで、冒頭へ改変表示を加えた。固定commit、配布zip・採譜入力・生成物のSHA256は `manifest.json`。

通常のROMビルドは生成済み `data.bin` と `data.s` を使い、音楽制作ツールを要求しない。音の再生成はWindowsで次を実行する。

```powershell
python -m pip install mido==1.3.3 numpy
python -X utf8 tools/build_audio.py
python -X utf8 tools/build_game.py
python -X utf8 tools/test_audio.py --frames 16000 --timeout 600
python -X utf8 tools/preview_audio.py
```

再生成時だけ固定hashを検査してTADと採譜入力を `.cache/tad` に取得する。`tad-compiler check` で全曲・SEのARAM収容とGaussian overflowを検査する。
