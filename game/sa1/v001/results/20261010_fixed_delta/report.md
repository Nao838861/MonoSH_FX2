# 透明map差分による消去CHR削減の試験

原画・縮小・反転・表示世代を維持したまま、空になったtileを共有mapの透明tileへ切り替え、二世代前の領域を消すCHR転送を省いた。**現行固定mapより遅く、不採用。60fps未達。試遊ROMはf8dbe7cの検証済み版を維持する。**

| 方式 | fields | 表示枚数 | 画素一致 |
|---|---:|---:|---:|
| 現行固定map＋no-history＋bullet-resident | 800 | 644 | 168 |
| SA-1生成list＋本体CPUのmap直接更新 | 800 | 638 | 168 |
| SA-1生成の連続区間＋ROM列からのmap DMA | 800 | 634 | 168 |
| DMA版の先頭120画面検査 | 270 | 120 | 120 |

比較入力はlogic世代ごとに固定。保存した描画packetも同じ世代の現行版と一致する。平均fpsだけで達成判定しない。

`--fixed-map-delta` はCHRを現在maskだけに絞り、占有maskの前世代との差分をSA-1が生成する。WRAMに1472B×8枠を確保し、各描画recordがmap更新listを所有する。40tile以下は本体CPUで表示直前に更新し、それ以上はSA-1が作った1472BのmapをDMAする。`--fixed-map-delta-dma` は変化した連続tileを最大48記述子へまとめ、自然番号列と透明列のROMからDMAする。超過時だけfull-mapへ戻す。更新費用を非表示時間の予約に含める。

重い爆発区間では直接更新版もfull-mapに戻ることが多い。DMA版は小区間の設定費用が増え、消去CHRを省く利点を相殺した。速度改善を主張しない。

初期失敗も証拠zipへ保存する。v1/v2はASM追加後のsegment復帰不足で後続のblank table等の配置が変わった。v3は同問題でHDMA期間検査が失敗。v4はdirect-pageとabsolute addressingの取り違えによりlistをWRAMから読めず、2枚目のmapが更新されなかった。GSU関数の後でCODEへ復帰し、WRAMの添字付き読出しを`a:$0000,x`にして修正した。失敗版を速度比較に含めない。VRAM各byteへの検査callbackは測定器の実行時間を大きく増やすため撤去し、map更新の入口・出口と各DMA入口・出口で実際の非表示状態を確認する。

`comparison.json`と`evidence.zip`に4正常試験・失敗例・ROM/ラベル/manifestのスナップショットを保存する。
