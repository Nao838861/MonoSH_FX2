# SA-1 / 4bpp / 60fps 実験 v001

独立分岐: `experiment/sa1-4bpp-60fps-20261010`。分岐元 `957eeee`。元の4bpp/30fps作業フォルダとGit分岐は変更しない。

現在は実SA-1を使う描画計測ROMが動く。ゲーム統合と60fps表示は作業中。素材は `game/v001/assets/color4/` をそのまま参照する。

実装前の3回の設計比較と依頼原文は [design_log.md](design_log.md)、同一packetを用いたFX2・SA-1・事前縮小・コンパイルドの比較は [結果](results/20261010_probe/report.md) を参照。

計測ROMは `tools/build_sa1_probe.py`、実CPU実行・画素照合は `tools/test_sa1_probe.py`、現行FX2との比較は `tools/test_sa1_fx2_comparison.py`。生成物は `build/sa1_v001/` に隔離する。各方式のROMはまだゲームを遊ぶためのものではない。
