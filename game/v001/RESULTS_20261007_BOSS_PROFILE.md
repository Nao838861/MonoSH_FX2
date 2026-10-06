# ボス戦の最悪負荷：連続60fpsにはGSU時間を約28%短縮、目標30%

2026年10月7日。**最新版ROMで観測したボス戦の最悪GSU時間は19.129ms。連続60Hzに使える枠は約13.760msなので、GSU全体の時間を約28.1%短縮する必要がある。速度換算では約39.0%向上。余裕込みの開発目標は30%短縮、約42.9%の速度向上。** CPUの時間は同じ場面で7.758〜8.440msだった。処理時間の短縮率と処理速度の向上率は分母が異なる。

これは観測した同程度の重い画像を連続で提示するための見積もりであり、最適化後の全場面60fpsを達成した結果ではない。公開ROMのコード・画像・表示領域は変更していない。[集計](results/boss_profile_20261007/summary.json)。

## 計測条件

ユーザー依頼原文：

> ボス戦の一番処理落ちするところは、60fpsまであと何%最適化しないといけないか計測できる？

`D:\HomeBrew\Mesen\Mesen.exe`と同じバイナリの専用コピー、GSU速度100%、NTSC、表示256×180・内部FB256×192・2bpp・部分転送。ゲーム時間をMesenのmaster clockで観測し、ホストPCでの実行時間から性能を換算していない。

|試験|field数|提示画像|ボス戦の画像|内容|
|---|---:|---:|---:|---|
|通常進行|18,000|17,139|1,806|ステージはA押しっぱなし、ボス戦は顔へ方向入力しながら射撃。撃破・次周も確認|
|ボス戦を長く観測|18,000|14,631|9,565|同じ通常進行で到達後、ボス戦だけ射撃を止める。HP16を維持し、多数の姿勢と死亡・復帰を観測|
|固定設定・OAMの追加計測|720|690|0|HBlank待ちの終了後からFB DMA開始までの時間を分離|

計36,720field。ボス戦11,371画像、FB/VRAMとRAM guardを1,768回照合。別実装によるUV・clip・透明合成とOBJ照合は58＋49＋3＝110場面が通過した。ステージ送り、無敵、敵HP、弾位置などのゲーム状態の書き換えは使わず、パッド入力で進めた。待ちを含む物理fieldと論理更新を区別し、DMA開始時刻で提示間隔を数えた。

CPUは次世代の更新・描画準備、GSUは提示予定の画像を並行処理する。画像の開始時にボス状態・描画件数を固定し、CPU終了・GSU終了・合流・DMA準備完了・DMA開始/終了を画像ごとに記録した。GSU時間には消去、clip/UV準備、縮小合成、DMA範囲生成を含む。縮小コピーのループだけの時間ではない。

## 最悪画像と必要短縮率

|項目|通常進行・画像10,678|射撃停止・画像5,523|
|---|---:|---:|
|GSU全体|19.129ms|19.129ms|
|並行するCPU|8.440ms|7.758ms|
|直前のFB DMA|1.700ms|1.699ms|
|次のGSU開始までの準備|0.842ms|0.843ms|
|CPU/GSU終了からDMA待ちに入るまで|0.202ms|0.203ms|
|固定設定・OAM転送の費用|0.134ms|0.134ms|
|連続60HzでCPU/GSUに残る枠|13.760ms|13.760ms|
|GSU時間の必要短縮率|28.07%|28.07%|
|GSU速度の必要向上率|39.02%|39.03%|

固定設定とOAM転送は同一ROMの固定68bytesの経路を690画像で追加測定し、最大0.134281msを採用した。最悪画像は14コマンド、FB 3,792bytes・7区間。全12KiB転送による最悪ではない。

NTSCの1fieldは約16.639264ms（60.0988Hz）。並行するCPUとGSUを足さず、長い方を用いる。

