# MonoSH Super FX2 開発プロジェクト

GitHub: [Nao838861/MonoSH_FX2](https://github.com/Nao838861/MonoSH_FX2)。ソース、単独起動ROM、設計書、測定ログ・画像をこのリポジトリにまとめる。

NES版MonoSHのゲームを、MSXSHの60Hz更新仕様を参照してSNESのCPUへ移植した。Super FX2が拡縮スプライトを奥から描き、通常BGとHDMAが地面・遠景を描く。**Stage 1からボス撃破・次周まで動くROM。表示256×180、通常進行平均55.11fps、序盤は起動を含め59.55fps。全場面60fpsには未達。**

地面の行別縦横スクロールと緑四色、遠景の上下移動、FX層の一対一表示、地上物との高さを修正した。CPU更新を65816へ、UV・clip・消去と転送範囲の準備をGSUへ移し、C/nativeの通常5,632更新・ボス2,847更新一致、最終RGBの三カメラ照合を含む [検証結果](game/v001/RESULTS.md) を保存した。

まず [play.cmd](play.cmd) で遊べる。[ROM単体](releases/MonoSHFX2_v001.sfc) と [操作・ビルド手順](game/v001/README.md)、[実ゲームの測定結果](game/v001/RESULTS.md) を保存した。上下はNESと同じリバース操作。専用ランチャーでは左右矢印、下＝上昇／上＝下降、X連射、Z単発、Enter一時停止。

## cloneして使う

ROMはGSU/Super FX対応のMesenで開く。専用ランチャーにはPython 3.10以上とPillowが必要で、Mesenの場所は環境変数 `MONOSH_FX2_MESEN` で指定できる。詳細は [操作・準備](game/v001/README.md)。

```powershell
git clone https://github.com/Nao838861/MonoSH_FX2.git
cd MonoSH_FX2
python -m pip install -r requirements.txt
```

ビルドにはPATH上のcc65/ca65/ld65を使う。プロジェクトのルートで実行する。

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/verify_game.py --equivalence
```

通常のゲームROMのビルドには、元のNES/MSXプロジェクトは不要。固定したソース・画像・表を同梱し、casfxだけ固定commitとhashを検査して取得する。

192行・上下16行黒帯の全12KiB転送は最初のプローブで992bytes欠けた。現在はGSUが前後の矩形を32列のtile区間にまとめ、CPUがSTOP後に部分転送する。転送量と区間数が大きい場合は全12KiB一本へ戻す。実ゲームHDMA併用の最大量テストを通すため、表示は180行にして上下を切った。内部FBは256×192・2bppで、座標・当たり判定は縮めていない。192行と全場面60fpsは改善目標。

- [設計書](DESIGN.md) — メモリ所有権、CPU と GSU の並行動作、転送量、地面、移植手順、未決事項。
- [実行可能な移植版 v001](game/v001/README.md) — ゲームROM、操作、元の60Hz更新の移植、描画・転送の実装。
- [v001測定結果](probes/v001/RESULTS.md) — 11種類のGSU描画経路、534件の画素検証、30体合成、全転送不足、NESとの速度比較。
- [clip条件とDMA対策](DMA_OPTIONS.md) — 最大の木はclipなし。矩形からの差分転送、固定空白、HBlank forced blank、黒帯追加を比較。
- [v001再実行手順](probes/v001/README.md) — 検証ROMのビルドと自動実行。
- [依頼原文](REQUEST.md) — 2026年10月5日の依頼を保持。
- [帯域計算](tools/frame_budget.py) — 解像度と描画リスト量から時間予算を再計算する。実測値ではない。
- [開発記憶](https://github.com/Nao838861/nao-u-lab/blob/codex/phase1-collect-20260810/GPT/memory/projects/monosh_fx2/README.md) — 元の作業環境での判断・再開場所。

```powershell
python -X utf8 tools/verify_probe.py
python -X utf8 tools/frame_budget.py
python -X utf8 tools/frame_budget.py --commands 40 --reserve-ms 0.5
python -X utf8 tools/frame_budget.py --normal-dma-bytes 7000
```

現在の実装先は [game/v001](game/v001)。参照元はNESの `D:\HomeBrew\MonoSH` とMSXの `D:\MSXDev\MSXSH` で、原本は変更していない。通常ビルドは固定済みの原本・画像を使う。初期の設計・測定記録にある `projects/monosh_fx2/` は元の作業環境での配置を指す。
