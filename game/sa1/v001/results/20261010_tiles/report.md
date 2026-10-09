# 変更タイルの個別転送は既定へ採用しない

同じ471回分の描画packet（背景位置も含む）がbyte単位で一致する二方式を、完成470枚まで比較した。素材・物量・ゲーム更新の内容を変更していない。両方式とも125枚の完成FBと転送後VRAMが参照画像に一致した。

|方式|470枚までのfield数|SA-1平均ms|SA-1最大ms|平均PPU転送bytes（初期化除外）|
|---|---:|---:|---:|---:|
|bands|604|7.469|21.437|4116.6|
|tiles|683|9.024|24.281|3739.5|

tiles方式は32bit×24行の変更bitmapを使う。descriptor設定より安い3tile以下の隙間はまとめ、二つのPPU面へ必要なrunを転送する。消去もrun単位とした。転送量は減るが、bitmap生成・走査と細かい消去の設定が増え、全体では遅い。既定はbands方式のままとし、比較実装は`--tile-dma`に分離する。

再現:

```powershell
python tools/build_sa1_game.py --tile-dma
python tools/test_sa1_game.py --frames 1800 --presents 470 --scenario tiles
python tools/build_sa1_game.py
python tools/test_sa1_game.py --frames 1800 --presents 470 --scenario bands
python tools/report_sa1_tiles.py
```

60fpsは引き続き未達。次は画像を先行して用意する構成を試す。
