# 上端の直接描画とCPU側の検証

60fps未達。公開ROMは更新しない。

|場面|実field数|完成画像数|FB/VRAM一致枚数|表示間隔field数:回数（初期2枚除外）|
|---|---:|---:|---:|---|
|temporal|600|502|126|{'1': 494, '2': 4, '3': 1}|
|bosstemporal|1200|1077|135|{'1': 1043, '2': 31}|

上端にはみ出すが下端が画面内に収まるspriteは、ROMの行呼び出し列の途中から末尾のRTLまで直接実行できる。I-RAMへ行列をコピーする必要がなく、ボスの1枚で最大約5.5msだった例を約2.3msへ短縮した。縮小・形状・クリップ結果を変えない。

小さいコードをMVN命令でコピーする`--cpu-code-copy`、PPU DMA中だけ命令で消去する`--cpu-fill`、背景コピーを代行する`--cpu-far`を試したが、ボス1200fieldの完成枚数は1070・1050・1056等で直接呼び出しだけの1077枚を改善しなかった。常時MVNと、DMA要求時のみMVNの探索は区別する。条件付き経路で転送長をAに戻し忘れた版は画素不一致として棄却し、修正版のcpufill/bosscpu/bosscpufarのみを検証済み結果とする。`bosscpu`はビルド失敗後に一つ前のcpu-fill版を測った名前であり、cpu-farの結果には使わない。

`--shape-cache`は2048BのBWRAM表で寸法検索結果を再利用するが、ボス1077枚のままで効果が乏しい。`--temporal-sort`は前回の順序を初期値とし、同じキーなら現在の元indexで比較して元の安定順を保つ。元の順序による独立sortと全フレームで照合し、FB/VRAM/OAMも一致したが、表示枚数は同じだった。上表はtemporal-sortを有効にした同一ROMの結果。

packet生成の初期化・sort・コピーを分離計測し、割り込み時間を除いた値も保存する。表示転送で割り込まれた関数の経過時間を、純粋な演算費用と混同しない。全体の次の制約は描画DMAとキャラクタ変換DMAの共有であり、変換済みデータをBWRAMへ先行保持する方向を検証する。

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct --pipeline-irq --pipeline-depth 5 --redraw-all --merge-dma --large-edge-cache --triple-bw --fast-dma --temporal-sort
python tools/test_sa1_game.py --frames 600 --scenario temporal
python tools/test_sa1_game.py --frames 1200 --scenario bosstemporal
python tools/report_sa1_pipeline_tail.py
```
