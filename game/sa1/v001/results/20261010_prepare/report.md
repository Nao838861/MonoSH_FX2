# DMA準備と描画前処理の改善

元の素材・縮小寸法・描画順を維持し、SA-1とS-CPUを通常クロックで測った。先に描いた7枚を順番に表示する構成で、入力から表示まで約7フレームの遅延がある。転送を完了していない絵を表示せず、世代の省略も禁止している。

## 改善した箇所

- CPUの近景OAMと地面の準備をSA-1描画待ちの前へ移した。
- V-IRQを200行へ移し、使用権と設定を先に準備する。実際のforced blankとPPU転送は203行以降に限定する。
- 同じpriorityの順序を保つ連結リストによるソートを採用した。radixとbitsetの試験は遅くなったため既定にしない。
- 幅32byte以下の端退避を内部RAMの専用コードにした。SA-1の消去ループも内部RAMへ戻した。
- 地面のHDMA表生成を65高さの専用コードにした。128位相との全8,320組を元の表と比較した。
- 空の帯ではDMA使用権を解放しない。獲得せずに解放すると、S-CPUへ渡したgrantを消す可能性があった。
- PPU転送を24記述子ずつ展開し、記述子ごとのループ費用を減らした。転送量の見積もりはrefreshを含めて8.3125 master ticks/byteとする。
- 8pxに整列済みの占有範囲は汎用矩形で再度丸めず、タイル範囲へ直接反映する。
- 幅104byte以上の旧画像の帯を消すときは、元々零である余白も含む1KiBを1回のDMAで消す。狭い帯は8行分の部分消去を維持する。零の転送元03:F000は生成ROMから検査した。

## 計測

`index.json`と`measurements.zip`に16回の途中比較を保存した。600fieldのボス移動・射撃試験は、初期の468枚から、転送設定展開後508枚、占有範囲の改善後509枚へ改善した。最初の90fieldは表示開始前であり、この枚数を600で割って定常fpsとはしない。509枚版にも表示間隔2fieldが1回残り、60fps成功とは扱わない。

広い帯の一括消去を加えたROM SHA-256 `b96563957e06e46e7fdb2910a12bd2a94a234900fb870e19d81b7343e53ac128` は、ボス移動・射撃1,800fieldで1,710枚を順番に表示し、評価対象1,707間隔が全て1field、末尾待ちは1fieldだった。SA-1単発の最大処理時間は19.73435msであり、7枚の保持によって平準化している。

146画面について、独立した元画像の合成、SA-1出力、変換後VRAM、近景OBJ、自機OAM、CGRAM、地面HDMA表を照合した。CGRAMは各fieldでも監視した。表示切り替えの最遅位置は21行で、実際のHDMAによる不正なunblankも検査する。全5,992個の整列境界表を最終ROMから読み戻して一致確認した。

長い道中では870枚後に描画が停止した。停止時のSA-1 PC=00:839Cは`unsupported_hflip`で、通常敵弾のflags=$22による上下反転が未対応だった。これはボス試験の合格とは別の不具合で、現段階ではゲーム全体の60fps成功ではない。

IRQ専用の一時変数を使う修正も入れたが、停止箇所は同じだった。現在は4種類・3色位相の原寸敵弾を18,816byteの4bppで保持し、反転した弾だけQ8.8の元のsamplingで描く経路を追加した。反転時の占有範囲も反映する。実ゲームと四辺クリップを含む独立fixtureで検証を継続中。ここは中間記録であり、試遊ROMを更新した最終報告とは区別する。

## 性能根拠から除外した試験

- `earlyrequest`: 195行で使用権を要求する旧案は53行まで待ち、非表示期間を越えたため失敗。現在は200行の一段階要求。
- `preconfigure`: blank開始helperより前のcallbackが202行を検出した旧検査。終了側callbackをhelper後へ移して再測定した。
- `oldmask`: exportがないラベルへのcallback登録で起動時に止まった。性能値はない。
- `bitset`: ROM表のbank指定漏れで並べ替え順が壊れた初期案。修正版は画素一致したが遅く、不採用。
- 前回の`neartable_safe`長期ボス試験はCGRAM不一致で失敗。今回の毎fieldパレット検査を通った結果と混同しない。

## 再現

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct --pipeline-irq --pipeline-depth 8 --deep-bw --prefill-pipeline --prefill-count 7 --redraw-all --merge-dma --large-edge-cache --triple-bw --fast-dma --linear-shape --cpu-code-copy --cpu-edge-copy --packet-shapes --native-background --native-near --row-dirty --row-dirty-aligned --wait-slots --occupancy --accurate-dma-budget --transfer-mask --front-mask --visible-mask --stack-band --early-request --list-sort --small-edge-jit --compiled-ground --unroll-ppu-dma --wide-clear
python tools/test_sa1_game.py --frames 1800 --scenario bossmovestress_tracepalette_wideclear
python tools/verify_sa1_aligned_bounds.py
```
