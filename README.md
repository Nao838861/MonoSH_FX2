# MonoSH Super FX2 開発プロジェクト

最新ROMは [ボス限定の縮小画像と追加最適化](game/v001/RESULTS_20261008_BOSS_SCALING.md)。縮小画像をボス3素材だけにし、先読み・透明余白省略・511byteの共通GSUキャッシュ・転送量別のDMA締切を採用した。追加データを約203KiB減らし、録画由来の大きい自弾・二層遠景も統合。CPUのOAM生成・地面HDMA表・転送区間loopも追加最適化した。表示256×180・内部FB256×192・2bpp。統合前後の速度・画素・転送の検証を上記の結果に分けて記録する。

統合した最終ROMで通常プレイ・長期ボス各約5分、**全区分の表示遅延0、60.10fps**を確認した。固定523場面2,454画像の全FB/OBJ、42条件のDMA限界量、操作・表示・押しっぱなしも検証済み。任意の入力・実機での保証はまだない。

録画由来の大きな自弾・紫から緑の空・二層遠景を実装した。[検証結果](game/v001/RESULTS_20261008_RECORDED_EFFECTS.md)、[静止連射GIF](game/v001/results/recorded_effects_20261008/stationary_fire.gif)を保存している。以前の測定値は、その測定時のROMに対する記録。

GitHub: [Nao838861/MonoSH_FX2](https://github.com/Nao838861/MonoSH_FX2)。ソース、単独起動ROM、設計書、測定ログ・画像をこのリポジトリにまとめる。

自機は録画から切り出した飛行4・走行4ポーズを32×48・16色へ差し替えた。原寸の16色素材と[比較画像](game/v001/assets/player_recording/comparison.png)、[処理・検証](game/v001/RESULTS_20261007_PLAYER_RECORDING.md)も保存し、通常起動するROMへ反映している。

NES版MonoSHのゲームを、MSXSHの60Hz更新仕様を参照してSNESのCPUへ移植した。Super FX2が拡縮スプライトを奥から描き、自機と自弾・反射弾はPPUのOBJ、通常BGとHDMAが地面・遠景を描く。**Stage 1からボス撃破・次周まで動くROM。** 押しっぱなし射撃で誤ポーズになる入力取得も修正済み。通常操作、押しっぱなし、Startでのポーズ・解除を検証した。詳細は [検証結果](game/v001/RESULTS.md)。

地面は同一消失点からの直線式へ直した。指定RGBに近い緑四色を使い、暗い1/2の列と明るい4/3の列が奥へ続く。空は紫から緑のグラデーション。紫の山と緑の森林は別BGで二重スクロールする。自機17poseは赤い服・青い脚・肌色、自弾は録画由来の水色の輪を56×32から縮小するカラーOBJ。静的CHRとパレットは起動時だけ設定し、毎画像の追加転送は使用枠に応じたOAMだけ。三カメラ・反転・画面端・最悪の重なりを最終PPUの画素で照合した。

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
python -X utf8 tools/verify_render_release.py
python -X utf8 tools/verify_full_transfer_objects.py
```

通常のゲームROMのビルドには、元のNES/MSXプロジェクトは不要。固定したソース・画像・表を同梱し、casfxだけ固定commitとhashを検査して取得する。

192行・上下16行黒帯の全12KiB転送は最初のプローブで992bytes欠けた。現在はGSUが前後の矩形を32列のtile区間にまとめ、CPUがSTOP後に部分転送する。転送量と区間数が大きい場合は全12KiB一本へ戻す。実ゲームHDMA併用の最大量テストを通すため、表示は180行にして上下を切った。内部FBは256×192・2bppで、座標・当たり判定は縮めていない。192行表示と実機・より広い入力での60Hz検証は残る。

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
