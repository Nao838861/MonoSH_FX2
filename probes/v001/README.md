# v001：FX2 描画・DMA の実行検証

2026年10月5日。ゲーム移植前のハードウェアプローブ。ca65/casfx で Super FX 入り ROM を生成し、Mesen の GSU を動かして、描画結果とエミュレートされたクロック数を検証する。

最初に読むものは [測定結果と判断](RESULTS.md)。実測の生データ、入力のハッシュ、合成画像は [results](results/) に保存している。ゲームロジック・地面・HUD はまだ入れていない。

## 再実行

必要なものは Python 3.10 以上、Pillow、PATH 上の ca65/ld65、GSU と Lua に対応する Mesen、参照元の NES MonoSH。今回の環境では既存の ca65 V2.19 と Mesen 2.1.1 を使用した。casfx の取得 commit とハッシュは [sources.lock.json](sources.lock.json) に固定している。

プロジェクトのルート（[README.md](../../README.md)のある場所）から実行する。

```powershell
python -X utf8 tools/verify_probe.py
```

既定の参照先は `D:\HomeBrew\MonoSH` と `D:\HomeBrew\Mesen\Mesen.exe`。必要なら、実行前に次の環境変数で変更できる。

```powershell
$env:MONOSH_NES_ROOT = 'D:\HomeBrew\MonoSH'
$env:MONOSH_FX2_MESEN = 'D:\HomeBrew\Mesen\Mesen.exe'
```

このコマンドは依存ソース取得、534件の描画比較、DMAの3条件、NES描画コードの5サイズ、30体の2場面を順番に実行する。全検証の成功後に `results/` の記録を更新する。失敗した場合は途中で終了する。

参照元の画像 `png/Tree0/Tree0_00.png` と生成済みの `src/gen/sprite_Tree0.s` を読み取る。参照元は変更しない。Mesen はプロジェクト内 `.cache/mesen_runtime` に複製して専用の設定を使う。Lua による入出力をこの設定で許可し、通常使用している Mesen の設定とは分ける。

## 個別実行

```powershell
python -X utf8 tools/bootstrap_probe.py
python -X utf8 tools/run_probe.py --sweep
python -X utf8 tools/run_dma_probe.py
python -X utf8 tools/run_nes_baseline.py
python -X utf8 tools/run_scene_probe.py
```

個別実行は `build/v001/` に出力する。`run_probe.py --source tree` なら木だけ、`--source fragmented` なら細かい模様だけを再検証できる。個別実行だけでは保存済みの `results/` は更新しない。

## 実装の入口

| ファイル | 役割 |
| --- | --- |
| [cpu.s](cpu.s) | 65816 起動、WRAM常駐、GSUレジスタ入力とSTOP待ち、Mode 0とHDMAによる帯域試験 |
| [gsu.s](gsu.s) | 全クリアと11種類の描画経路。GSU命令での縮小、透過合成、pixel cacheのflush |
| [rom.cfg](rom.cfg) | 512KiBの試験用LoROM。描画元を形式別のROM bankへ配置 |
| [measure.lua](measure.lua) | GSU命令の開始・終了クロック取得、FB dump、guard検査 |
| [dma_measure.lua](dma_measure.lua) | DMAの開始・終了位相、VRAMへ届いたbytes、PPU画像の記録 |
| [run_probe.py](../../tools/run_probe.py) | アセット変換、ビルド、GSU出力とPython参照画像の比較 |
| [run_scene_probe.py](../../tools/run_scene_probe.py) | 深度順の30体を連続描画。縮小率に応じた経路選択 |

生成される `.sfc` / `.nes` は Lua から試験入力を渡す ROM で、通常起動時は入力待ちになる。単体起動できるゲームや操作デモとしては扱わない。`.cache/`、`build/`、Python cache は git 管理外。

casfx は外部依存として取得し、同じ取得先の `LICENSE` を保持する。Mesen の参照ソース commit は挙動の調査用で、今回使用した既存の実行ファイルをその commit からビルドしたという意味ではない。測定環境は実行ファイルの SHA-256 で識別する。
