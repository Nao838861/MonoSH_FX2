# 録画由来の自弾・空・二層遠景

通常起動の `releases/MonoSHFX2_v001.sfc` を更新した。発射直後の自弾は56×32ドットの水色の輪で、自機を動かさずに撃っても左右に見える。[静止連射GIF](results/recorded_effects_20261008/stationary_fire.gif)、[実画面](results/recorded_effects_20261008/stationary_fire.png)、[三つのカメラ高さ](results/recorded_effects_20261008/camera_heights.png)を保存した。

ROM SHA256: `61c228dd8b7576194756d260e84aa04e236af8e28b01aa99512e560673e049b9`。

## 素材と実装

動画の1920×1080内のゲーム部分960×672を、最近傍で元の320×224へ戻した。78.100秒の自弾と58.000秒の遠景を使う。自機が覆う弾の中央は露出色と対称部分で補修し、512pxの遠景外周は実画素の反転で延長した。推定を含む箇所と元の切り出しは[素材記録](assets/recorded_effects/README.md)へ残した。

自弾は透明1＋最大15不透明色・RGB5、独立したOBJパレット1。発射直後56×32は32×32 OBJ二枚、40×24は32×32一枚＋16×16二枚、以降は32×20、24×16、16×12などへ縮小する。自機17ポーズと全縮小パターンは126/128枠・16,128byte。毎フレームにCHRを再転送せず、消えた枠を含む必要範囲のOAMだけを送る。

当たり判定、発射周期、弾の寿命、三発の枠、反射の速度と寿命は維持する。反射弾は発光輪の12×8版とし、最悪でも「発射弾三発24tile＋反射弾三発6tile＋自機4tile＝34tile/走査線」に収める。画像の分割数は自弾一発最大3 OBJ。

Mode0のBG4に紫の山、BG1に緑の森林を置く。森林は山の2倍の横速度で、512px周期。縦位置は地面のカメラに追従する。BG2のFX画像を高優先にし、森林で敵や物体を隠さない。2bppの山と森林は各タイル3不透明色・各BG8パレット、共用CHRは220タイル・3,520byte。

空の紫→緑は録画から採った21色の間接HDMA6。色列84byteを共有し、開始行だけ三組の10byte表へ作る。HDMAとスクロールレジスタの共有ラッチが競合しないよう、黒帯内のレジスタ更新中だけHDMAを停止する。

## 検証

- 三カメラ高さ0/32/64で、全四BG・OBJ・空のHDMAを合成した最終PPUのRGB全画素が独立した参照と一致。山の横位置17、森林34も確認。
- 自機17pose、全四方向反転、弾の16論理サイズ、画面端・点滅・三発＋反射三発の重なりを検査。85場面のFB全49,152画素とOBJが一致。実PPU66画面・68,057 OBJ画素も一致。走査線overflowはEndFrameで確認する。
- 全12KiBのFB転送と大きな自弾を同時に検証。21行までに完了し、22行のOBJ準備と23行の表示開始に間に合う。以前の68byte固定OAM・最遅20行という余裕の値は現行版へ流用しない。
- 静止したA連射900fieldで、大きな輪が自機の左右へ出ることを実画面で確認。左上＋Y900fieldとStartポーズ/解除も検証する。
- 自然な通常入力18,000field、約5分で17,934画像を提示し、道中・ボス・撃破後・次周が進行した。FB/VRAM/OBJの60標本が一致し、GSU guardとOBJ overflowを検査した。

|区分|平均fps|表示遅延の画像数|測定した間隔数|最低の約1秒窓|
|---|---:|---:|---:|---:|
|道中|59.941|41|15,585|46画像|
|ボス|60.032|2|1,802|58画像|
|撃破後|60.099|0|537|60画像|

DMA開始の物理fieldで提示間隔を数える。完了callbackが225行をまたいで生じる0/2の揺れを遅延と混同しない。詳細は `results/recorded_effects_20261008/long/performance.json` と圧縮した生timings。**素材追加前の「遅延0回の60.10fps」は現行版の測定結果ではない。** 今回は少数の提示遅延が残る。任意の操作や実機を保証する検証でもない。

## 再実行と自己評価

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/test_game.py --scenario display --frames 720
python -X utf8 tools/test_game.py --scenario objects --frames 360
python -X utf8 tools/test_game.py --scenario held --held-direction none --held-fire a --frames 900
python -X utf8 tools/verify_full_transfer_objects.py --output recorded_effects_20261008/full
python -X utf8 tools/profile_boss.py --frames 18000 --timeout 600 --allow-unreleased --output boss_profile_effects
```

静止射撃の読みやすさと、遠景の二層化という依頼の二点を実画面へ反映できた。単に弾の色を変える修正や山を一枚の帯にまとめる修正ではない。画像の復元には補修と反転延長があり、元のアーケード全パターンを抽出できたとは扱わない。既存の画面領域、ゲーム更新、衝突を保ち、表示余裕と実測性能の変化も残した。
