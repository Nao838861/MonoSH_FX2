# 可視域を左右128pxずつの二面へ分ける容量・命令量の算定

未実装・速度未測定。60fps達成結果ではない。既存の広幅バッファ試験は512pxから中央256pxをコピーし直す費用で遅くなった。今回の候補は通常の256px幅バッファを二つ使い、各面の中央128pxだけを文字変換DMAから直接読む。左右64pxずつの余白があるため、大きな爆発も画面端の退避なしで描ける場合が増える。原画や寸法を減らす案ではない。

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

1. 小さい独立ROMで、同じbankの0400/8400の二面から中央16tileずつをCC1で直接読む実DMAを検証する。512px幅の未対応設定やCPUの中央コピーに依存しない。
2. 実ゲームpacketを二面へ再生して、元のnative行・palette・全画素を確認し、描画の重複と端処理減少の実費を測る。軽い二面probeを全体60fpsと扱わない。
3. 統合する場合は可視dirty範囲の消去・転送sourceを左右へ写像する。余白のpixelは表示しないが、境界wordのread-modify-writeと既存の端保護は検査する。wide-clearをそのまま使うと余白まで余分に消すので注意する。
4. raw七画像から三画像への変更による待ち行列の減少、追加descriptor、消去設定費も含め、同じ道中・ボスの長区間で判定する。

算定コード `tools/analyze_sa1_split_viewport.py` のnativeBytesは速度ではない。圧縮弾worker、分岐・dispatch、clear/dirty、CC1/PPU、待ち行列の費用は含まない。今回の入力に圧縮弾素材6/7/8/37は0件であり、武器全種を網羅したとは主張しない。解析自体はROMや配布版を変更しない。

```text
python tools/analyze_sa1_split_viewport.py build/sa1_game/movestress_detinput_captureburst_directleft_currentbase_tracepalette build/sa1_game/flame_currentbase_build/MonoSHSA1_4bpp_game.sfc --output game/sa1/v001/results/20261013_split_viewport/analysis.json
```
