# 先行描画とVRAM先行転送の途中結果

60fpsは未達。既定の公開ROMは更新しない。SA-1専用分岐で、`--pipeline --pipeline-direct`を追加した。

二つのBW-RAM画像へ交互に直接描画し、各面の前回使用から二世代分の変更領域を再合成する。画像コピー方式も`--pipeline`として保持する。OBJ、地面HDMAの参照先、描画packetを512B×3のmetadataへ固定し、表示世代を対応させる。完成画像だけを順に表示する。転送終了後に残った非表示時間は、次の画像の未表示CHR面への転送に使う。SA-1描画DMAと変換DMAのレジスタは排他する。

|場面|実field数|完成画像数|FB/VRAM一致枚数|完成画像間のfield数:回数（初期2枚除外）|
|---|---:|---:|---:|---|
|directpipe|600|444|125|{'1': 380, '2': 59, '3': 2}|
|boss|1200|830|131|{'1': 557, '2': 264, '3': 6}|

実際の画面更新間隔に2・3fieldが残る。固定field数での進行量には差があるため、この表を同一packetの厳密な速度比とは扱わない。ボス戦は90field以降にテスト側からステージ終了条件を設定している。

検査上の修正: Mesenのcallback内のLua例外を`pcall`で捕捉し、失敗ファイルと終了コードでPython側へ伝える。従来の直接assertだけではcallback内の失敗が実行停止につながらない場合があった。画素比較は従来からPython側で実施している。各世代の欠落・順序違い、表示中のpage切替、転送終了の非表示期間超過を検査する。PPUの残り時間は各descriptorの直前に9bit垂直カウンタから求める。

非採用・修正した問題:

- S-CPUからDCNT($2230)は設定できない。SA-1側が変換モードを設定し、許可を返す。
- DMA設定を毎scanlineで排他する費用と、描画画像をコピーする費用が大きい。
- 一つの大型native call chainを最後まで実行すると、転送要求への応答が遅れる。現在は最大8行に区切る。
- IRQの転送待ち中にjob解放が来た場合は、doneを下げただけで新jobを取りこぼさないよう、解放状態も保持する。
- 地面buffer待ちをゲーム処理の末尾へ移して、前段の処理を先行する。

再現:

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct
python tools/test_sa1_game.py --frames 600 --scenario directpipe
python tools/test_sa1_game.py --frames 1200 --scenario boss
python tools/report_sa1_pipeline.py
```

次はDMA排他の設定回数を減らし、SA-1 IRQによる転送要求への応答も検討する。素材・物量・ゲーム内の更新回数を削って60fps扱いにはしない。
