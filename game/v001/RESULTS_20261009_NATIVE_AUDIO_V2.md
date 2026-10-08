# BGM第2版：原作サントラで音色を測ったメインテーマ

配布ROM：[MonoSHFX2_v001.sfc](../../releases/MonoSHFX2_v001.sfc)。SHA256 `bfb35914dedf793f3178015d650c9fc040eb1b3fe810a68a8a005ffa1d5e9025`、2MiB。直前版は [木・小型敵・ボスの配色整理版](RESULTS_20261008_PALETTE_REGIONS.md)（`29cf2c2d…`）。

[BGM試聴60秒](results/native_audio_v2_20261009/bgm_preview.mp3)、[SE試聴](results/native_audio_v2_20261009/se_preview.mp3)。どちらも実ROMの試験で保存したSPC状態をlibgmeで演奏したもの。

## 変えたこと

メインテーマの楽器と編曲を作り直し、配色整理版の画面・ゲーム進行・SEに載せた。前版は、録画の音を基準にした短い周期波形で、6声へ機械的に削減していた。

- **基準の取り直し**：ゲーム録画は連射音などが常に重なり、音色を正しく測れない（録画で測ったビブラートは連射音による誤り）。効果音のない原作サントラで、主旋律・刻みの和音・決めのシンバルを測り直した。採譜MIDIは、録画とテンポ（154BPM）・音の並びが一致することを拍単位で確認し、そのまま使う。
- **主旋律**：サントラの倍音（2倍音−13dB、3倍音−17dB、4〜12倍音が−21dB前後で平ら、20倍音まで）を足し合わせ、減衰をADSRで合わせた（伸ばした音の差0.7dB）。ビブラートなし。高い倍音ほど深く揺れる原作の特徴に合わせて、約9セント上の2つ目の音を重ねて厚みを出し、薄いノイズ成分でFM音源のざらつきを模した。
- **声部**：採譜のパートの役割どおり8声へ割り振った。主旋律の1オクターブ下のブラス、刻みの和音2声、タム回し（原作の音程）を加え、同じ音の連打を1音ずつ鳴らす。SEが借りるG・Hには一時的に消えても曲の骨格が残るパートを置いた。
- **刻みの和音**：前試作の矩形波は悪目立ちしたため、サントラで測った柔らかい音（偶数倍音中心）に替え、試聴で6dB下げた。
- **決めのシンバル**：短く明るい音（32kHz・0.3秒）。高域の強さをサントラに合わせた。
- **全体**：S-DSPの補間で削れる高域の補正、旋律・和音の声に32msの薄いエコー。曲の音量は、SEとの釣り合いが前版と同じになるよう調整した。

詳細な楽器・声部の表と再生成手順は [audio/README.md](audio/README.md)。試聴での判断（主旋律の音色、刻みの和音の音量、厚み、決めの音）は作者の聴き比べで決めた。

## 聴感で残る差

- 原作より全体の厚みは少なく、FM音源とPCMドラムの質感そのものには届かない。4kHzより上はサントラより3〜5dB少ない。
- ベースとドラムは原作では録音した音（PCM）。サントラでの測定による合わせ込みはまだしていない。
- SEは前版のまま（短い周期波形とノイズの代用音）。原作SEの再現は未着手。録画からサントラを差し引いてSEを取り出す方法は、録画と原作サントラで各パートの音量の配分が違うため、曲が十分に消えず使えなかった。

## メモリと配置

|用途|配置・容量|
|---|---|
|音のデータ（ドライバ・楽器・SE・曲）|`$59:1300..$59:E38F`、53,392bytes。$59の未使用だった後半を `AUDIO59`（60,672bytes）として予約|
|前版の音のデータ|`$00:8F1B..D660`（18,246bytes）から移動し、BOOTの空きが戻った|
|ARAM|TADの収容検査（エコー32msを含む）を通過|

`$59:1300..$59:FFFF` は原画42の行の後の余白で、前版では縮小画像の詰め込みに使われていなかった。[tools/build_game.py](../../tools/build_game.py) の詰め込み対象から外し、[gsu.s](gsu.s) は原画bankの先頭 `$1300` bytesだけを取り込む。縮小画像の詰め込み量は前版と同じ406,800bytes。配色整理版ROMとの差は、BOOTのbank（音の読込callback）と$59の後半だけ。音のデータは起動時に一度だけ転送するので、GSUのROMバスとは競合しない。

## 動作の確認

標準Mesen 2.1.1、GSU clock100%、実機は未確認。

|試験|結果|
|---|---|
|音 16,000フィールド|曲tick 32,065でループ点30,720を通過して演奏継続。ポーズ中59フィールドで停止。六SEの命令をすべて観測。GSU稼働中のAPI呼出し0。音の処理は平均0.148ms（前版0.122ms）、最大5.36ms（起動時の読込、前版5.33ms）|
|SEの声|連射音はH、二つ同時のときだけGも使用（SE命令時のDSP状態で確認）。ドラム（B）と主旋律（A）は消えない|
|カラー 360フィールド|全49,152画素とOBJが一致。200標本・153,600タイルでmap／VRAM／パレットの誤り0|
|表示 720フィールド|3場面の全画素・OBJ一致。3カメラのBG1〜4と空HDMAの最終RGB一致|
|ポーズ 650フィールド|3場面の全画素・OBJ一致|
|通常・継続ボスの計測中の場面|各60場面の全画素・OBJ一致|
|通常プレイ 18,000フィールド|17,997画像、全17,996区間が1フィールド、60.0988fps、同じblank内の重複提示0|
|継続ボス 18,000フィールド|17,998画像、全17,997区間が1フィールド、60.0988fps。生存ボス12,932画像を含む|

証拠：[音](results/native_audio_v2_20261009/audio/summary.json)、[通常](results/native_audio_v2_20261009/natural_profile/report.json)、[ボス](results/native_audio_v2_20261009/boss_profile/report.json)、[回帰](results/native_audio_v2_20261009/regressions.txt)、[音量](results/native_audio_v2_20261009/audio_levels.json)、[生成物hash](results/native_audio_v2_20261009/manifest.json)。

## 再実行

```powershell
python -m pip install mido==1.3.3 numpy
python -X utf8 tools/build_audio.py
python -X utf8 tools/build_game.py
python -X utf8 tools/test_audio.py --frames 16000 --timeout 600
python -X utf8 tools/preview_audio.py
python -X utf8 tools/test_game.py --scenario color --frames 360 --timeout 300
python -X utf8 tools/test_game.py --scenario display --frames 720 --timeout 300
python -X utf8 tools/test_game.py --scenario pause --frames 650 --timeout 300
python -X utf8 tools/profile_boss.py --minimal --frames 18000 --timeout 1500 --allow-unreleased --output boss_profile_audio
python -X utf8 tools/report_color_60hz.py build/game_v001/boss_profile_audio --require-60hz
python -X utf8 tools/profile_boss.py --minimal --frames 18000 --timeout 1500 --boss-fire none --allow-unreleased --output boss_profile_audioboss
python -X utf8 tools/report_color_60hz.py build/game_v001/boss_profile_audioboss --require-60hz --require-boss
```

`test_audio.py` と `test_game.py` は終了時のLuaで「閉じたファイルへの書込み」を報告することがあるが、判定と要約の書込みの後の終了処理で、結果には影響しない。
