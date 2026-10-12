# 可視域を左右128pxずつの二面へ分ける容量・命令量の算定

ゲームへの二面描画は未統合・速度未測定。下記の独立ROMで転送だけを検証済み。60fps達成結果ではない。既存の広幅バッファ試験は512pxから中央256pxをコピーし直す費用で遅くなった。今回の候補は通常の256px幅バッファを二つ使い、各面の中央128pxだけを文字変換DMAから直接読む。左右64pxずつの余白があるため、大きな爆発も画面端の退避なしで描ける場合が増える。原画や寸法を減らす案ではない。

Mesenの[SA-1実装](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/SNES/Coprocessors/SA1/Sa1.cpp)では、2231hのCharConvWidthを最大5（32 character、256px）へ制限している。従って512px幅へ設定するだけで旧コピーを省く案をMesenで使えるとは扱わない。この調査は実装コードに基づくもので、実機上の未定義レジスタ値の挙動を測定したものではない。

現行固定map基準a9bcd247の道中653packetを解析した。左面にはglobal x=0..127が見える物体をx+64へ移して描き、右面には128..255が見える物体をx-64へ移して描く。painter順と全画素・色位相・寸法を維持する。各面の中央128px（packed byte32..95）を取り出して連結する。全データは直前の試験の `../20261013_direct_left/evidence.zip` 内 `baseline_road/packet_trace.bin` と `rom_baseline/MonoSHSA1_4bpp_game.sfc` にある。

|全653packet|現行|二面の算定|
|---|---:|---:|
|可視範囲に関係する物体数|6264|6965|
|native行の命令byte＋行macro byte|5248257|6137718|
|左端が切れる物体|239|15|
|右端が切れる物体|365|2|

native命令量は約16.95%増える。二面とも関係する物体を二回描くためで、端処理の減少だけでは速くなると断定できない。重い530..570の41packetに限ると、命令量1062117→1123641（約5.79%増）、端処理100→8件。元画像から生成したpacked参照絵で、この41packetの左右の再合成が元の256px画像へ全画素一致した。これはホストの参照計算であり、Mesenで二面を描画・転送して一致を確認した結果ではない。

1ゲーム画像は2×192×128=49152B、三画像で147456B。既存BW-RAMの40/41/42 bankの0400/8400の組を一画像として使う候補なら、二面の行strideは既存と同じ128Bでnative行コードを生成し直さずに済む。一面256pxのCC1を使い、bandごとに中央16tileを送る。既存の変換元を0400とすると、右面8400は変換後のvirtual addressも+8000になる計算だが、実DMAでの確認が必要。可視範囲を転送する総byte数は二面化だけでは減らない。中央を跨ぐrunは二つへ分ける必要があり、descriptor数は増え得る。

次の順で候補を検査する。

1. 実施済み：小さい独立ROMで、同じbankの0400/8400の二面から中央16tileずつをCC1で直接読む実DMAを検証した。詳細は末尾。512px幅の未対応設定やCPUの中央コピーに依存しない。
2. 実ゲームpacketを二面へ再生して、元のnative行・palette・全画素を確認し、描画の重複と端処理減少の実費を測る。軽い二面probeを全体60fpsと扱わない。
3. 統合する場合は可視dirty範囲の消去・転送sourceを左右へ写像する。余白のpixelは表示しないが、境界wordのread-modify-writeと既存の端保護は検査する。wide-clearをそのまま使うと余白まで余分に消すので注意する。
4. raw七画像から三画像への変更による待ち行列の減少、追加descriptor、消去設定費も含め、同じ道中・ボスの長区間で判定する。

算定コード `tools/analyze_sa1_split_viewport.py` のnativeBytesは速度ではない。圧縮弾worker、分岐・dispatch、clear/dirty、CC1/PPU、待ち行列の費用は含まない。今回の入力に圧縮弾素材6/7/8/37は0件であり、武器全種を網羅したとは主張しない。解析自体はROMや配布版を変更しない。

```text
python tools/analyze_sa1_split_viewport.py build/sa1_game/movestress_detinput_captureburst_directleft_currentbase_tracepalette build/sa1_game/flame_currentbase_build/MonoSHSA1_4bpp_game.sfc --output game/sa1/v001/results/20261013_split_viewport/analysis.json
```

## 独立ROMでのCC1→PPU DMA転送確認

