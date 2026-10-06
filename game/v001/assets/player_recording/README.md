# 録画由来の自機素材

`pose00.png`〜`pose03.png`、`pose10.png`〜`pose13.png`は背景を除去した録画の格子サイズの原画。`native16_pose*.png`はそのサイズを保った透明1色＋不透明15色のインデックスPNG。ゲーム用は隣の`obj_color/`の09、15〜18、28〜30。32×48へ75%で収め、各色はSNESのRGB5へ合わせている。

[変更前・原寸・ゲーム用の比較](comparison.png)と[ゲーム用8ポーズ](preview.png)。フレーム・矩形・動画ハッシュは[source.json](source.json)、処理・検証は[検証結果](../../RESULTS_20261007_PLAYER_RECORDING.md)。元動画は同梱しない。

プロジェクトルートから、固定した原画だけを使ってOBJ用PNGを再生成する：

```powershell
python -X utf8 tools/import_recorded_player.py
python -X utf8 tools/build_game.py
```

元動画から取り出し直す場合だけ、ffmpegと録画が必要：

```powershell
python -X utf8 tools/import_recorded_player.py --video "D:\HomeBrew\MonoSH\tmp\スペースハリアー録画１.mp4"
```

録画にない死亡・つまずき9ポーズは既存の輪郭を残している。再取込用の`import_obj_colors.py`は以前のNES画像を復元する別の入口なので、録画版を維持する通常ビルドでは実行しない。
