# 2bppカラー最適化と既存BGM・SEの統合

最新main `f94087bc` の標準SPC700音声を残し、カラー描画・差分DMA最適化を統合した。音声データ・曲・六種類のSEは変更していない。

- 配布ROM: `releases/MonoSHFX2_v001.sfc`、2,097,152 bytes
- SHA256: `5894da3a3f3f25110ec3b05e122ec2a57f9fbff814ca3e6b26a9446e03c2dd16`
- Mesen 2.1.1、NTSC、GSU100%、追加scanlineなし。実機未検証。

## 性能

|最終ROMの試験|提示数|平均fps|1field間隔|2field間隔|
|---|---:|---:|---:|---:|
|通常18,000field|17,995|60.092133|17,992|2|
|継続ボス18,000field|17,988|60.065418|17,977|10|

提示間隔はDMA開始の物理fieldから計算し、同じ黒帯への重複提示は0。継続ボスは12,922画像を含む。音声を含まない[旧カラー最適化ROM](RESULTS_20261008_COLOR_60HZ.md)の全間隔1fieldという結果を、この統合版の結果と混同しない。ユーザーの指示に従い、まれな処理落ちは残したまま反映した。音声の空通知省略は試作のみで、このROMには含めていない。

## 最終ROMの回帰確認

- 音声16,000field: 曲一周、六種類のSE、ポーズ／再開、GSU稼働中の音声API呼出し0。原作との音楽的な再現品質は本試験の判定対象外。
- カラー360field: 243画像、186,624属性セルとCGRAM／VRAMが一致。
- 固定523場面: 2,314画像のFB／OBJおよび色属性・VRAMが基準描画と一致。
- OBJ720、display720、controls720、pause650、packed360、stumble800、boss3000、stress360、held1800、scenery800fieldが合格。表示3視点の最終RGBも一致。
- 独立DMA／HDMA試験: 6,110提示、SRAM保護領域1,869,660bytesを確認。12KiB全FB＋最大OAM＋配色切替の終了は最遅21行864clock、OBJ準備の22行まで500clock。
- 専用probeの72締切条件、計7,200fieldが合格。各99～100画像、最遅終了18行。probeの前後で通常ROMを再ビルドし、上記SHAとの一致を確認。

色素材はカラー試作版のものを保持している。この画素一致試験はコードの回帰確認であり、素材のシルエットや原作らしさを保証するものではない。見た目の比較・修正は別途進める。

[最終ROMの検証JSON](results/color60_audio_20261008/integration.json)、[通常](results/color60_audio_20261008/natural.json)、[継続ボス](results/color60_audio_20261008/sustained_boss.json)、[音声](results/color60_audio_20261008/audio.json)、[DMA](results/color60_audio_20261008/pipeline_summary.json)。以前のカラー最適化の詳細資料も保持した。

再現: `python tools/build_game.py`、`python tools/test_audio.py --frames 16000 --timeout 1200`、`python tools/profile_boss.py --minimal --frames 18000 --timeout 1200 --allow-unreleased --output boss_profile_final`。継続ボスは `--boss-fire none` を追加する。`tools/report_color_60hz.py` は上記の少数の2field間隔を正しく不合格として報告する。
