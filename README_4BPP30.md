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

内部画像は256×192、表示は既存と同じ256×180。4bpp画像は24KiB。PPUのMode1でBG1を4bpp画像、BG3を既存の地面に使う。カラー版の自機は専用パレットのOBJ、自弾、敵、物体、二層遠景はGSUで合成する。地面と空のHDMAは維持する。

VRAMの画像面は`0000..5FFF`と`6000..BFFF`の二つ。`C000..C7FF`が画像マップ、`C800..CB7F`がカラー版の自機OBJ、`D000..EFFF`が地面CHR、`F000..FFFF`が地面マップ。自機は姿勢が変わると896bytesを転送し、OAMとBG1を同じ世代で提示する。VRAMを上書きしている途中の面は表示せず、二つのフィールドの転送が終わってからBG1のCHR面を切り替える。

画像を64pxの四つの縦帯に分け、一方のフィールドで左から第1・第3帯、次で第2・第4帯を描く。ゲーム計算と入力は各フィールドに1回、画像更新は2フィールドに1回。NTSCの目標値は約30.05fpsであり、30.000fps固定ではない。負荷で締切を超えれば次の非表示区間まで待つため、その場面では描画とゲーム進行に遅延が出る。

初期の固定24KiB転送から、列ごとの必要なタイル範囲だけを送る方式へ変更した。転送先VRAM面に残る旧画像の範囲と、現在の画像の範囲の和集合をGSUで計算する。消去すべき旧画像も転送対象に含め、残像を防ぐ。DMAは既存の非表示区間（走査線203以降と、次フィールドの22まで）に収める。転送バイト数と記述子数に応じて開始可能な最終時刻を計算する。

ボス・爆発・ボス弾の7原画は、実際に使う幅・高さに合わせた水平縮小行をROMへ事前生成する。元と同じQ8.8のサンプリング、座標、クリップ、前後関係を使う。元幅・高さが事前計算の対象外なら汎用経路へ戻し、整数刻みの水平参照は短い専用loopで描く。爆発の高さ計算はSNESの乗算器で行い、元の整数式との一致をエミュレータ内で検査する。

拡縮準備では描画kernelの命令cacheを入れ直さず、連続するボス部品で再利用する。転送区間plannerの16列loop、背景二層の境界計算・画素loopもcacheへ置く。2bpp経路のCACHE命令は維持する。

特に面積の大きいボス胴・顔は、事前生成する縮小行を1画素1byteで配置し、描画中の4bit展開を省く。他の爆発・ボス弾は2画素1byteのまま保持し、2MiBのROM内に収める。
通常向きの胴・顔は描画経路を先に選び、使用しない水平UV計算も省く。寸法が対象外なら元のUV計算と汎用描画へ戻す。

## 素材

承認済みの物体だけを黒背景へ切り抜いた実験と同じ手法を、カラーROMへ反映した。採取後の二色塗り直しと固定ディザを外し、原作の色画素・陰影を入力として共通15色＋透明へ減色する。木、草、岩、敵の開閉、ボスと炎弾を録画から採取する。草は外周で切り抜き、明るい葉と暗部を色キーで抜かない。顎には隣の胴を含めない。爆発は白黒版と同じ四パターンの輪郭・内部模様を持つ以前の素材を使い、5→39→40→41→40→39の順に切り替える。各矩形・時刻・背景分離・元動画SHA256・爆発素材の出典は `game/v001/assets/color4/source.json` に保存する。

パレットは背景・自機を除く物体画素から選ぶ。通常弾の紫・青・赤には録画由来の色を各1色確保する。通常弾は旧四姿勢の回転軸に録画の階調を移し、32更新の色周期と64更新の回転を保つ。各色周期の原画を事前生成するので、パレット番号の加算や画素ごとの色変換は不要。炎形のボス弾は原作の橙色。自機はmainの透明修正済み17姿勢と専用15色を維持する。自弾も録画由来、影とSTAGE文字は従来素材。

拡縮は最近傍、縦横を一緒に拡縮して既存の投影比率へ透明余白を足す。旧二色版と完全に同じ白黒画素という条件は今回の切り抜き採用で置き換わる。新しい原画の透明・元RGB・最近傍減色・実ROM内の画素を `tools/verify_4bpp_cutouts.py` で検査する。旧検証結果は過去のROMの記録として残す。

mainのBGM第2版・SEも搭載する。起動時の非表示中に音源を読み込み、ゲーム中の転送締切を圧迫しない。再生開始前の黒画面は約1.5秒。

## 再現

cc65、Python（Pillow、NumPy）、ffmpeg、Mesenが必要。既存と同じ `D:\HomeBrew\CC65\bin`、`D:\HomeBrew\Mesen\Mesen.exe` を利用する。Mesenの場所は `MONOSH_FX2_MESEN` でも指定できる。

```powershell
python -X utf8 tools/build_4bpp.py --color
python -X utf8 tools/test_4bpp.py --scenario controls --frames 2400
python -X utf8 tools/test_4bpp.py --scenario boss --frames 2600
python -X utf8 tools/verify_4bpp.py controls boss
python -X utf8 tools/archive_4bpp.py color controls boss
```

白黒素材のビルドは `--color` を外す。通常プレイの長時間試験は `--scenario play --frames 18000`。元動画から素材を再採取する場合は `python -X utf8 tools/import_4bpp_cutouts.py --video <動画のパス>`。

独立したPython合成器で全49,152画素を再計算し、GSUの4面データと表示中VRAMの24KiBを照合する。各半分のDMAが非表示区間内に完了することも検査する。入力はMesenの`inputPolled`へ渡し、controlsでは移動量と連射、pauseでは論理時間の停止・再開をassertする。全44素材×四反転×五寸法・clip条件は`--scenario assets --frames 2000`、24KiB全転送へのfallbackは`--scenario full --frames 240`で検証する。計測・画面・標本は `game/v001/results/four_bpp_20261008/`、ROMのSHA256と要約は `releases/4bpp30_*.json` に保存する。

自機の独立検査は `--scenario players --frames 920`（17姿勢×四反転×六条件）、弾の周期検査は `--scenario bullets --frames 480`（通常弾三発とボス炎弾）。同じシナリオ名を `tools/verify_4bpp.py` に渡すと、実OAM・CHR・パレットから合成した自機と、弾64位相を照合する。

爆発の順序検査は `--scenario effects --frames 480`。通常敵とボスの描画処理へ六位相のタイマーを渡し、両方の実packetと全画素を照合する。`tools/report_4bpp_material_repair.py` が修正前後の草・顔、爆発四枚と実PPUのアニメを `results/material_repair_20261009/` へ保存する。

次回以降のmainの取り込みは、変更をcommitしたこのworktreeで以下を実行する。mainから実験ブランチへの一方向のmerge、ビルド、検証、ROM保存、実験ブランチへのpushを行う。競合や検証失敗時は停止する。

```powershell
powershell -ExecutionPolicy Bypass -File tools/sync_4bpp_upstream.ps1
```

測定結果と達成範囲は `game/v001/RESULTS_4BPP30_20261008.md` に記載する。
