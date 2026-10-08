# MonoSH FX2：実行可能な移植版 v001

最新は [影と草のパレット共通化](RESULTS_20261009_SHADOW_GRASS.md)。影を草と同じpalette1・最暗index1へ変更。両描画順とタイル位置を変えた実PPU33場面で草の明暗と影の色を確認。

最新は [自弾の時間色と地面上2行の修正](RESULTS_20261009_GROUND_TIME.md)。自弾は全弾共通の論理時間で4色を巡る。地面の上2行だけをclipし、その下の投影を保つ。山・森林を全復元して2ドット下へ表示。前回の距離色・遠景上端削除は取り消した。

最新は [白黒の二値化と自機の透明穴修正](RESULTS_20261009_BINARY_PLAYER.md)。SELECT／Spaceで敵・障害物を純黒／純白に切替。録画の青紫の服を誤って抜いていた処理を直し、ズボン・背中の176画素を復元した。以下のBGM第2版を引き継ぐ。

最新は [BGM第2版](RESULTS_20261009_NATIVE_AUDIO_V2.md)：原作サントラで音色を測って作り直したメインテーマ（8声）を配色整理版に載せた。SEは前版のまま。

その前は [木・小型敵・ボスの配色整理](RESULTS_20261008_PALETTE_REGIONS.md)。木3色、敵の赤い目と灰色の金属、ボスの象牙色の目・角と茶色の腹部を実PPUで検証。以下は以前の実装・検証記録。


最新ROMは [輪郭修正＋カラー＋BGM・SE版](RESULTS_20261008_VISUAL_FIDELITY.md)。カラー化で欠けた草木・敵弾・敵・ボスの輪郭と暗部の細部を修復した。録画を色の参考にし、旧原画のポーズを保持する。6組の固定場面で、実エミュレーターのframebuffer輪郭がカラー化前ROMと完全一致。実PPUの比較画像と原作らしさの評価をリンク先に保存した。処理落ちは今回の反映条件にしていない。

起動時はカラー、SELECT／Spaceで敵・障害物だけモノクロへ切り替える。メインテーマ（8声）と六SEをSPC700で再生し、Startで音も停止・再開する。音声・ゲーム進行・奥行き寸法・自機と自弾は維持する。

[音声なしのカラー60Hz版](RESULTS_20261008_COLOR_60HZ.md)、[初期カラー試作](RESULTS_20261008_BG_COLOR.md)、[変更前のモノクロROM](../../releases/MonoSHFX2_pre_color_20261008.sfc)も残した。

カラー版にも [奥行きに沿った滑らかな拡縮](RESULTS_20261008_SMOOTH_DEPTH.md)を引き継いだ。14寸法表と開いた敵EM1の5ポーズを、Z=0..110の滑らかな寸法へ変更した。開EM1の最大段差20→1画素、ボス胴の最長同サイズ区間15→4段階。接地・移動速度の設定・解像度を維持する。以下は前版の実装と検証の履歴。

前版の [ボス限定の縮小画像と追加最適化](RESULTS_20261008_BOSS_SCALING.md)から、ボス3素材だけの縮小画像、非ボスの透明余白省略、原画の先読みと511byteの共通cache、転送量別のDMA締切、CPUのOAM生成・地面HDMA表・転送区間loopの最適化を引き継ぐ。

前版の統合ROMは通常プレイ・長期ボス各約5分で、全区分の表示遅延0、60.10fps。固定523場面と42条件のDMA限界量も検証した。新版の測定は冒頭の拡縮修正の結果に分けて記録する。

録画由来の大きな自弾・紫から緑の空・二層遠景を実装した。[検証結果](RESULTS_20261008_RECORDED_EFFECTS.md)、[静止連射GIF](results/recorded_effects_20261008/stationary_fire.gif)を保存している。森の位置・山裾の透明穴・空の範囲は[録画との画像比較](RESULTS_20261008_SCENERY_FIX.md)で修正した。以前の測定値は、その測定時のROMに対する記録。

Stage 1、地形・敵2種・射撃・反射・転倒・死亡・復帰・9節ボス・撃破・次周の進行を含む単独起動SNES ROM。MSX版の60Hz更新仕様とデータを移植し、CPUが更新・ソート、Super FX2が拡縮描画、自機・自弾・反射弾はPPUのOBJ、通常BGとHDMAが地面・遠景を担当する。

JOY1取得の前後でbusyを確認し、押しっぱなしで誤Startが混入するポーズ停止を修正済み。自機と弾はカラーOBJ。60Hzの時間刻みを1回ずつ処理し、遅れた時は次の表示枠を待つため、その時だけゲーム時間も遅くなる。指定RGBの四色・縦列の配色、直線パース、紫から緑の空と二層遠景、OBJ化とDMA、CPU/GSU時間は [RESULTS.md](RESULTS.md)。

## 遊ぶ

