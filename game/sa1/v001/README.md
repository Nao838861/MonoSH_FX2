# SA-1 / 4bpp / 60fps 実験 v001

独立分岐: `experiment/sa1-4bpp-60fps-20261010`。分岐元 `957eeee`。元の4bpp/30fps作業フォルダとGit分岐は変更しない。

現在は実SA-1を使うゲーム統合ROMが動く。60fps表示は未達で作業中。素材は `game/v001/assets/color4/` をそのまま参照する。試遊はリポジトリ直下の `play_sa1.cmd`。統合ROMの測定と制約は [ゲーム統合の記録](results/20261010_game/report.md) を参照。

試遊ROMは[PPUの実参照位置を修正・再検証した版](results/20261010_ppu_layout/report.md)へ更新した。道中・ボス各1,900fieldで147画面一致。表示が2field間隔になる箇所はそれぞれ8回・9回残る。従来の固定配置表・四面の検証はPPU参照位置の不整合を見逃しており、正常表示の証拠としては使わない。

実装前の3回の設計比較と依頼原文は [design_log.md](design_log.md)、同一packetを用いたFX2・SA-1・事前縮小・コンパイルドの比較は [結果](results/20261010_probe/report.md) を参照。

計測ROMは `tools/build_sa1_probe.py`、実CPU実行・画素照合は `tools/test_sa1_probe.py`、現行FX2との比較は `tools/test_sa1_fx2_comparison.py`。生成物は `build/sa1_v001/` に隔離する。各方式のROMはまだゲームを遊ぶためのものではない。
