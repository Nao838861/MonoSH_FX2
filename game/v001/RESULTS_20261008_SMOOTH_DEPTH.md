# 奥行きに沿った滑らかな拡縮

2026年10月8日。元の縮小段階に由来する長い寸法の停滞と、開いた敵EM1の急な寸法切替を修正した。表示256×180、内部FB256×192・2bpp、60Hzのロジック更新を維持する。[公開ROM](../../releases/MonoSHFX2_v001.sfc)。更新後はROMを開き直してリセットする。旧ステートには旧WRAMコードと寸法表も保存されている。

## 変更した寸法

地形・通常敵・敵弾・ボスの14表を、奥行きZ=0..110に沿った単調3次Hermite曲線から生成する。近端・遠端と中景の形を元データから取り、最後に整数画素へ丸める。計算はビルド時だけで、ゲーム中は以前と同じ幅・高さの表引き。位置投影、接地Y、移動速度、描画順は維持する。

|対象|同じ幅・高さが連続する最長の奥行き区間：旧→新|寸法の種類：旧→新|
|---|---:|---:|
|木|9→6|70→74|
|通常敵EM0|12→5|64→78|
|ボス胴|15→4|61→81|
|ボス顔|7→2|85→96|

これは奥行きの段階数であり、実プレイ中の停止フレーム数ではない。Zの進行速度により見える時間は変わる。整数画素への丸め、小さい敵や遠端の最小寸法による同値は残る。閉じたEM1には近距離で最大28×30を保つ区間もあり、最長同サイズは42→39段階に留まる。共通の位置投影倍率を変更したわけではなく、全素材の寸法を一つの倍率から求める実装でもない。

開いたEM1は別経路で、従来は5ポーズそれぞれに遠・中・近の3サイズしかなかった。これを5ポーズ×111奥行きに変更した。奥行き1段階で最大20画素変わっていた幅・高さは、各ポーズとも最大1画素の変化になる。近端・遠端の寸法を保ち、旧中サイズをZ66の基準とする。

描画と当たり判定は同じ新寸法を読むため、中間距離の当たり判定矩形も変わる。移動や射撃の更新処理は同じだが、旧版と命中タイミングまで同一とは限らない。14表の寸法差は旧版から最大4画素、旧3段階の開EM1は境界付近で最大16画素の差がある。

木は高さだけを独立に丸めると、地面の投影・接地の丸めと干渉して樹冠が逆戻りした。そのため、地面の伸びが最大のカメラで樹冠位置を補間し、固定した接地Yから高さを戻す。全65カメラ・全Zを調べ、隣接Zでの樹冠逆戻りは38箇所から20箇所、最大量は1画素のまま。完全なサブピクセル拡縮ではない。

## 実装と描画の確認

[smooth_depth.py](../../tools/smooth_depth.py)が固定したupstream原本を読み、ビルド先のCデータへ新寸法を適用する。原本34ファイルのハッシュは変更していない。開EM1の追加表は1,110bytesで、CPUコードと一緒にWRAM7Fへコピーする。GSU稼働中もROMバスを使わず読める。[smooth_depth.s](smooth_depth.s)がC参照経路を、[enemy_render.s](enemy_render.s)と[enemy_collision.s](enemy_collision.s)が実ゲームの経路を担当する。

GSU命令・原画・UV表・ボス3素材だけの横縮小済み画像は旧版とbyte一致。511bytesの共通キャッシュ、クリッピング経路、DMA締切の実装を引き継ぐ。寸法変更によって描画面積や汚れたタイルは変わるため、速度と転送は新ROMで再測定する。

以下の比較は、旧寸法を左、新寸法を右に配置し、同じ新ROMのFX2で実際に描画したFBを独立照合してからGIFにしたもの。画像中のZ110が遠方、Z0が近方。GIFは20ms刻みの比較用プレビューであり、ゲームのフレームレート測定ではない。

- [ボス胴の比較GIF](results/smooth_depth_20261008/tables/depth_13.gif)／[遠〜中距離の比較画像](results/smooth_depth_20261008/tables/boss_body_steps.png)
- [木](results/smooth_depth_20261008/tables/depth_4.gif)／[通常敵EM0](results/smooth_depth_20261008/tables/depth_3.gif)／[開EM1の最大ポーズ](results/smooth_depth_20261008/tables/depth_36.gif)
- [開EM1の旧切替境界付近の比較画像](results/smooth_depth_20261008/tables/em1_steps.png)
- [全19系列×111項目のCSV](results/smooth_depth_20261008/tables/sizes.csv)／[寸法の集計](results/smooth_depth_20261008/tables/tables.json)

## 拡縮単体ROMでの検証

拡縮単体の検証ROMは`887ac0a0401f7523b0e2f506380f19139615e0fa557b8ea2045038d3f2e37c27`。拡縮修正前の基準ROMは`571c1d9fc0d0389aff5f58326388e43297bc3674934b7564bae00f6dd20356c2`。この後、別途反映された遠景修正も統合した。公開する統合ROMの検証は次節へ分ける。

