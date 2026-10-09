# 地面四色の指定RGB更新

2026年10月9日。現行の2bpp・60fps版の地面色を更新した。[通常起動](../../play.cmd)で新ROMを開く。起動中の場合はROMを開き直す。

依頼原文：

> 地面の色を暗い方から、
> 112 191 111
> 129 208 128
> 145 223 145
> 159 240 161
> になるようにして。

SNESの各成分5bitに合わせ、8bitへ展開した値が指定に最も近い色を選ぶ。同距離は小さい値を選ぶ。

|暗い順|指定RGB|RGB5|表示RGB|
|---|---|---|---|
|1|112,191,111|14,23,13|115,189,107|
|2|129,208,128|16,25,16|132,206,132|
|3|145,223,145|18,27,18|148,222,148|
|4|159,240,161|19,29,20|156,239,165|

暗い列に1/2、明るい列に4/3を置く配置を引き継ぐ。横隣接は1/4・2/3。指定は生成元の `tools/build_ground.py` と配布manifestへ保存した。

変更前ソースの再ビルドが配布ROM `01a4c6d63bcf458b0c28d16f58906872376b7d501a4a5b2901ad69e0ee8f3f27` と全2MiBで一致してから変更した。新ROMは `38d2fccd3f125c413d019b83073294e5eb47beb2dcda1ebbce8371b002ce560d`。

Mesenのdisplay試験720フィールドに通過。カメラ位置0/32/64の最終PPU計183,552画素が独立合成と一致し、四つの地面色・縦列の明度グループ・横の色ペア・遠景と地面上2行のclipを確認した。FXの全49,152画素とOBJも各3場面で一致。

全65カメラ×14位相×2色の1,820本のHDMA表、22,452色エントリーを変更前と照合した。全ROMの差分11,228bytesは地面の色定数・色HDMAの値・checksumだけ。CPU/GSU・音源を含むそれ以外の全byteと全label位置が一致し、転送量・描画負荷は変わらない。今回新たに長時間60Hz試験や実機試験は行っていない。

自己評価：指定RGBを暗い順に保存し、ハードウェアで表現できる近似色を全カメラで反映できた。8bit指定値との丸め差は残る。

集計は [summary.json](results/ground_palette_20261009/summary.json)、表示とVRAM/CGRAM/HDMAの標本は同所の `display_samples.zip`。画面は [カメラ0](results/ground_palette_20261009/display00238.png)・[32](results/ground_palette_20261009/display00478.png)・[64](results/ground_palette_20261009/display00718.png)。以前の計測とmanifestは同所 `previous_release.json` に保持した。

再確認はプロジェクトのルートで `python -X utf8 tools/build_game.py`、`python -X utf8 tools/test_game.py --scenario display --frames 720 --timeout 120`。
