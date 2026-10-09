# 先行変換と小規模な描画改善の比較

60fps未達。元の素材・物量・通常クロックを維持。公開ROMは更新しない。

|方式・場面|実field数|表示枚数|FB/VRAM一致枚数|表示間隔field数:回数（初期2枚除外）|
|---|---:|---:|---:|---|
|stageprefetch|600|494|126|{'1': 479, '2': 12}|
|bossstageprefetch|1200|1010|134|{'1': 912, '2': 95}|
|fastleftmemo|600|499|126|{'1': 487, '2': 9}|
|clearlinear|600|502|126|{'1': 493, '2': 6}|
|bossclearlinear|1200|1078|135|{'1': 1045, '2': 30}|

`stageprefetch` は24KiBのWRAMに変換済みの一画像を保持する。地面の読み取り表をROMへ置き、使っていないボス描画順配列もROMへ移した。ゲーム素材は変更していない。S-CPUの通常処理からBW-RAM→WRAMのキャラクタ変換を行い、VIRQではWRAM→VRAMだけを行う。描画用DMAと表示DMAの同時使用を避けられるが、S-CPUの転送と先行変換の開始タイミングが制約となり、二面への直接変換転送より遅い。初期の8KiB往復コピー方式（staged/bossstaged）とは別の実装・結果。

`fastleftmemo` は左端から大きくはみ出す絵だけ、二分探索で可視部分の先頭命令を探してROM末尾まで直接実行する。連続する同じ行コードの検索結果を再利用する。正しい画素を得るが、道中の最良枚数を改善しないため既定にはしない。

`clearlinear` は背景の遠景が全幅を上書きする14行の事前消去を省く。寸法の検索は同じ幅に属する最大4個の高さを順に調べる。旧二分探索の範囲・中点計算を減らす。道中の表示枚数は502で同じ、ボスは1077から1078。平均SA-1時間はボス約11.47msから11.16msへ下がったが、一枚ずつの表示間隔はまだ崩れる。固定fieldの比較は論理進行量が異なるので、厳密な同一packetの速度比ではない。

表示中のVRAM面を非表示期間内に一括更新する方式も試した。転送の設定費用を含まない初版は38枚目で待ち続けた。設定費用込みの版も後半でVRAM画素不一致を検出したため棄却し、実装は削除した。性能・正しさの根拠に使わない。

画面切替を直接計測すると約0.21ms、プレイヤーCHR更新を含む最大は約0.60msだった。しかし切替予約量を下げた版は900/1900unitsでも1500/2400unitsでも長時間検証中に走査線23へ越境したため棄却し、実装は削除した。現在のDMA見積りは長い転送の実時間との差も予約量で吸収している。切替時間だけから予約量を減らしてはいけない。

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct --pipeline-irq --pipeline-depth 5 --redraw-all --merge-dma --large-edge-cache --triple-bw --fast-dma --skip-far-clear --linear-shape
python tools/test_sa1_game.py --frames 600 --scenario clearlinear
python tools/test_sa1_game.py --frames 1200 --scenario bossclearlinear
python tools/report_sa1_pipeline_stageclip.py
```

先行変換は `--staged-conversion`、左端の試作は `--clip-edges --fast-left-clip` を基本方式へ追加する。各結果のROM SHAとlabels SHAはJSONに保存して区別する。evidence.zipは全計測JSON、Lua、全画素の照合対象、最終画面を収める。