[../../play.cmd](../../play.cmd) を実行する。この環境では既存の `D:\HomeBrew\Mesen\Mesen.exe` を使い、プロジェクト内 `.cache/mesen_runtime` に専用設定を作る。通常のMesen設定を変更せず、オーバークロックなしでROMを開く。別の場所なら環境変数 `MONOSH_FX2_MESEN` にMesenのパスを指定する。

更新後はROMを開き直してリセットし、起動から確認する。旧ステートからの再開はWRAMの旧コードも復元する。

ROM単体は [../../releases/MonoSHFX2_v001.sfc](../../releases/MonoSHFX2_v001.sfc)。GSU/Super FX対応のMesenで開き、Port 1をSNESコントローラにしても遊べる。ROMにLua、元のNES ROM、MSX本体は必要ない。

|操作|SNESパッド|専用ランチャーのキーボード|
|---|---|---|
|左右移動|左右|左右矢印|
|下降／上昇|上／下|上／下矢印|
|連射|Aを押し続ける|Xを押し続ける|
|単発|Yの押下|Zの押下|
|一時停止／再開|Start|Enter|
|敵・障害物のカラー／モノクロ|SELECT|Space|

上下はNES原本 `src/update_player_pos.s` と同じリバース操作。最初に走り・上昇・タイトル表示があり、その間は縦操作に制限がある。死亡後は自動復帰し、ボス撃破後は次の周が始まる。

## ビルドと検証

Python 3.10以上、Pillow・NumPy、PATH上のcc65/ca65/ld65を使用する。ca65用GSUマクロcasfxは固定ハッシュを検査し、なければ取得する。固定済みソース・画像・テーブルがリポジトリ内にあるため、通常ビルドに元のNES/MSXプロジェクトは不要。

