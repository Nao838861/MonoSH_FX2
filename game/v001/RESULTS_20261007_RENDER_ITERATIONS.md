# MonoSH FX2：反復最適化と60Hz提示

2026年10月7日。横縮小済みpacked行、512byteキャッシュ配置、CPUのOBJ準備、DMA区間表の取得を順に改善した。表示256×180、内部FB256×192・2bpp、ゲームロジック、原画、カラーOBJ、地面と空の配色は維持する。Super FX2のクロックを上げる変更はない。

**通常入力18,000field（約5分）では、道中・ボス戦・撃破後とも提示遅延0回、60.10fpsを達成した。** Mesen 2.1.1、GSU速度100%、NTSC、追加scanlineなし。起動後17,977画像を記録し、ゲームの死亡・復帰・ボス出現・撃破・次周を含む。公開ROMは [MonoSHFX2_v001.sfc](../../releases/MonoSHFX2_v001.sfc)。

## 通常プレイの結果

|区分|変更前の遅延画像 / 提示間隔|変更前平均fps|最終版の遅延画像 / 提示間隔|最終版平均fps|
|---|---:|---:|---:|---:|
|道中|65 / 15,146（0.429%）|59.84|0 / 15,627|60.10|
|ボス戦|416 / 1,803（23.073%）|48.83|0 / 1,803|60.10|
|撃破後|0 / 537|60.10|0 / 537|60.10|

最終版のGSU最大は道中12.846ms、ボス12.938ms。CPU最大は道中14.803ms、ボス13.490ms。初期に想定したCPU約4msとは異なり、ゲーム更新だけでなく描画リスト・OBJ・地面HDMA表の準備も含む。CPUとGSUは並行実行し、前画像の転送終了位置、次の準備、転送開始の締切も含めて毎field提示を確認した。

道中はGSU開始時boss=0、戦闘はboss=1/2、撃破後はboss=3。区分が切り替わる境界は比較から外す。CPU/GSUが速くなり同じ5分で進むゲーム内時間が変わるため、前後の道中標本数は一致しない。固定標本の性能比較は次節で別に行う。[自然入力の全計測と集計](results/render_iterations_20261007/boss_profile_final/analysis.json)に、死亡中・生存中と60field窓も保存した。

追加で、ボスを攻撃せず長く残す入力を18,000field計測した。道中5,065・ボス12,911の提示間隔はすべて1field、遅延0回。戦闘区間のGSU最大11.459ms、CPU最大10.769ms。通常入力と合わせた約10分、35,955画像を記録し、重いボス姿勢が繰り返される場合も検査した。[長期ボスの全計測](results/render_iterations_20261007/boss_profile_finalnofire/analysis.json)。

## 同じ標本で繰り返した比較

前回の122標本を同じ順で各3回描き、後半2回の中央値を比較した。実ゲーム107場面、従来の最悪ボス、64体の人工負荷2種、境界12種。計測値はGSUの起動からSTOPまでで、部分クリア・準備・描画・DMA区間表作成を含む。CPU packet時間は別に測り、並行して動くためGSU時間とは足さない。

|試行|固定ボスGSU ms|64体画面内GSU ms|実ゲーム107標本のCPU packet平均 ms|判断|
|---|---:|---:|---:|---|
|開始時 `opt_base`|17.352|11.767|4.148|今回の基準|
|CPU制御値の書込み削減 `opt_cpu`|17.352|11.767|4.085|採用|
|行ごとの透明余白表 `opt_spans`|16.941|12.378|4.085|表参照の費用が大きく不採用|
|横縮小済みpacked行 `opt_scaled`|12.280|15.486|4.085|ボスは改善、cache配置の修正が必要|
|共通cacheへ描画経路を配置 `opt_shared`|11.656|11.313|4.085|採用|
|深度bucket sort `opt_bucket`|11.656|11.313|4.406|人工64体では速いが実ゲーム平均は悪化、不採用|
|OBJ専用準備とdirect page `opt_obj`|11.656|11.313|3.397|採用。OBJ表のbank配置を後で修正|
|任意left clipをpacked行へ `opt_clip`|12.041|12.282|3.397|clipには効くが共通cacheを圧迫|
|skip/flipなしのUV準備を短縮 `opt_uv`|11.919|11.590|3.397|採用。端数処理もcache内へ戻した|
|端数をcache内へ戻しDMA準備もcache化 `final`|**11.459**|11.600|**3.397**|採用、固定ボス約34.0%短縮|