通常のパッド入力だけで18,000field、約299.5秒を走らせた。死亡・復帰、自然なボス到達・撃破・次周を含み、17,977画像を提示した。区分が変わる境界を除いた同一区分内の表示間隔は次の通り。起動時の待ち時間はフレーム落ちとして数えない。

|区分|調べた連続画像間隔|2field以上の遅延|平均fps|GSU最大|CPU最大|
|---|---:|---:|---:|---:|---:|
|道中|15,860|0|60.099|11.591ms|15.187ms|
|ボス|1,570|0|60.099|12.707ms|14.070ms|
|撃破後|537|0|60.099|1.098ms|8.537ms|

最悪の連続60field窓も各区分60画像。CPUとGSUは並行なので、上記の時間は足し算しない。表示間隔はDMA開始の物理fieldから算出し、225行をまたぐ完了callbackの揺れを処理落ちと数えない。実行中の開EM1描画9,594件で、実際の幅・高さが新しいWRAM表と一致することも確認した。[通常プレイの集計](results/smooth_depth_20261008/boss_profile_smoothfinal/analysis.json)。

射撃せずボスを残した9,000field、約149.8秒も道中・ボスとも表示遅延0、60.099fps。ボス区間は3,911の連続間隔を調べた。[継続ボスの集計](results/smooth_depth_20261008/boss_profile_smoothnofire/analysis.json)。

主要6素材と開EM1の5ポーズの全111奥行き、1,221場面・7,404画像を描画し、独立したUV・clip・透明合成の計算と全FB画素が一致した。[再描画の記録](results/smooth_depth_20261008/replay/comparison.json)。C参照版と65816版は、[道中5,587回](results/smooth_depth_20261008/equivalence/summary.json)・[ボス2,749回](results/smooth_depth_20261008/equivalence_boss/summary.json)の論理更新で、全状態ブロックと有効な描画矩形が一致した。これは修正前の寸法との一致試験ではなく、新寸法を使うC版と65816版の比較。

## 遠景修正を含む公開統合版

公開ROMのSHA-256は`0b5e3c57072898c91feeb31721d8a211d4bb59a68c44a78920e907b77db99bfe`。[遠景・空の修正](RESULTS_20261008_SCENERY_FIX.md)を保ったまま拡縮を更新した。

拡縮単体887ac0a0との差分を全2MiBで照合した。CPU命令の変更は背景位置に使う即値2箇所（14→23、87→74）のみ。その他は遠景修正版の色・画像3,119bytesとchecksumだけで、拡縮・当たり判定・入力・DMAの命令、全450個の既存label位置、GSUコード、GSU用原画・縮小画像・UVは同一。したがって、上記の全Z描画とC/nativeの検証は拡縮単体ROMの記録として保ち、統合版で表示・操作・実プレイの速度を改めて検証する。[byte照合の根拠](results/smooth_depth_20261008/integrated/integration.json)。

統合版も通常入力18,000field・17,977画像で、道中15,860・ボス1,570・撃破後537の連続表示間隔すべて1field。全区分60.099fps、表示遅延0、最悪の60field窓も60画像。GSU最大は道中11.591ms、ボス12.707ms、CPU最大は道中15.179ms、ボス14.060ms。[統合版の実測](results/smooth_depth_20261008/integrated/natural/analysis.json)。

統合版の射撃なし9,000field・8,978画像も道中・ボスとも60.099fps、表示遅延0。ボス区間3,911の連続間隔、GSU最大11.794msを確認した。[継続ボスの実測](results/smooth_depth_20261008/integrated/no_fire/analysis.json)。実ゲームが出した開EM1の寸法は通常9,594件・射撃なし3,198件で新表と一致した。

統合版でobjects・packed・controls・pause・display・held・boss・stumble・stress、計8,080fieldを再検証した。自機17ポーズ・四反転・16弾サイズ、最終PPU 66画面・68,057 OBJ画素、三カメラの背景・空色、押しっぱなし、転倒、通常HPのボス撃破・次周が通過。人工的な大木20本のstressは速度保証の対象ではなく、四辺clip・RAM guard・全12KiB転送を確認する試験で、転送は20行目までに終了した。[回帰試験の集計](results/smooth_depth_20261008/integrated/tests.json)。

## 再現手順

プロジェクトのルートで実行する。計測に使うMesenは通常GSUクロック100%、NTSC、追加走査線0。実機と任意の入力での全条件保証は未確認。

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/archive_smooth_integration.py --verify-only
python -X utf8 tools/verify_depth_sizes.py --replay
python -X utf8 tools/verify_scaled_assets.py
python -X utf8 tools/verify_game_equivalence.py --result-root game/v001/results/smooth_depth_local_check
python -X utf8 tools/profile_boss.py --frames 18000 --timeout 900 --output boss_profile_smoothfinal
python -X utf8 tools/analyze_render_profile.py build/game_v001/boss_profile_smoothfinal --output build/game_v001/boss_profile_smoothfinal/analysis.json
python -X utf8 tools/profile_boss.py --frames 9000 --timeout 600 --boss-fire none --output boss_profile_smoothnofire
```

比較用の旧寸法は`build_game.py --legacy-depth-sizes`で生成できる。遠景修正を含む旧寸法版になる。フラグなしで新版へ戻る。