```text
連続更新の時間 = 直前DMA + 準備 + max(CPU, GSU) + 合流後の準備 + 固定設定/OAM
GSUに残る枠 ≈ 16.639 - 1.699 - 0.843 - 0.203 - 0.134 = 13.760ms
時間の必要短縮率 = 1 - 13.760 / 19.129 ≈ 28.1%
速度の必要向上率 = 19.129 / 13.760 - 1 ≈ 39.0%
```

HBlankポーリングの位相に1scanline（約0.064ms）の余裕を追加すると、必要短縮率は約28.4%。**30%短縮ならGSU時間は約13.391msとなり、約0.369msの余裕を持てる**ので、最初の改善目標にする。

最大画像のプレイヤー状態は死亡中だったが、生存中・ボス戦継続中にも19.079msの画像がある。死亡画面だけに固有の問題ではない。今回のボス戦全画像ではCPUを短縮しなくても計算上の枠に収まり、まずGSUを改善する方針が妥当。ただし描画ループだけを改善する場合、GSU内でそのループが占める割合の測定が必要で、ループ自体の30%短縮がGSU全体の30%短縮とは限らない。

## 単発の締切と連続60fpsは分ける

小さい転送は220行まで開始を許可するため、現在のDMA位相で1回だけ締切へ間に合わせる枠は約14.845msだった。この比較では22.4%の時間短縮、28.9%の速度向上になる。しかし開始を遅らせた画像は次の描画開始も遅らせる。開始猶予を毎画像へ足すことはできず、連続60Hzには上の約28.1%が必要。

同様に、19.129msを16.639msへ短縮するだけなら約13.0%だが、毎画像のDMAと準備を無視している。これを60fps達成の目標にしない。

両試験の最も重い60field窓は30画像、約30.05fps。締切を超えると次fieldの黒帯を待つため、処理時間が倍にならなくても表示は30fpsへ落ちる。30fpsから60fpsへ戻すために、処理速度を必ず2倍にする必要はない。

## 保存データと再実行

通常進行は [natural/budget.json](results/boss_profile_20261007/natural/budget.json)、射撃停止は [linger/budget.json](results/boss_profile_20261007/linger/budget.json)。各フォルダの`timings.jsonl.gz`に生の時計・走査線・状態、`analyzed.jsonl.gz`にボス画像ごとの枠と必要率、`trace.jsonl.gz`に従来の検証ログ、`test.lua.gz`にその実行で使った観測スクリプトを保存した。射撃停止側には最大画像のFB・packet・OAMも保存した。

初回の通常進行ログではHClockを保存していなかったため、master clockとPPU frameCount/scanlineから復元した。225行でframeCountが増えること、奇数fieldの240行が4clock短いこと、uint32のwrapを考慮。後続の射撃停止・追加計測では`memoryManager.hClock`を直接保存し、全ての時計で復元値との一致も検査した。根拠は [MesenのPPU実装](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/SNES/SnesPpu.cpp) と [時計の実装](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/SNES/SnesMemoryManager.cpp)。

プロジェクトルートで実行する。

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/profile_boss.py --frames 720 --timeout 60 --output boss_profile_serial
python -X utf8 tools/profile_boss.py --frames 18000 --timeout 360
python -X utf8 tools/profile_boss.py --frames 18000 --timeout 360 --boss-fire none --output boss_profile_linger
python -X utf8 tools/analyze_boss_profile.py boss_profile
python -X utf8 tools/analyze_boss_profile.py boss_profile_linger
```

ROM SHA-256：`a9e07ed26d26d7e27ec50c8204fb206664445c5c46af8f3723549737d935f4f6`。Mesen SHA-256：`d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b`。

自己評価：最新版・実パッド入力・二つの長時間試験で最悪負荷を観測し、平均fpsからの逆算を避けた。単発の締切と連続更新の枠を分離した。残る限界は、最適化後にCPU/GSU・DMAの位相とゲーム状態が変わること、未観測の入力・姿勢や実機に対する最悪保証ではないこと。次の判断はGSU全体の30%短縮を試し、同じ種類の長時間入力で毎field提示を再計測する。
