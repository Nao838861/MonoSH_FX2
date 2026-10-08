# 標準SFC音源データ

SPC700・S-DSPで鳴るメインテーマ一曲と六種類のSE。音符列と短いBRR楽器を起動時にARAMへ載せ、ゲーム中はAPUIOの命令だけを送る。MSU1・録音ストリーム・追加DMAは使わない。

音楽：川口博史（Hiroshi Kawaguchi）、原作『Space Harrier』SEGA。音符の照合には [JK150 / SixtyTunesによる公開採譜](https://www.vgmusic.com/file/7bf98bd350648dc6d0548ed8b0e2e6d7.html)を参照した。元MIDIをそのまま再生せず、三つの和音上声・ベース・打楽器二声へ削減し、単旋律区間では空いた声へ副旋律を入れる。原作録画の音声も制作時に展開し、音高・フレーズの進行をスペクトルで照合した。録画の完全自動採譜や、原作の音色の完全抽出を達成したという扱いではない。

楽器は `tools/build_audio.py` で生成する周期波形四種と、減衰ノイズ・低音から作る打楽器四種。TADがBRRへ変換する。BGMはA..Fの六声、SEはG/Hの二声を使用する。640拍・四分音符154BPM、約249秒で先頭へ戻る。ポーズで停止し、解除で続きを演奏する。

SEは死亡、ボス撃破、転倒、敵爆発、弾反射、発射の六種類。実発射の時だけイベントを立て、弾枠が満杯の空撃ちでは鳴らさない。同一論理フレームの衝突は死亡、ボス撃破、転倒、爆発、反射、発射の順で優先する。重要SEは連射に上書きされない。現状は録画を基準に音の役割を作り直したSFC用SEであり、原作SEの完全コピーではない。

音源は [Terrific Audio Driver v0.4.2](https://github.com/undisbeliever/terrific-audio-driver/tree/v0.4.2)（Marcus Rowe、zlib License）。`vendor/LICENSE` とソース内の著作権表示を保持する。APIソースの変更は `.bss` の配置先を専用 `AUDIOBSS` へ変えた点だけで、冒頭へ改変表示を加えた。固定commit、配布zip・採譜入力・生成物のSHA256は `manifest.json`。

通常のROMビルドは生成済み `data.bin` と `data.s` を使い、音楽制作ツールを要求しない。音の再生成はWindowsで次を実行する。

```powershell
python -m pip install mido==1.3.3
python -X utf8 tools/build_audio.py
python -X utf8 tools/build_game.py
python -X utf8 tools/test_audio.py --timeout 240
```

再生成時だけ固定hashを検査してTADと採譜入力を `.cache/tad` に取得する。MIDIの範囲外velocityは127へ丸め、音符開始・終了をSFC向け48tick/拍へ量子化する。繰り返すドラムの小節は共通サブルーチンへまとめる。`tad-compiler check` で全曲・SEのARAM収容とGaussian overflowを検査する。

`theme.spc` は制作側の全曲データ。[実ROMの検証と試聴](../RESULTS_20261008_NATIVE_AUDIO.md)には、ゲームから書き出したSPC状態と音量・性能の結果を保存する。

残る差：原作FM音色、細かい打楽器・副旋律、SEの音質、ボス専用曲、音声。現在はボス戦でもメインテーマを継続する。実機での出音は未確認。
