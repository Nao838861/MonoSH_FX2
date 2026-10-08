# カラー版を60Hzへ復帰

2026年10月8日。2bppカラー、SELECT切替、滑らかな奥行き拡縮、256×192内部FB／256×180表示を維持した。

**同一ROMをMesen 2.1.1・NTSC・GSU 100%で検証し、通常と継続ボスの各18,000fieldで60.0988118623fps。起動後の全表示間隔が1fieldで、遅延・同じblank内の重複提示とも0。実機は未検証。**

ROM SHA-256: `0c7282ce976a9345adcd1719d6aa14fa8088e553cfa01a0ba95e1a134955da38`

変更元: `4c5ec389e67737837a09980069374267d24e7c20`。同コミットのカラー試作ROMは `4ef5a95fec70a4ee3dfcf3b9f39ea38180aa138fd44b7709fed8b21704197025`、保存済み試験では通常31.62fps／ボス33.96fpsだった。前後で試験時間・入力シナリオが異なるため、この旧値は参考値として扱う。今回の60Hz判定はCPU時間やエミュレータの実行速度から推測せず、DMA開始の物理fieldから数えた。

## 実装

- GSUが描画パケットと同じ順で、8×8中心のQ8.8参照・clip・反転・透明セルを厳密に処理して属性を生成する。CPUは完成した世代だけをVRAMへ転送し、モードを同時にラッチする。
- GSU用の色表は既存2MiB ROMの未使用領域 `$5E:C000..$EEFF` に追加。原画、縮小画像、UV表を置き換えない。従来の511byte描画キャッシュも維持する。
- SRAM `$1000..$12FF` の属性と `$1300..$15FF` の前回属性を比較し、最大12区間へまとめて差分転送する。初回は全768byte。
- 全FBだけでなく、大きい部分FBと属性が同じblankに収まらない場合も、裏mapへ先行転送する。CGRAMはHDMA停止中に先に更新し、その後にHDMAを再開してmap／FBを送る。
- 転送量に基づく締切式を維持し、少量転送の受付上限を240行から255行へ拡張。OAMの転送準備をblankの前へ移し、blank内の不要なHBlank待ちを省いた。
- 地面の横HDMAはカメラ高さ・world phaseが同じバッファを再利用する。空・遠景・縦スクロール・パレットアニメーションは毎回更新する。
- OAMラッチは新旧の使用範囲とhigh-tableだけをコピー。パケットは225～250行のVBlank中だけ逆方向DMAを使い、それ以外は従来のMVNを使う。
- CPU属性生成の互換経路も保持。行辞書、direct page、一部乗算の省略を独立に検査した。

## 最終ROMの検証

|検証|結果|
|---|---|
|通常18,000field|17,975画像、17,974区間すべて1field、60.0988118623fps|
|継続ボス18,000field|17,976画像、17,975区間すべて1field。生存ボス12,910画像を含む|
|固定523場面の再描画|2,309画像の全FB／OBJ、1,773,312セルの属性とVRAMが一致|
|カラー／モノクロ切替|243画像、186,624セル。反転・clip・1/2px・透明・描画順・保持／再押下を確認|
|旧60Hz版とのゲーム状態比較|通常5,966更新、ボス1,942更新。1更新1,408byteの状態と有効drawが一致|
|元絵・縮小画像|原画249,538画素、縮小1,578,384画素、余白16,268行を独立検証|
|奥行き・地面|14寸法表＋EM1の5姿勢の平滑化を保持。158,269本の地面境界を確認|
|DMA限界量|220～255行×1/32区間の72条件、各99～100画像。配色を毎回切替え、18行までに完了|
|追加の境界試験|6,110画像、1,253,370 HDMA行、1,869,660 SRAMガードbyteを検査|
|全FB＋最大OAM＋毎回切替|最遅21行・HClock864。22行のOBJ準備まで500 master clocksの余裕|
|操作・表示|17姿勢／4反転／16弾寸法、3カメラの最終RGB、方向、射撃、ポーズ、転倒、撃破・次周、押しっぱなしを確認|

証拠: [性能](results/color60_20261008/profiles.json)、[固定場面](results/color60_20261008/replay/comparison.json)、[ゲーム状態](results/color60_20261008/logic/)、[DMA](results/color60_20261008/dma_deadlines/summary.json)、[境界試験](results/color60_20261008/pipeline_audit_summary.json)、[環境](results/color60_20261008/environment.json)、[ファイルhash](results/color60_20261008/SHA256SUMS.json)。trace、実行Lua、全標本も同じ場所に圧縮保存した。

## 再実行

PATH上のcc65/ca65/ld65とPillow、numpy、Mesen 2.1.1を使う。検証したcc65はcommit `71746c829e77f74c2b601a7d16821170c2610df3`。`MONOSH_FX2_MESEN` に実行ファイルを設定する。Linuxの本環境では公式Mesenの起動にシステムlibstdc++のLD_PRELOADが必要だった。ハッシュは環境JSONを参照。

```sh
python tools/build_game.py
python tools/test_game.py --scenario color --frames 360 --timeout 180
python tools/test_game.py --scenario display --frames 720 --timeout 180
python tools/benchmark_render.py --name release --edges --fixtures game/v001/results/boss_scaling_20261008/base_fixtures.json.gz --reuse-build
python tools/profile_boss.py --minimal --frames 18000 --timeout 1200 --allow-unreleased --output boss_profile_release
python tools/profile_boss.py --minimal --frames 18000 --timeout 1200 --boss-fire none --allow-unreleased --output boss_profile_releaseboss
python tools/report_color_60hz.py build/game_v001/boss_profile_release --require-60hz
python tools/report_color_60hz.py build/game_v001/boss_profile_releaseboss --require-60hz --require-boss
python tools/verify_scaled_assets.py
python tools/verify_depth_sizes.py
python tools/verify_dma_deadlines.py --output color60_20261008/dma_deadlines
```

`--minimal` はホスト側の詳細区間callbackを省く計測設定で、ROM・CPU/GSU設定・入力・描画検査は変えない。表示間隔とCPU/GSU完了時刻は保存する。

境界試験の `pipeline_audit.zip` は同じROM、ラベル、4本のLuaと結果を収録。移動先に合わせてLua先頭のoutputを変更し、同梱READMEのコマンドで再実行できる。

## 残る制約

60Hzの確認範囲は上記の自然入力と継続ボス。64体重ねなど意図的な過負荷は正しさ試験であり、全人工場面が60fpsという意味ではない。2bpp／8×8パレット共有による色干渉も方式上そのまま残る。

物理SNES／Super FX2、PAL、オーバースキャンは未検証。特にS-CPU初期版にはDMAとHDMAの終了タイミングに関する既知の制約がある。今回の逆方向パケットDMAはVBlank内へ制限したが、従来の地面・descriptor DMAを含む実機全体の保証には実機検証が必要。旧ステートはWRAMコードも復元するので、ROMを開き直してリセットすること。