`split_cc1_probe.s` と `tools/probe_sa1_split_cc1.py` で転送だけのROMを作り、Mesen上で実行した。入力の二面bitmapはホストで原画から生成してBW-RAMへ置く。SA-1が絵を描いた試験ではない。その後、SA-1 workerが2230h=B1/2231h=15で文字変換1を開始し、S-CPUがPPU DMAを行う。source baseは一度だけ0400へ設定し、右面の読み出しをvirtual address +8000で行う。bandごとに左16tile・右16tileの順に転送し、実VRAMを保存して原画の期待planarデータへ照合する。

41ゲーム画像＋全16色・各行/tile/左右が異なる検査パターンの計42件が、全24576B一致した。source bank40/41/42を全て通り、各bankのprefix表位置6A00/EA00に置いた128Bのguardも変更されなかった。二面の中央を詰め直すCPUコピーや、512px幅CC1は使わない。ROM SHA256は6c23de6bd25d8ac19479fb7d2598934379a370db370624f2c8395f33b8374669。

全画面は48 DMA descriptor・24576Bで約10.116～10.118msかかった。これは全時間forced blankの独立試験であり、ゲームのVBLANK内に全画面を送れた意味ではない。実ゲームでは現行のdirty転送量を保持する必要がある。SA-1描画費、消去、IRQとの競合、二面へのrun分割、三画像の待ち行列はまだ測定していない。

初回buildはheaderのROM名が1B長くlinkできず、ROM測定前に修正した。失敗ログも証拠へ保存。`cc1_transfer_evidence.zip` は402378B、SHA256=87e7c66d09a4539404f25ea94129e13a035d45971a9fef92b73f2b810165dee6。ROM・labels・cfg/map・Lua・入力二面bitmap・期待/実VRAM・timings・emulator logを含む。実行コマンドは以下。ゲームのbuildや配布ROMは変更しない。

```text
python tools/probe_sa1_split_cc1.py
```

## 同じSA-1描画器による左右の再生比較

`tools/test_sa1_game.py --split-fixture-source` と `sa1_split_fixture.py` で、重い41画像を一面・左面・右面として123 jobの周期で実際のSA-1へ再生した。元のnative行コード、色、寸法、painter順を維持し、左右のpacketだけ座標を±64px移す。ホストは絵を描かず、入力packetを書き替える。通常の一面ROMを使うため、二面同時の所有権や転送はまだ検査していない。

500表示でPPU・VRAM・参照画像が全画素一致し、165組の左右sprite再合成も一面と一致した。41画像全てを含む。中央の近景stripはこの再生では元の位置へ描くため、再合成比較はspriteのalpha領域に限定する。各表示のstripを含む全画像は共通のPPU検査で確認している。

|165組の平均（ms）|一面|左右の合計|
|---|---:|---:|
|描画|9.933918|6.837607|
|dirty計算|2.956178|3.927190|
|消去|0.977020|2.984176|
|背景|0.712409|1.484172|
|SA-1総計|14.579524|15.233144|

描画だけは約31.17%短縮し、136/165組で速い。しかし別jobのdirty・消去・背景を二重に実行するため、総計は約4.48%増える。712 field・507 logic・500表示、表示間隔は1 field=435件/2 field=62件。これは部分画面の再生であり、ゲーム全体の60fps結果ではない。両jobは別時刻のIRQ/PPU競合を含むので、二面統合後の費用とは異なる。

初回試験は起動時の最初のpacketが注入hookより先に取得される位相差をverifierが考慮せず失敗した。推測で入力をずらさず、後続499 packetの全byteから一意に位相1を特定するよう修正してMesenを再実行した。v2は終了コード0で全検査完了。fixture無効の通常道中も130表示/120全画素照合を通した。ROMは基準a9bcd247のままである。

証拠は `drawing_replay_evidence.zip`（11225934B、SHA256=c821d50da594575338295daced011ef2979e2fa270e94f41fe00ab18df87c666）。入力・実画像・metadata・PPU/VRAM・timing・ROM・labels・初回失敗logも含む。集計は `drawing_replay.json`。配布版は変更していない。

```text
python tools/test_sa1_game.py --frames 1000 --presents 500 --timeout 300 --scenario splitfixture_replay_v2_tracepalette --split-fixture-source build/sa1_game/movestress_detinput_captureburst_directleft_currentbase_tracepalette
python tools/test_sa1_game.py --frames 360 --presents 130 --scenario movestress_detinput_splitfixture_defaultsmoke_tracepalette
python tools/report_sa1_split_replay.py
```
