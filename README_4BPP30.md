# MonoSH Super FX2・4bpp/30fps 実験

作業場所は `D:\HomeBrew\MonoSHFX2_4bpp30_20261008`、GitHubのブランチは `experiment/4bpp-30fps-20261008`。元の開発フォルダーとmainは切り替えず、独立したworktreeで開発する。60fps側の地平線、山裾、空、ボス、自弾、奥行き拡縮の修正を引き継ぐ。mainの2bppタイル色属性のCPU処理は、この4bpp描画経路では実行しない。

## 遊ぶ

`play_4bpp30.cmd` を実行する。白黒素材の比較版は `play_4bpp30.cmd --mono`。

- カラーROM: `releases/MonoSHFX2_4bpp30_color.sfc`
- 白黒素材を4bpp化したROM: `releases/MonoSHFX2_4bpp30_mono.sfc`
- エディタ: `edit_4bpp30.cmd`
- 操作: 矢印で移動、Xで連射、Zで単発、Enterでポーズ。

ROMはMesenで直接開ける。ランチャーはこのworktreeの専用Mesenコピーを使い、GSU 100%、NTSCで起動する。通常のMesen設定は専用コピーに分けて保持する。実機での検証は未実施。

エディタはVS Codeを新しいウィンドウで開く。F5でこのworktreeのカラー4bpp版をビルドし、生成直後のROMをMesenで起動する。Ctrl+Shift+Bはカラー4bpp版のビルド。配布用`releases/`の検証済みROMは、開発中のビルドでは置き換えない。VS Codeがない場合は説明書をメモ帳で開く。

## 描画と転送

内部画像は256×192、表示は既存と同じ256×180。4bpp画像は24KiB。PPUのMode1でBG1を4bpp画像、BG3を既存の地面に使う。自機、自弾、敵、物体、二層遠景はGSUで合成する。地面と空のHDMAは維持する。

VRAMの画像面は`0000..5FFF`と`6000..BFFF`の二つ。`C000..C7FF`が画像マップ、`D000..EFFF`が地面CHR、`F000..FFFF`が地面マップ。VRAMを上書きしている途中の面は表示せず、二つのフィールドの転送が終わってからBG1のCHR面を切り替える。

画像を64pxの四つの縦帯に分け、一方のフィールドで左から第1・第3帯、次で第2・第4帯を描く。ゲーム計算と入力は各フィールドに1回、画像更新は2フィールドに1回。NTSCの目標値は約30.05fpsであり、30.000fps固定ではない。負荷で締切を超えれば次の非表示区間まで待つため、その場面では描画とゲーム進行に遅延が出る。

初期の固定24KiB転送から、列ごとの必要なタイル範囲だけを送る方式へ変更した。転送先VRAM面に残る旧画像の範囲と、現在の画像の範囲の和集合をGSUで計算する。消去すべき旧画像も転送対象に含め、残像を防ぐ。DMAは既存の非表示区間（走査線203以降と、次フィールドの22まで）に収める。転送バイト数と記述子数に応じて開始可能な最終時刻を計算する。

ボス・爆発・ボス弾の7原画は、実際に使う幅・高さに合わせた水平縮小行をROMへ事前生成する。元と同じQ8.8のサンプリング、座標、クリップ、前後関係を使う。元幅・高さが事前計算の対象外なら汎用経路へ戻し、整数刻みの水平参照は短い専用loopで描く。爆発の高さ計算はSNESの乗算器で行い、元の整数式との一致をエミュレータ内で検査する。

拡縮準備では描画kernelの命令cacheを入れ直さず、連続するボス部品で再利用する。転送区間plannerの16列loop、背景二層の境界計算・画素loopもcacheへ置く。2bpp経路のCACHE命令は維持する。

特に面積の大きいボス胴・顔は、事前生成する縮小行を1画素1byteで配置し、描画中の4bit展開を省く。他の爆発・ボス弾は2画素1byteのまま保持し、2MiBのROM内に収める。
通常向きの胴・顔は描画経路を先に選び、使用しない水平UV計算も省く。寸法が対象外なら元のUV計算と汎用描画へ戻す。

## カラー素材

自機を採取したものと同じ `スペースハリアー録画１.mp4` を使用する。画面部分960×672を左上`(480,204)`から取り出し、最近傍で320×224に戻して切り出す。採取時刻、矩形、透過処理、元動画のSHA256は `game/v001/assets/color4/source.json`、元画像と切り抜きの一覧は同フォルダーの `captures.png` に保存する。

敵、弾、植物、岩、ボス、爆発は、元の白黒原画の透過輪郭と黒い模様を維持し、白い画素へ録画由来の色を載せる。録画の別姿勢を拡縮して形ごと置換しない。切り出しの欠損部分は対象の基本色を使い、元原画の画素を削らない。色は従来の二値化と通常のグレースケール二値化で白へ戻る明るさへ調整する。

対象35素材はPNGとROM内の画素の両方で、透過・白黒が元原画に完全一致することを `python -X utf8 tools/verify_4bpp_shapes.py` で検査する。[原画・カラー・白黒復元の比較](game/v001/results/legacy_shapes_20261008/comparison.png)と検証値を保存する。既存60fps版の取り込み済み自機8姿勢と自弾はその画像を使う。録画にない転倒9姿勢は元原画の輪郭・白黒を保った派生着色。影とSTAGE表示も元原画を維持する。

4bppは透明色を含む16色のインデックス画像であり、16bppのフルカラーではない。この実験の合成画像は共有15色＋透明色へ減色する。空と地面は別のRGB5 HDMAなので、画面全体の色数は16色に限定されない。RGBA原画は残すが、原動画の全色を無損失で再現する実装ではない。

## 再現

cc65、Python（Pillow、NumPy）、ffmpeg、Mesenが必要。既存と同じ `D:\HomeBrew\CC65\bin`、`D:\HomeBrew\Mesen\Mesen.exe` を利用する。Mesenの場所は `MONOSH_FX2_MESEN` でも指定できる。

```powershell
python -X utf8 tools/build_4bpp.py --color
python -X utf8 tools/test_4bpp.py --scenario controls --frames 2400
python -X utf8 tools/test_4bpp.py --scenario boss --frames 2600
python -X utf8 tools/verify_4bpp.py controls boss
python -X utf8 tools/archive_4bpp.py color controls boss
```

白黒素材のビルドは `--color` を外す。通常プレイの長時間試験は `--scenario play --frames 18000`。元動画から素材を再採取する場合は `python -X utf8 tools/import_4bpp_recording.py --video <動画のパス>`。

独立したPython合成器で全49,152画素を再計算し、GSUの4面データと表示中VRAMの24KiBを照合する。各半分のDMAが非表示区間内に完了することも検査する。入力はMesenの`inputPolled`へ渡し、controlsでは移動量と連射、pauseでは論理時間の停止・再開をassertする。全44素材×四反転×五寸法・clip条件は`--scenario assets --frames 1784`、24KiB全転送へのfallbackは`--scenario full --frames 120`で検証する。計測・画面・標本は `game/v001/results/four_bpp_20261008/`、ROMのSHA256と要約は `releases/4bpp30_*.json` に保存する。

次回以降のmainの取り込みは、変更をcommitしたこのworktreeで以下を実行する。mainから実験ブランチへの一方向のmerge、ビルド、検証、ROM保存、実験ブランチへのpushを行う。競合や検証失敗時は停止する。

```powershell
powershell -ExecutionPolicy Bypass -File tools/sync_4bpp_upstream.ps1
```

測定結果と達成範囲は `game/v001/RESULTS_4BPP30_20261008.md` に記載する。
