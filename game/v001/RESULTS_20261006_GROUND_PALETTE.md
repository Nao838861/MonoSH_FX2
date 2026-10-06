# MonoSH FX2 v001：地面の直線パース・配色と自機OBJ化

2026年10月6日。地面の境界を同一消失点からの直線へ変更し、自機・自弾・反射弾をSNESのOBJへ移した。その後の指摘に合わせて、地面を指定RGBの四色へ直し、暗い二色と明るい二色がそれぞれ同じ縦列を保つ配置に修正した。**表示256×180、内部FB256×192。配色前版の通常進行は平均57.05fps、序盤59.35fps。配色修正で処理・転送量は増えていない。全場面60fps・192行表示は未達。** [ROM](../../releases/MonoSHFX2_v001.sfc)、[起動・操作](README.md)。

依頼原文と三巡の設計検討は [DESIGN_LOG.md](DESIGN_LOG.md)。配色前版の全試験は [RESULTS_20261006_GROUND_OBJ.md](RESULTS_20261006_GROUND_OBJ.md)、55.11fps版は [RESULTS_20261005.md](RESULTS_20261005.md)、初版は [RESULTS_INITIAL.md](RESULTS_INITIAL.md) に保存した。

## 地面のパースと色

旧方式は木の倍率・距離表から作った整数格子幅を地面にも使い、画面Yに対する幅が非線形になっていた。地上物の接地・投影は原本のまま保存し、地面のBGだけ別の直線式で作る。

地面atlasの深さd=0〜80に対し、境界を `256 + k*d*51/80` の位置で整数化する。幅を先に整数化してk倍する方式も避けた。65段階のカメラ位置について、地平線 `104+offset` と下端204の間をatlasへ線形に対応させる。横移動も `128+phase*d*51/(64*80)` を行ごとにHDMAで設定する。カメラが動いても一つの消失点へ集まる。

通常BGは81本のsource行から選ぶため、実画面には行選択と整数画素による階段が残る。65カメラ×5横位相の158,269境界を独立に調べ、理想直線との差は最大3.486px、解析上の上限4px未満だった。[投影検査](results/ground_projection.json)。ピクセル単位で完全な直線にするには地面も毎行別画像にする等の追加設計が必要。

|暗い順|指定RGB|実際の表示RGB（最も近いRGB5）|SNES RGB5|
|---|---|---|---|
|1|114,193,112|115,189,115（`#73BD73`）|14,23,14|
|2|129,208,127|132,206,123（`#84CE7B`）|16,25,15|
|3|145,223,145|148,222,148（`#94DE94`）|18,27,18|
|4|160,241,162|156,239,165（`#9CEFA5`）|19,29,20|

SNESの5bit成分では指定8bit RGBと完全一致できないため、各成分の展開値との差が最小になる色を選ぶ。空は従来の紫 `#C673FF`（RGB5 24,14,31）。

奥行き方向に `1 4` → `2 3` → `1 4` と並ぶ。片方の縦列は暗い1/2、もう片方は明るい4/3で、最暗1と最明4が横に隣接する。以前は同じ列に暗色と明色を交互に配置していたため、違和感の原因になっていた。14相の地面アニメーションと行別パースを維持する。BG2はFBの一対一表示、BG3だけH/Vを行別投影、BG4は独立した遠景H/V。地上物の0〜3pxの沈み込み・当たり判定も保存する。

[修正後・低い視点](results/palette_20261006/display/display00238.png)、[中間](results/palette_20261006/display/display00478.png)、[高い視点](results/palette_20261006/display/display00718.png)。三カメラそれぞれの最終RGB全61,184画素が、OBJ・BG・CGRAM・HDMAを別実装で合成した結果と一致した。暗い／明るい列の対応と横の色ペアも検査した。全65カメラ×14位相、62,790地面行でもこの配置を確認した。