プロジェクトのルート（[README.md](../../README.md)のある場所）で実行する。

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/verify_render_release.py
python -X utf8 tools/test_game.py --scenario held --held-fire y --frames 900
python -X utf8 tools/verify_game_inputs.py
python -X utf8 tools/test_game.py --scenario play --frames 360
python -X utf8 tools/test_game.py --scenario pause --frames 360
python -X utf8 tools/test_game.py --scenario controls --frames 720
python -X utf8 tools/test_game.py --scenario stumble --frames 800
python -X utf8 tools/test_game.py --scenario boss --frames 2600
python -X utf8 tools/test_game.py --scenario stress --frames 360
python -X utf8 tools/test_game.py --scenario objects --frames 360
python -X utf8 tools/verify_full_transfer_objects.py
python -X utf8 tools/test_game.py --scenario long --frames 18000 --timeout 360
```

テストは専用Mesenを非対話モードで実行する。`long` は通常のパッド入力だけで進め、死亡・復帰・自然なボス到達・撃破・周回を要求する。`boss` はステージ終端と無敵をテスト側から設定し、通常ボス射撃の後に自弾を命中位置へ置く。HPは書き換えず、16回の頭部命中と胴反射・爆発・周回を確認する。`stress` は上下左右をclipした20本の木をテスト側から投入し、全12KiB転送とRAM guardを検査する。これらの状態書換えはLua検証専用で、製品ROMにデバッグショートカットを組み込んでいない。

`--equivalence` はC参照版と65816版を同一入力・更新回数で比較し、通常ステージとボス出現・撃破・次周を別々に確認する。`display` は低・中・高カメラの最終RGB、地上物と同じ投影表、緑四色を検査する。`packed` は7種の高速経路・clip・反転を実行したことも要求する。

`objects` は全17pose・四反転・16弾サイズ・四辺clip・点滅を検査し、OAM/CHRの独立復号と最終PPUのRGBを照合する。`verify_full_transfer_objects.py` は全12KiBと自弾三発・反射弾三発・自機の最悪の重なりを同時検証して記録し、最後に既定ROMを復元する。動的画素の照合ではMesenのホスト負荷によるframe skipを無効にする。ゲームの処理落ち判定とは別の設定。

VRAMとGSUのFBを比較し、別のPython実装でもソート、Q8.8 UV、clip、flip、透明合成の全画素を照合する。`build/game_v001/` は自動生成物。保存済み測定・画像は [results/](results/)。Mesenのテスト用メモリアクセスAPIを使った検証であり、実機確認はまだ行っていない。

原本の取り込みを更新する時だけ `tools/import_game.py`、画像を更新する時だけ `build_game.py --import-assets` を使う。環境変数 `MONOSH_MSX_ROOT` / `MONOSH_NES_ROOT` で参照先を変更できる。原本の作業ツリーを読み取って固定するので、ビルドに使った原本ハッシュは [upstream/sources.json](upstream/sources.json) を参照する。

## 実装の入口

|ファイル|役割|
|---|---|
|[frame.s](frame.s) / [game.c](game.c)|65816の更新順、パッド、カメラ、死亡時の停止、周回とC参照版|
|[upstream/](upstream/)|元のMSX Cと製品ASMの変更しないスナップショット|
|[combat_port.c](combat_port.c) / [enemy_impl.inc](enemy_impl.inc)|Z80の高速更新経路のC翻訳、射撃・EM1・反射・ボス弾DDA|
|[combat.s](combat.s)|自弾・反射弾の更新と描画準備|
|[boss_render.s](boss_render.s) / [boss_collision.s](boss_collision.s)|ボスの履歴投影、描画、頭部命中・胴反射の判定|
|[player.s](player.s) / [enemy_update.s](enemy_update.s) / [enemy_bullet.s](enemy_bullet.s)|通常移動、敵経路・開き状態、敵弾・DDAの65816更新|
|[submit.s](submit.s) / [packet.s](packet.s)|65816の描画リスト、安定ソート、10byte/体の送信情報|
|[objects.s](objects.s) / [../../tools/build_objects.py](../../tools/build_objects.py)|自機17poseを16×16の6 OBJへ分割、大きな自弾を16/32px OBJで事前生成、OAM世代固定と使用枠分の転送|
|[stage.s](stage.s) / [projection.s](projection.s)|地形の投影と、描画矩形を共用する自弾判定。更新はstage_update.s|
|[gsu.s](gsu.s) / [gsu_draw.inc](gsu_draw.inc) / [gsu_clip.inc](gsu_clip.inc) / [gsu_uv.inc](gsu_uv.inc)|生の描画情報、clip、ROM比率表によるQ8.8 UV、最近傍拡縮|
|[gsu_clear.inc](gsu_clear.inc) / [gsu_dma.inc](gsu_dma.inc)|前回の描画tile消去、前後の和集合からDMA区間生成|
|[dma.s](dma.s)|CPU側のDMA保存領域と比較用の旧範囲生成|
|[ground.s](ground.s) / [ground.c](ground.c)|通常BGの行別縦横投影、奥行き帯ごとの緑四色、独立した遠景スクロール|
|[../../tools/build_scenery.py](../../tools/build_scenery.py)|録画由来の山・森林を別BGへ配置、21色の空を間接HDMAで共有|
|[cpu.s](cpu.s) / [rom.cfg](rom.cfg)|起動・WRAM配置・CPU/GSU並行処理・HDMA・DMA|

GSU動作中、CPUのコード・定数・作業領域はWRAMだけを使う。GSUへ渡したリストはSTOPまで固定し、CPUは次フレームを準備する。GSU RAMをCPUが読む／DMAするのはSTOP後。地面の可変HDMA表は3組で、表示中・描画中・次フレーム準備が同じ表を書かない。

OBJ CHRはVRAM C000–FFFFへ起動時だけ転送し、遠景mapはB000へ移動した。OBJはpriority 3でFXの手前に置き、自機と弾をFX packetから除く。CPUが次世代のdrawを準備する前にOAMを固定し、対応するFBと同じ黒帯で転送する。22行目は輝度0でOBJ評価・CHR読み出しを再開し、23〜202行の180行を表示する。

既定設定は [config.json](config.json) のGSU UV・clip・部分転送。FX2は前回描いたtileだけを消し、今回の範囲との和集合を作る。CPUがSTOP後にDMA区間を受け取り、64byte以内の隙間をまとめた区間を送る。bytes+区間数×64が12,000以上なら全12KiB一本に戻す。bytes+区間数×128が9,216以下の時だけ、220行目まで転送開始を許す。転送は上下の黒帯内で完了させる。

全転送との比較は `build_game.py --full-transfer`、旧CPU準備版との比較は `build_game.py --cpu-clip --cpu-uv --partial-transfer`。フラグなしで既定へ戻す。設計の判断は [GSU_UV_REVIEW.md](GSU_UV_REVIEW.md)。通常ビルドはROM $5Eの比率表も画像から生成する。

GSU側はQ8.8の任意倍率とclipに対応する。原画を2枚ずつROM bankに置くため各原画の高さは128までで、近距離の一部は拡大参照になる。水平2倍・等倍・半分・1/4と、左右反転した等倍・半分・1/4の7経路は、4texel/byteのpacked参照へ切り替える。原画4画素境界の開始位置と必要な幅の条件を満たす場合だけ選び、2倍では末尾1〜7pxも処理する。Y反転と行のclipにも対応する。その他は汎用点参照で同じQ8.8の画素を描く。最大表示寸法に合わせた原画配置と同色区間描画は、引き続き改善対象。

依存の一次資料は [casfx](https://github.com/ARM9/casfx)、[Mesen GSU実装](https://github.com/SourMesen/Mesen2/tree/master/Core/SNES/Coprocessors/GSU)、ランチャーの入力設定は [Mesen InputConfig](https://github.com/SourMesen/Mesen2/blob/master/UI/Config/InputConfig.cs) と [共通キー定義](https://github.com/SourMesen/Mesen2/blob/master/Core/Shared/KeyDefinitions.h)。固定した取得元・ハッシュは [../../probes/v001/sources.lock.json](../../probes/v001/sources.lock.json)。

casfxのライセンス原文は [licenses/casfx.txt](licenses/casfx.txt) に保存した。