各試行の [比較値とROMハッシュ](results/render_iterations_20261007/iterations.json)、固定ROMの圧縮コピー・labels・入力・実行ログを保存した。これらの途中版はFBの全画素検証を通した測定用ROMであり、公開版ではない。特に`opt_obj`〜`opt_uv`のOBJ位置表のbank誤配置は公開前に修正し、最終版で独立OAM・PPU照合を行った。

最終版は元の122標本に、6素材×5幅×4反転の120標本を追加した。各追加標本はleft skip=1/2/3、右端、上端、下端を含む6体構成。幅7/8/9、対応表の最大幅と最大幅+1を検査する。計242標本・1,194完成画像のFB49,152画素とOBJが独立参照に一致し、最初の122標本のFBハッシュも変更前と一致した。

## 横方向だけ先に縮小する

元のQ8.8と同じ `sourceX = (x * floor(sourceWidth * 256 / width)) >> 8` で、4画素/byteの行をビルド時に作る。草2種、木、ボス胴・顔・弾の6素材、計608幅を収録。縦は元のV/DVで原画行を選ぶため、高さごとの画像群を持つ必要がない。左右反転・未収録幅は従来の任意倍率経路へ戻る。幅7以下も準備費用を避けて従来経路を使う。

実行時は1byteから4画素を取り出し、COLOR/PLOTへ渡す。元の「毎画素Uを進めて原画アドレスを作る」処理を減らす。左clipが4画素境界からずれた場合は先頭1〜3画素を処理してから4画素ループへ入る。最後の0〜3画素とY反転も元と同じ画素を描く。色0の透明合成と奥から手前の順序を保つ。

追加画像646,848bytesは、既存の各原画bankの行領域の後にある703,744bytesの空白へ配置した。2MiB ROMの容量と元のraw/packed/反転領域は維持し、bank5Fの64KiBを索引に使用する。[独立画像検証](results/render_iterations_20261007/scaled_assets_verified.json)では原画249,538画素と縮小済み2,514,624画素、領域の非重複、実ROMとの一致を確認した。

共通準備・scaled/generic・先頭端数のコードは485bytesに収めた。clip状態が変わってもCBRは変わらない。整数比の別経路から共通入口へ戻る場合は従来通りcacheを設定する。全spriteを描いた後、DMA区間表の生成だけ別cacheへ移す。ここをROM直読みから変えた最後の改善が、道中に残っていた1回の締切超過に効いた。
DMA区間生成のコードは201bytesで、毎画像最後に1回だけcacheを切り替える。

## 最終版の回帰検証

|試験|結果|
|---|---|
|objects360|17pose・四反転・16弾サイズ・最大12 OBJ一致。実PPU66画面15,313 OBJ画素一致|
|display720|三カメラの地面・遠景・FB・OBJを合成した最終RGBが一致|
|controls720・pause360|通常操作、単発射撃、Startでのポーズと解除が通過|
|held1800|開始直後から左上＋Yを押しっぱなし。誤ポーズ・論理停止なし|
|boss2600・stumble800|ボス撃破・次周、転倒40更新と復帰が通過|
|packed360・stress360|従来の整数比・反転・端数と大型20体のRAM/VRAM保護が通過|
|全12KiB＋最大12 OBJ、360field|最遅20行完了、22行OBJ準備・23行表示に間に合う|
|縮小済み行を無効にした122標本|745画像のFB/OBJ一致。汎用fallbackを維持|

