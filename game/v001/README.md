# MonoSH FX2：実行可能な移植版 v001

Stage 1、地形・敵2種・射撃・反射・転倒・死亡・復帰・9節ボス・撃破・次周の進行を含む単独起動SNES ROM。MSX版の60Hz更新仕様とデータを移植し、CPUが更新・ソート、Super FX2が拡縮スプライト、通常BGとHDMAが地面・遠景を担当する。

**表示256×180、通常進行平均55.11fps。序盤は起動を含め59.55fpsで、全場面60fpsには未達。** 60Hzの時間刻みを1回ずつ処理し、遅れた時は次の表示枠を待つため、ゲーム時間も遅くなる。通常進行の表示間隔は約91%が1field、残りが2field。地面・遠景・FX層の表示修正、CPU更新の高速化、GSU側のUV・clip・範囲管理を含む検証は [RESULTS.md](RESULTS.md)。

## 遊ぶ

[../../play.cmd](../../play.cmd) を実行する。この環境では既存の `D:\HomeBrew\Mesen\Mesen.exe` を使い、プロジェクト内 `.cache/mesen_runtime` に専用設定を作る。通常のMesen設定を変更せず、オーバークロックなしでROMを開く。別の場所なら環境変数 `MONOSH_FX2_MESEN` にMesenのパスを指定する。

ROM単体は [../../releases/MonoSHFX2_v001.sfc](../../releases/MonoSHFX2_v001.sfc)。GSU/Super FX対応のMesenで開き、Port 1をSNESコントローラにしても遊べる。ROMにLua、元のNES ROM、MSX本体は必要ない。

|操作|SNESパッド|専用ランチャーのキーボード|
|---|---|---|
|左右移動|左右|左右矢印|
|下降／上昇|上／下|上／下矢印|
|連射|Aを押し続ける|Xを押し続ける|
|単発|Yの押下|Zの押下|
|一時停止／再開|Start|Enter|

上下はNES原本 `src/update_player_pos.s` と同じリバース操作。最初に走り・上昇・タイトル表示があり、その間は縦操作に制限がある。死亡後は自動復帰し、ボス撃破後は次の周が始まる。

## ビルドと検証

Python 3.10以上、Pillow、PATH上のcc65/ca65/ld65を使用する。ca65用GSUマクロcasfxは固定ハッシュを検査し、なければ取得する。固定済みソース・画像・テーブルがリポジトリ内にあるため、通常ビルドに元のNES/MSXプロジェクトは不要。

プロジェクトのルート（[README.md](../../README.md)のある場所）で実行する。

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/verify_game.py --equivalence
python -X utf8 tools/test_game.py --scenario play --frames 360
python -X utf8 tools/test_game.py --scenario pause --frames 360
python -X utf8 tools/test_game.py --scenario controls --frames 720
python -X utf8 tools/test_game.py --scenario stumble --frames 800
python -X utf8 tools/test_game.py --scenario boss --frames 2600
python -X utf8 tools/test_game.py --scenario stress --frames 360
python -X utf8 tools/test_game.py --scenario long --frames 18000 --timeout 360
```

テストは専用Mesenを非対話モードで実行する。`long` は通常のパッド入力だけで進め、死亡・復帰・自然なボス到達・撃破・周回を要求する。`boss` はステージ終端と無敵をテスト側から設定し、通常ボス射撃の後に自弾を命中位置へ置く。HPは書き換えず、16回の頭部命中と胴反射・爆発・周回を確認する。`stress` は上下左右をclipした20本の木をテスト側から投入し、全12KiB転送とRAM guardを検査する。これらの状態書換えはLua検証専用で、製品ROMにデバッグショートカットを組み込んでいない。

`--equivalence` はC参照版と65816版を同一入力・更新回数で比較し、通常ステージとボス出現・撃破・次周を別々に確認する。`display` は低・中・高カメラの最終RGB、地上物と同じ投影表、緑四色を検査する。`packed` は7種の高速経路・clip・反転を実行したことも要求する。

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
|[stage.s](stage.s) / [projection.s](projection.s)|地形の投影と、描画矩形を共用する自弾判定。更新はstage_update.s|
|[gsu.s](gsu.s) / [gsu_draw.inc](gsu_draw.inc) / [gsu_clip.inc](gsu_clip.inc) / [gsu_uv.inc](gsu_uv.inc)|生の描画情報、clip、ROM比率表によるQ8.8 UV、最近傍拡縮|
|[gsu_clear.inc](gsu_clear.inc) / [gsu_dma.inc](gsu_dma.inc)|前回の描画tile消去、前後の和集合からDMA区間生成|
|[dma.s](dma.s)|CPU側のDMA保存領域と比較用の旧範囲生成|
|[ground.s](ground.s) / [ground.c](ground.c)|通常BGの行別縦横投影、奥行き帯ごとの緑四色、独立した遠景スクロール|
|[cpu.s](cpu.s) / [rom.cfg](rom.cfg)|起動・WRAM配置・CPU/GSU並行処理・HDMA・DMA|

GSU動作中、CPUのコード・定数・作業領域はWRAMだけを使う。GSUへ渡したリストはSTOPまで固定し、CPUは次フレームを準備する。GSU RAMをCPUが読む／DMAするのはSTOP後。地面の可変HDMA表は3組で、表示中・描画中・次フレーム準備が同じ表を書かない。

既定設定は [config.json](config.json) のGSU UV・clip・部分転送。FX2は前回描いたtileだけを消し、今回の範囲との和集合を作る。CPUがSTOP後にDMA区間を受け取り、64byte以内の隙間をまとめた区間を送る。bytes+区間数×64が12,000以上なら全12KiB一本に戻す。bytes+区間数×128が9,216以下の時だけ、220行目まで転送開始を許す。転送は上下の黒帯内で完了させる。

全転送との比較は `build_game.py --full-transfer`、旧CPU準備版との比較は `build_game.py --cpu-clip --cpu-uv --partial-transfer`。フラグなしで既定へ戻す。設計の判断は [GSU_UV_REVIEW.md](GSU_UV_REVIEW.md)。通常ビルドはROM $5Eの比率表も画像から生成する。

GSU側はQ8.8の任意倍率とclipに対応する。原画を2枚ずつROM bankに置くため各原画の高さは128までで、近距離の一部は拡大参照になる。水平2倍・等倍・半分・1/4と、左右反転した等倍・半分・1/4の7経路は、4texel/byteのpacked参照へ切り替える。原画4画素境界の開始位置と必要な幅の条件を満たす場合だけ選び、2倍では末尾1〜7pxも処理する。Y反転と行のclipにも対応する。その他は汎用点参照で同じQ8.8の画素を描く。最大表示寸法に合わせた原画配置と同色区間描画は、引き続き改善対象。

依存の一次資料は [casfx](https://github.com/ARM9/casfx)、[Mesen GSU実装](https://github.com/SourMesen/Mesen2/tree/master/Core/SNES/Coprocessors/GSU)、ランチャーの入力設定は [Mesen InputConfig](https://github.com/SourMesen/Mesen2/blob/master/UI/Config/InputConfig.cs) と [共通キー定義](https://github.com/SourMesen/Mesen2/blob/master/Core/Shared/KeyDefinitions.h)。固定した取得元・ハッシュは [../../probes/v001/sources.lock.json](../../probes/v001/sources.lock.json)。

casfxのライセンス原文は [licenses/casfx.txt](licenses/casfx.txt) に保存した。