配色修正版はplay360field・display720fieldを検証し、前版の計測ログ計4,177レコードと全項目一致した。ROMの49,932変更bytesは地面色定数8bytes、色HDMAの色値、checksumだけで、CPU/GSUコード・画像・投影・HDMA構造は同一だった。[今回の検査](results/palette_20261006/summary.json)。以下の長時間・C/native・全転送の数値は配色前版の実測として残す。

## 自機・自弾をハードウェアOBJへ

自機32×48を16×16の6 OBJへ分割し、17poseを静的4bpp CHRへ変換した。自弾・反射弾は1〜16pxの16サイズを元のQ8.8最近傍と同じ画素で事前生成し、1発1 OBJで表示する。これらはGSUの拡縮packetから除くが、ゲーム側の描画矩形と当たり判定は保存する。元の固定前景グループをOBJ priority 3へ対応させ、自機と弾の前後もOAM順で保存する。

CHRは起動時だけ転送し、有効データ15,104bytesをVRAM C000〜FFFFへ置く。遠景mapはC000からB000へ移した。通常は自機6＋自弾3＋反射弾3の最大12 OBJで、用意する16枠を超えない。16×16なので全12個が同じ行に重なっても24個の8px tile。PPUの行制限は32 OBJ／34 tileで、全試験のrange/time overは0だった。[PPU OBJ一次実装](https://github.com/bsnes-emu/bsnes/blob/master/bsnes/sfc/ppu/object.cpp)。

CPUは次の更新前にOAMを固定し、対応するFXのFBと同じ黒帯で提示する。毎画像はlow OAM 64bytes＋high OAM 4bytesだけをDMAする。左右・上下反転、四辺clip、死亡pose、点滅も保持する。OBJのYはPPUの1行遅れと固定BG2 Vを補正し、以前のFX座標へ一致させた。

黒帯明けの最初の行にOBJが欠ける問題を最終PPU検査で発見した。22行目をforced blank解除・輝度0にして、OBJ評価とCHR fetchを先行させる。23〜202行の180行だけが見え、準備行は黒いまま。起動時にHDMAを画面途中から開始すると空のCGRAMが壊れる問題も、VBlankを待って有効化する形に直した。

全17pose・四反転・16弾サイズ・画面端・点滅の85場面をOAM/CHRから復号し、元のdraw矩形の独立描画と全画素を照合した。さらに66枚の実PPU画面、15,649 OBJ画素が一致し、CHR第2表と全反転も確認した。[OBJ検査](results/objects/objects_ppu.json)。RGB取得ではホスト負荷によるエミュレータのframe skipを無効化し、画面とOAMの世代を揃える。

## DMAは間に合うか

内部FBは256×192・2bppで12,288bytes。既定は前後の描画範囲の和集合を32列のtile区間にまとめて部分転送する。前回だけ描いた部分の消去も必ず送る。範囲が大きければ全12KiB一本へ戻す。64bytes以内の隙間は統合し、bytes＋区間数×64が12,000以上なら全転送へ切り替える。

大きい転送は203行目から始まる黒帯を待つ。bytes＋区間数×128が9,216以下だけ220行目まで開始を許す。STOP後にGSU RAMからVRAMへDMAし、OAMはWRAMから先に送る。OAMの追加は平均0.071ms、最大0.072ms。毎回4bpp CHRを送る必要はない。

全転送版で最大12 OBJと毎回12,288bytesを同時に送る360field試験も通した。FBのDMA最大4.835ms、OAM最大0.072ms、最遅完了はPPU 20行目。22行目のOBJ準備より前に終わり、23行目の表示へ間に合う。全FB/VRAM、RAM guard、OAM、最終OBJ画素が一致した。[全転送の実測](results/full_transfer_objects/summary.json)。これは180行表示のMesen実測で、192行へ戻せる余裕の証明ではない。

## CPUとFX2、実測性能

CPUが65816でゲーム更新・投影・判定・OBJ準備・描画順の安定ソート・HDMA表を準備する。GSUは固定した10byte/体のリストからUV・clip・flipを求め、前回のtile消去、Q8.8拡縮・透明合成、前後範囲のDMA区間生成を行う。GSU動作中のCPUはWRAMのコード・定数・作業領域だけで次世代を作る。ROM／GSU RAMをCPUが参照するのはSTOP後。地面表は表示中・描画中・準備中の3組で分ける。

|通常進行18,000field・約299.5秒|結果|
|---|---:|
|新しい画像／平均fps（起動を含む）|17,086回／57.05fps|
|表示間隔1field／2field／3field以上|16,193／892／0|
|CPU全体：更新・OBJ・packet・地面表|平均8.85ms、最大14.84ms|
|GSU：消去・UV/clip・描画・範囲生成|平均7.32ms、最大19.13ms|
|CPU/GSU合流|平均9.77ms、95%点15.11ms|
|FB DMA／OAM DMA|平均1.45ms／0.071ms|
|FB転送量|平均2,352bytes、最小128、最大12,288|
|序盤profile 2,400field|59.35fps、1field間隔2,362、2field間隔7|

前版の55.11fpsから通常平均は57.05fpsへ改善した。GSU平均8.43msから7.32msへ減り、FB平均2,439bytesから2,352bytesへ減った。一方、OBJ準備と直線地面の増えたH区間でCPU平均は7.28msから8.85msへ増えた。OAMのDMA量よりCPUの準備費用が次の課題。速度により同じfield内のゲーム進行が変わるため、同一場面の厳密な速度比とは扱わない。

処理落ち時は次の表示枠を待ち、ゲーム時間も遅くなる。CPUが常に4msで終わる構成ではない。GSUの7高速経路と汎用Q8.8描画は維持した。人工の木20本は約59ms・約14fpsで、帯域・clip破損検査用。通常のゲーム性能とは分ける。

## 検証・自己評価と残る範囲

11シナリオ：play360、controls720、pause360、stumble800、boss2,600、stress360、packed360、objects360、display720、long18,000、profile2,400field。FB/VRAMとguardを3,447回照合、181場面のFX/OBJを別実装で再描画した。通常入力だけの長時間試験で死亡31回・復帰31回、EM0全経路・EM1全状態、自然なボス撃破・次周を確認した。三カメラの最終RGB、動的OBJ、全転送の追加試験も通した。

同一入力・同一論理更新でC参照版／65816版を比較し、通常5,315更新・ボス2,624更新の全状態・有効なdraw矩形が全byte一致した。[通常比較](results/equivalence/summary.json)、[ボス比較](results/equivalence_boss/summary.json)。NES実機との全frame一致を意味しない。固定原本34ファイルのhashも一致する。

自己評価：地面の曲線化は解消し、指定の緑四色・紫の空、OBJとFXの位置・前後関係を最終画素まで確認した。DMAは最大量でも成立した。CPU費用は増えたが通常の平均fpsは改善した。残るのは81行の地面量子化、全場面60fps、192行表示、音、実機確認。次はカメラ／横位相が不変なHDMA表の再利用とOBJ準備の短縮を計測して進める。

配色修正版ROM SHA256: `1dfedc985036b201e5f32cef9a771389027c94fc21e550f56d5b0d9fc7c37bdc`、2MiB。[manifest](../../releases/v001.json)。長時間・全転送・C/nativeの基準ROMは `7a0a0c5dd7cb594017fbc87cac4e63644d69d0a19178cd4409abad3c93270b9d`。測定はMesen 2.1.1、NTSC、GSU速度100%、追加走査線0。保存済みログ・状態・draw・packet・FB・OAM・VRAM/CGRAM・RGB/PNGは [results/](results/)。全試験の再実行はプロジェクトルートで：

```powershell
python -X utf8 tools/verify_game.py --equivalence
python -X utf8 tools/verify_full_transfer_objects.py
```