公開版の検証は通常・長期ボス36,000field、回帰8,080field、標本1,552fieldの合計45,632field。全転送360fieldとfallback832fieldは別構成。全転送の [計測結果](results/render_iterations_20261007/full_transfer_objects/summary.json) と [最終PPU表示](results/render_iterations_20261007/display00478.png) も保存した。全転送専用ROMのSHA-256は `08fde4ab9fd8387f9de7ba246a602d3f940a3af1813a1b56b53b68ab4cc24b76`。検証後に既定ROMを再ビルドし、公開ROMとハッシュ一致を確認した。

## CPUとDMA

CPUは従来の安定insertion sortを保つ。packetの作業領域をdirect pageへ移し、重複していた制御値の書込みを省いた。32×48のプレイヤー全体が画面内なら、6個のOBJの座標と属性をまとめて作る。端では従来のclip・9bit X・枠数検査を使う。CHRは起動時だけ転送し、毎画像のOAMは68bytesのまま。

GSUは前回と今回の32列の範囲を結び、残像を消す部分DMA区間を生成する。STOP後にCPUがcart RAMの最大128bytesの区間表をWRAM portへのDMAで取得する。描画中に共有RAMへCPUがアクセスする変更はない。VRAMへのFB転送と区間表の読出しは別の処理である。

`FB bytes + 区間数 × 128 <= 9984` の画像だけ、203〜220行で転送開始を許可する。128はDMA設定費用の保守的なbyte換算。9KiBの従来基準から9.75KiBへ広げ、最終試験で全転送の終了位置を検査した。大きな転送は203行の枠を使い、間に合わなければ次fieldを待つ。全12KiBの場合も翌20行までに完了させ、22行のOBJ準備、23〜202行の表示を守る。

## 再実行

プロジェクトのルートで実行する。最初の標本比較に元のNES/MSXプロジェクトは不要。

```powershell
python -X utf8 tools/benchmark_render.py --name final --edges
python -X utf8 tools/verify_scaled_assets.py
python -X utf8 tools/profile_boss.py --frames 18000 --timeout 600 --output boss_profile_final
python -X utf8 tools/analyze_render_profile.py build/game_v001/boss_profile_final --output build/game_v001/road_final.json
```

`--no-scaled-rows`、`--no-scaled-clip`、`--no-fast-uv`、`--no-fast-obj`、`--no-descriptor-dma`、`--legacy-dma-admission`で効果を分離できる。`--bucket-sort`は比較用で既定は無効。途中版の数値を現行コードのフラグだけで完全再現できるとは扱わず、保存済みROMと生成Luaが当時の測定の正本となる。

一式の再検証は `python -X utf8 tools/verify_render_release.py`。CPUの安定sortはゲーム内最大規模を優先したため、人工64体のpacket作成は約42msかかり60Hz対象ではない。`stress`の大型物20体も回帰・RAM/VRAM保護の試験で、60fps達成の根拠には使わない。

転送完了時の簡易fieldカウンタは、DMAが225行の前後に動くだけでも0/2の間隔を記録することがある。最終の自然入力集計はDMA開始のPPU位置から物理fieldを復元し、summaryの旧完了カウンタは`legacyCompletionIntervals`へ分けた。実際の提示遅延と混同しない。

ROM SHA-256：`4c9308d79d3cdf1108267a9678289721e081912ffc3436b98758a32e4eec418b`。

自己評価：描画順、操作、敵数やボス節数、縮小の段階、画像の横幅を削らずに速度を上げた。費用対効果が逆転した透明余白表とbucket sortは採用しなかった。任意のプレイや64体の人工最悪入力、実機の全条件で60fpsを保証する測定ではない。表示192行・音・実機確認は引き続き残る。
